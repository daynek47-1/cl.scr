"""Engine Manager - Lifecycle & Heartbeat Orchestrator"""
import logging
import os
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from ..models import MirrorSite, SiteHealth, ScrapeRun
from ..models.database import SessionLocal
from .auth import AuthManager
from .pv_calculator import PVCalculator
from .deduplicator import BonusDeduplicator
from .worker import Worker, ProxyPool
from .console import TwoLineConsole

load_dotenv()

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


class EngineManager:
    """
    The Manager - Orchestrates the entire Intelligence Engine

    Responsibilities:
    1. Lifecycle Management: Track site health (Active/Purgatory/Pruned)
    2. Heartbeat Cycles:
       - Standard Run (every cycle): Check Active sites
       - Retest Cycle (every 5th run): Check Purgatory sites
       - Resurrection (every 125th run): Check Pruned sites
    3. Worker Coordination: Manage parallel workers
    4. Statistics Tracking: Record all runs
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        worker_count: int = None,
        use_proxies: bool = None,
        proxy_list: List[str] = None,
        quiet_mode: bool = True
    ):
        # Configuration from environment or parameters
        self.username = username or os.getenv('CASINO_USERNAME')
        self.password = password or os.getenv('CASINO_PASSWORD')
        self.worker_count = worker_count or int(os.getenv('WORKER_COUNT', 5))
        self.use_proxies = use_proxies or os.getenv('USE_PROXIES', 'false').lower() == 'true'
        self.quiet_mode = quiet_mode if quiet_mode is not None else os.getenv('QUIET_MODE', 'true').lower() == 'true'

        # Proxy setup
        if proxy_list:
            self.proxy_list = proxy_list
        else:
            proxy_str = os.getenv('PROXY_LIST', '')
            self.proxy_list = [p.strip() for p in proxy_str.split(',') if p.strip()]

        # Heartbeat configuration
        self.purgatory_interval = int(os.getenv('PURGATORY_CHECK_INTERVAL', 5))
        self.resurrection_interval = int(os.getenv('RESURRECTION_CHECK_INTERVAL', 125))

        # Run counter
        self.run_number = 0

        # Set logging level based on quiet mode
        if self.quiet_mode:
            # In quiet mode, suppress all logs (only show critical failures)
            logging.getLogger().setLevel(logging.CRITICAL)
            logging.getLogger('src.engine').setLevel(logging.CRITICAL)
        else:
            logger.info(f"Engine Manager initialized:")
            logger.info(f"  Workers: {self.worker_count}")
            logger.info(f"  Proxies: {len(self.proxy_list) if self.use_proxies else 0}")
            logger.info(f"  Purgatory check: Every {self.purgatory_interval} runs")
            logger.info(f"  Resurrection check: Every {self.resurrection_interval} runs")

    def run_cycle(self) -> Dict:
        """
        Execute one complete scrape cycle

        Returns statistics about the run
        """
        self.run_number += 1
        run_type = self._determine_run_type()

        if not self.quiet_mode:
            logger.info(f"=" * 60)
            logger.info(f"Starting Run #{self.run_number} - Type: {run_type.upper()}")
            logger.info(f"=" * 60)

        start_time = datetime.utcnow()

        # Get sites to check based on run type
        sites_to_check = self._get_sites_for_run(run_type)

        if not self.quiet_mode:
            logger.info(f"Sites to check: {len(sites_to_check)}")

        if not sites_to_check:
            logger.warning("No sites to check!")
            return {'status': 'no_sites', 'run_number': self.run_number}

        # Initialize components
        db = SessionLocal()
        auth_manager = AuthManager(db, self.username, self.password)
        pv_calculator = PVCalculator()
        deduplicator = BonusDeduplicator(db)

        # Proxy pool setup
        proxy_pool = ProxyPool(self.proxy_list) if self.use_proxies and self.proxy_list else None

        # Console setup
        console = TwoLineConsole()
        console.print_header()

        # Create scrape run record
        scrape_run = ScrapeRun(
            run_number=self.run_number,
            run_type=run_type,
            started_at=start_time
        )
        db.add(scrape_run)
        db.commit()

        # Execute parallel scraping
        results = self._execute_parallel_scrape(
            sites_to_check,
            auth_manager,
            pv_calculator,
            deduplicator,
            proxy_pool,
            console
        )

        # Aggregate results
        stats = self._aggregate_results(results)

        # Update scrape run record
        scrape_run.sites_checked = stats['sites_checked']
        scrape_run.sites_successful = stats['sites_successful']
        scrape_run.sites_failed = stats['sites_failed']
        scrape_run.bonuses_found = stats['bonuses_found']
        scrape_run.bonuses_new = stats['bonuses_new']
        scrape_run.completed_at = datetime.utcnow()
        scrape_run.duration_seconds = (scrape_run.completed_at - start_time).total_seconds()

        db.commit()

        # Mark expired bonuses
        expired_count = deduplicator.mark_expired_bonuses()

        # Get deduplication stats
        dedup_stats = deduplicator.get_duplicate_stats()

        db.close()

        # Print console summary (always show)
        console.print_summary()

        # Log summary (only in verbose mode)
        if not self.quiet_mode:
            logger.info(f"=" * 60)
            logger.info(f"Run #{self.run_number} Complete!")
            logger.info(f"  Duration: {scrape_run.duration_seconds:.2f}s")
            logger.info(f"  Sites Checked: {stats['sites_checked']}")
            logger.info(f"  Successful: {stats['sites_successful']}")
            logger.info(f"  Failed: {stats['sites_failed']}")
            logger.info(f"  Bonuses Found: {stats['bonuses_found']}")
            logger.info(f"  New Bonuses: {stats['bonuses_new']}")
            logger.info(f"  Expired: {expired_count}")
            logger.info(f"  Deduplication Rate: {dedup_stats['deduplication_rate']}%")
            logger.info(f"=" * 60)

        return {
            'run_number': self.run_number,
            'run_type': run_type,
            'duration': scrape_run.duration_seconds,
            **stats,
            'expired_bonuses': expired_count,
            'dedup_stats': dedup_stats
        }

    def _determine_run_type(self) -> str:
        """Determine type of run based on run number"""
        if self.run_number % self.resurrection_interval == 0:
            return 'resurrection'
        elif self.run_number % self.purgatory_interval == 0:
            return 'retest'
        else:
            return 'standard'

    def _get_sites_for_run(self, run_type: str) -> List[MirrorSite]:
        """Get sites to check based on run type"""
        db = SessionLocal()

        if run_type == 'standard':
            # Check only Active sites
            sites = db.query(MirrorSite).filter(
                MirrorSite.health_status == SiteHealth.ACTIVE
            ).all()

        elif run_type == 'retest':
            # Check Active + Purgatory sites
            sites = db.query(MirrorSite).filter(
                MirrorSite.health_status.in_([SiteHealth.ACTIVE, SiteHealth.PURGATORY])
            ).all()

        else:  # resurrection
            # Check ALL sites (Active + Purgatory + Pruned)
            sites = db.query(MirrorSite).all()

        db.close()
        return sites

    def _execute_parallel_scrape(
        self,
        sites: List[MirrorSite],
        auth_manager: AuthManager,
        pv_calculator: PVCalculator,
        deduplicator: BonusDeduplicator,
        proxy_pool: ProxyPool,
        console: TwoLineConsole
    ) -> List[Dict]:
        """Execute scraping with parallel workers"""
        results = []

        if not self.quiet_mode:
            logger.info(f"Launching {self.worker_count} workers...")

        with ThreadPoolExecutor(max_workers=self.worker_count) as executor:
            # Create workers
            workers = []
            for i in range(self.worker_count):
                # Each worker gets its own DB session
                db = SessionLocal()
                worker = Worker(
                    worker_id=i + 1,
                    db=db,
                    auth_manager=auth_manager,
                    pv_calculator=pv_calculator,
                    deduplicator=BonusDeduplicator(db),  # Fresh deduplicator for each worker
                    proxy_pool=proxy_pool,
                    console=console
                )
                workers.append((worker, db))

            # Submit tasks
            futures = {}
            total_sites = len(sites)
            for idx, site in enumerate(sites):
                worker, db = workers[idx % len(workers)]
                count = idx + 1
                future = executor.submit(worker.process_site, site, count, total_sites)
                futures[future] = (site.url, count)

            # Collect results
            for future in as_completed(futures):
                site_url, count = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Worker exception for {site_url}: {e}")
                    results.append({
                        'status': 'failed',
                        'bonuses_found': 0,
                        'bonuses_new': 0,
                        'error': str(e)
                    })

            # Clean up worker DB sessions
            for _, db in workers:
                db.close()

        if not self.quiet_mode:
            logger.info("All workers completed")
        return results

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results from all workers"""
        stats = {
            'sites_checked': len(results),
            'sites_successful': sum(1 for r in results if r['status'] == 'success'),
            'sites_failed': sum(1 for r in results if r['status'] == 'failed'),
            'bonuses_found': sum(r['bonuses_found'] for r in results),
            'bonuses_new': sum(r['bonuses_new'] for r in results),
        }

        return stats

    def add_mirror_site(self, url: str, merchant_id: str = None, name: str = None):
        """Add a new mirror site to the database"""
        db = SessionLocal()

        # Check if already exists
        existing = db.query(MirrorSite).filter(MirrorSite.url == url).first()

        if existing:
            if not self.quiet_mode:
                logger.warning(f"Site already exists: {url}")
            db.close()
            return existing

        # Create new site
        site = MirrorSite(
            url=url,
            merchant_id=merchant_id,
            name=name,
            health_status=SiteHealth.ACTIVE
        )

        db.add(site)
        db.commit()

        if not self.quiet_mode:
            logger.info(f"Added new mirror site: {url}")

        db.close()
        return site

    def get_site_health_summary(self) -> Dict:
        """Get summary of site health across all mirrors"""
        db = SessionLocal()

        active = db.query(MirrorSite).filter(MirrorSite.health_status == SiteHealth.ACTIVE).count()
        purgatory = db.query(MirrorSite).filter(MirrorSite.health_status == SiteHealth.PURGATORY).count()
        pruned = db.query(MirrorSite).filter(MirrorSite.health_status == SiteHealth.PRUNED).count()

        db.close()

        return {
            'active': active,
            'purgatory': purgatory,
            'pruned': pruned,
            'total': active + purgatory + pruned
        }
