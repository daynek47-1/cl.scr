"""Casino API Client for /api/v1/index.php endpoint"""
import requests
import logging
from typing import Optional, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential

from .auth import AuthManager

logger = logging.getLogger(__name__)


class CasinoAPIClient:
    """
    Client for casino API with EXACT payload specification

    Endpoint: {Base_URL}/api/v1/index.php
    Method: POST
    Payload:
        - module: "/users/syncData"
        - merchantId: Extracted from HTML
        - accessToken: From login
        - accessId: From login
        - domainId: "0"
        - walletIsAdmin: ""
    """

    def __init__(self, auth_manager: AuthManager, proxy: Optional[str] = None):
        self.auth_manager = auth_manager
        self.proxy = proxy
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy,
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_bonuses(self, site_url: str, retry_auth: bool = True) -> Optional[Dict]:
        """
        Fetch bonus data from casino API

        Args:
            site_url: Base URL of casino mirror site
            retry_auth: If True, will retry with fresh login on auth failure

        Returns:
            Dict with bonus data or None on failure
        """
        # Get session credentials (from cache or fresh login)
        session_data = self.auth_manager.get_session(site_url)
        if not session_data:
            logger.error(f"Failed to get session for {site_url}")
            return None

        # Build API endpoint
        api_endpoint = f"{site_url}/api/v1/index.php"

        # Build EXACT payload as specified
        payload = {
            "module": "/users/syncData",
            "merchantId": session_data['merchant_id'],
            "accessToken": session_data['access_token'],
            "accessId": session_data['access_id'],
            "domainId": "0",
            "walletIsAdmin": ""
        }

        logger.debug(f"Calling API: {api_endpoint}")
        logger.debug(f"Payload: {payload}")

        try:
            # Update session with cookies
            if session_data.get('cookies'):
                for cookie_name, cookie_value in session_data['cookies'].items():
                    self.session.cookies.set(cookie_name, cookie_value)

            # Make API call
            response = self.session.post(
                api_endpoint,
                json=payload,
                timeout=30
            )

            # Handle response
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"API call successful for {site_url}")
                    return data
                except ValueError as e:
                    logger.error(f"Invalid JSON response from {site_url}: {e}")
                    return None

            elif response.status_code == 401 or response.status_code == 403:
                # Authentication failed - token likely expired
                logger.warning(f"Auth failed for {site_url} (status {response.status_code})")

                if retry_auth:
                    logger.info(f"Retrying with fresh login for {site_url}")
                    # Invalidate cache and retry
                    self.auth_manager.invalidate_session(site_url)
                    return self.fetch_bonuses(site_url, retry_auth=False)

                return None

            else:
                logger.error(f"API call failed for {site_url}: HTTP {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error calling {site_url}: {e}")
            raise  # Let retry decorator handle this

    def extract_bonuses_from_response(self, api_response: Dict) -> List[Dict]:
        """
        Extract bonus list from API response

        The actual structure varies by casino, but common patterns:
        - response['data']['bonuses']
        - response['bonuses']
        - response['data']['promotions']
        """
        if not api_response:
            return []

        bonuses = []

        # Try common response structures
        possible_paths = [
            ['data', 'bonuses'],
            ['bonuses'],
            ['data', 'promotions'],
            ['promotions'],
            ['data', 'offers'],
            ['offers'],
            ['data'],
        ]

        for path in possible_paths:
            try:
                value = api_response
                for key in path:
                    value = value.get(key)
                    if value is None:
                        break

                if value and isinstance(value, list):
                    bonuses = value
                    logger.debug(f"Found {len(bonuses)} bonuses at path: {' -> '.join(path)}")
                    break
            except (AttributeError, TypeError):
                continue

        return bonuses

    def parse_bonus(self, bonus_raw: Dict) -> Dict:
        """
        Parse raw bonus data into standardized format

        Extracts:
        - title
        - description
        - bonus_amount
        - rollover
        - max_withdrawal
        - bonus_code
        - expiration_date
        """
        # This is a generic parser - may need customization per casino
        parsed = {
            'title': bonus_raw.get('title') or bonus_raw.get('name') or bonus_raw.get('bonusName') or 'Unknown',
            'description': bonus_raw.get('description') or bonus_raw.get('desc') or bonus_raw.get('details') or '',
            'raw_data': str(bonus_raw),
        }

        # Extract financial values
        parsed['bonus_amount'] = self._extract_float(
            bonus_raw.get('amount') or bonus_raw.get('bonusAmount') or bonus_raw.get('value')
        )

        # Extract rollover (wagering requirement)
        parsed['rollover'] = self._extract_float(
            bonus_raw.get('rollover') or bonus_raw.get('wagering') or bonus_raw.get('wager') or
            bonus_raw.get('playthrough') or bonus_raw.get('wageringRequirement')
        )

        # Extract max withdrawal
        parsed['max_withdrawal'] = self._extract_float(
            bonus_raw.get('maxWithdrawal') or bonus_raw.get('max_withdrawal') or
            bonus_raw.get('withdrawalLimit') or bonus_raw.get('maxCashout')
        )

        # Extract other fields
        parsed['min_deposit'] = self._extract_float(bonus_raw.get('minDeposit') or bonus_raw.get('min_deposit'))
        parsed['max_bet'] = self._extract_float(bonus_raw.get('maxBet') or bonus_raw.get('max_bet'))

        parsed['bonus_code'] = bonus_raw.get('code') or bonus_raw.get('bonusCode') or bonus_raw.get('promoCode')
        parsed['requires_code'] = bool(parsed['bonus_code'])

        # Extract dates
        parsed['expiration_date'] = bonus_raw.get('expirationDate') or bonus_raw.get('validUntil') or bonus_raw.get('endDate')

        return parsed

    def _extract_float(self, value) -> Optional[float]:
        """Safely extract float from various formats"""
        if value is None:
            return None

        try:
            # Handle string values like "$100", "100.50", "100,000"
            if isinstance(value, str):
                value = value.replace('$', '').replace(',', '').replace('€', '').replace('£', '').strip()

            return float(value)
        except (ValueError, TypeError):
            return None
