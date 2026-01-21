"""Worker - Individual scraping unit with proxy rotation and human mimicry"""
import logging
import random
import time
import requests
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from ..models import MirrorSite, WorkerLog
from .auth import AuthManager
from .api_client import CasinoAPIClient
from .pv_calculator import PVCalculator
from .deduplicator import BonusDeduplicator
from .console import TwoLineConsole

logger = logging.getLogger(__name__)


class ProxyPool:
    """Manages rotating proxies for workers"""

    def __init__(self, proxy_list: List[str]):
        self.proxies = proxy_list if proxy_list else []
        self.current_index = 0
        self.failed_proxies = set()

    def get_proxy(self) -> Optional[str]:
        """Get next available proxy"""
        if not self.proxies:
            return None

        # Try to find a working proxy
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

            if proxy not in self.failed_proxies:
                return proxy

            attempts += 1

        # All proxies failed, reset failed set and try again
        logger.warning("All proxies failed, resetting failed proxy list")
        self.failed_proxies.clear()
        return self.proxies[0] if self.proxies else None

    def mark_failed(self, proxy: str):
        """Mark a proxy as failed"""
        self.failed_proxies.add(proxy)
        logger.warning(f"Proxy marked as failed: {proxy}")


class Worker:
    """
    Individual scraping worker

    Features:
    - Proxy rotation on failure
    - Random delays (human mimicry)
    - Detailed logging
    - Retry logic
    """

    def __init__(
        self,
        worker_id: int,
        db: Session,
        auth_manager: AuthManager,
        pv_calculator: PVCalculator,
        deduplicator: BonusDeduplicator,
        proxy_pool: Optional[ProxyPool] = None,
        console: Optional[TwoLineConsole] = None,
        delay_min: int = 2,
        delay_max: int = 5
    ):
        self.worker_id = worker_id
        self.db = db
        self.auth_manager = auth_manager
        self.pv_calculator = pv_calculator
        self.deduplicator = deduplicator
        self.proxy_pool = proxy_pool
        self.console = console
        self.delay_min = delay_min
        self.delay_max = delay_max

        self.current_proxy = proxy_pool.get_proxy() if proxy_pool else None
        self.api_client = CasinoAPIClient(auth_manager, self.current_proxy)

        logger.info(f"Worker {worker_id} initialized (proxy: {self.current_proxy or 'None'})")

    def process_site(self, mirror_site: MirrorSite, count: int = 0, total_sites: int = 0) -> Dict:
        """
        Process a single mirror site

        Args:
            mirror_site: The mirror site to process
            count: Current site number (for console display)
            total_sites: Total sites being checked (for console display)

        Returns:
            {
                'status': 'success' | 'failed',
                'bonuses_found': int,
                'bonuses_new': int,
                'error': str | None
            }
        """
        start_time = datetime.utcnow()
        result = {
            'status': 'failed',
            'bonuses_found': 0,
            'bonuses_new': 0,
            'error': None
        }

        try:
            logger.info(f"Worker {self.worker_id}: Processing {mirror_site.url}")

            # Human mimicry: Random delay before starting
            self._human_delay()

            # Log start
            self._log_action('starting', 'in_progress', mirror_site.url)

            # Step 1: Fetch bonuses from API
            self._log_action('api_call', 'in_progress', mirror_site.url)
            api_response = self.api_client.fetch_bonuses(mirror_site.url)

            if not api_response:
                raise Exception("Failed to fetch data from API")

            # Step 2: Extract bonuses from response
            self._log_action('parsing', 'in_progress', mirror_site.url)
            bonuses_raw = self.api_client.extract_bonuses_from_response(api_response)

            logger.info(f"Worker {self.worker_id}: Found {len(bonuses_raw)} bonuses")
            result['bonuses_found'] = len(bonuses_raw)

            # Step 3: Process each bonus
            bonuses_new = 0

            for bonus_raw in bonuses_raw:
                try:
                    # Parse bonus
                    parsed_bonus = self.api_client.parse_bonus(bonus_raw)

                    # Calculate PV score
                    pv_data = self.pv_calculator.calculate(
                        parsed_bonus.get('bonus_amount'),
                        parsed_bonus.get('rollover'),
                        parsed_bonus.get('max_withdrawal')
                    )

                    # Deduplicate and save
                    bonus, is_new = self.deduplicator.find_or_create_bonus(
                        mirror_site.id,
                        parsed_bonus,
                        pv_data['pv_score'],
                        pv_data['is_beatable']
                    )

                    if is_new:
                        bonuses_new += 1

                except Exception as e:
                    logger.warning(f"Worker {self.worker_id}: Error processing bonus: {e}")
                    continue

            result['bonuses_new'] = bonuses_new

            # Commit all changes
            self.db.commit()

            # Mark site as successful
            mirror_site.mark_success()
            self.db.commit()

            result['status'] = 'success'
            self._log_action('completed', 'success', mirror_site.url)

            logger.info(
                f"Worker {self.worker_id}: SUCCESS - {result['bonuses_found']} found, "
                f"{result['bonuses_new']} new"
            )

        except requests.exceptions.HTTPError as e:
            # HTTP error - might be proxy or auth issue
            error_msg = f"HTTP {e.response.status_code if hasattr(e, 'response') else 'error'}"

            if hasattr(e, 'response') and e.response.status_code == 403:
                # Likely proxy blocked, rotate proxy
                logger.warning(f"Worker {self.worker_id}: 403 error, rotating proxy")
                self._rotate_proxy()

            result['error'] = error_msg
            mirror_site.mark_failure()
            self.db.commit()

            self._log_action('failed', 'failed', mirror_site.url, error_msg)

        except Exception as e:
            error_msg = str(e)
            result['error'] = error_msg

            mirror_site.mark_failure()
            self.db.commit()

            self._log_action('failed', 'failed', mirror_site.url, error_msg)
            logger.error(f"Worker {self.worker_id}: ERROR - {error_msg}")

        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.debug(f"Worker {self.worker_id}: Completed in {duration:.2f}s")

            # Update 2-line console if available
            if self.console and count > 0 and total_sites > 0:
                # Calculate proxy health (100% if no proxy, or based on proxy pool status)
                proxy_health = 100.0
                if self.proxy_pool and self.proxy_pool.proxies:
                    working_proxies = len(self.proxy_pool.proxies) - len(self.proxy_pool.failed_proxies)
                    proxy_health = (working_proxies / len(self.proxy_pool.proxies)) * 100

                # Calculate site history health based on consecutive failures
                hist_health = 100.0
                if hasattr(mirror_site, 'consecutive_failures'):
                    # 0 failures = 100%, 5+ failures = 0%
                    hist_health = max(0, 100 - (mirror_site.consecutive_failures * 20))

                # Parse error code if present
                error_code = None
                if result['error']:
                    # Extract error code from error message (e.g., "HTTP 403" -> "403")
                    if 'HTTP' in result['error']:
                        error_code = result['error'].replace('HTTP', '').strip()
                    else:
                        error_code = 'ERR'

                self.console.print_two_line(
                    count=count,
                    total_sites=total_sites,
                    url=mirror_site.url,
                    worker_id=self.worker_id,
                    success=result['status'] == 'success',
                    bonuses_this_site=result['bonuses_found'],
                    latency=duration,
                    proxy_health=proxy_health,
                    hist_health=hist_health,
                    error_code=error_code
                )

        return result

    def _human_delay(self):
        """Random delay to mimic human behavior"""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug(f"Worker {self.worker_id}: Sleeping {delay:.2f}s...")
        time.sleep(delay)

    def _rotate_proxy(self):
        """Rotate to next proxy"""
        if not self.proxy_pool:
            return

        # Mark current proxy as failed
        if self.current_proxy:
            self.proxy_pool.mark_failed(self.current_proxy)

        # Get new proxy
        self.current_proxy = self.proxy_pool.get_proxy()
        self.api_client = CasinoAPIClient(self.auth_manager, self.current_proxy)

        logger.info(f"Worker {self.worker_id}: Rotated to proxy: {self.current_proxy or 'None'}")

    def _log_action(
        self,
        action: str,
        status: str,
        site_url: str,
        error_message: Optional[str] = None
    ):
        """Log worker action to database"""
        log_entry = WorkerLog(
            worker_id=self.worker_id,
            mirror_site_url=site_url,
            action=action,
            status=status,
            error_message=error_message,
            proxy_used=self.current_proxy,
            timestamp=datetime.utcnow()
        )

        self.db.add(log_entry)
        # Don't commit here - let the main process handle commits
