"""Authentication Manager with 6-hour session caching"""
import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session

from ..models import SessionCache
from .errors import map_auth_error, map_exception_to_error

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Manages authentication and session caching for casino mirror sites

    Implements the "Swarm Strategy" - tries primary username first, then all alternates
    """

    def __init__(self, db: Session, usernames: list, passwords: list, cache_hours: int = 6):
        """
        Args:
            db: Database session
            usernames: List of usernames to try (primary will be selected per-site)
            passwords: List of passwords (must match usernames 1:1)
            cache_hours: Hours to cache sessions
        """
        self.db = db
        self.usernames = usernames
        self.passwords = passwords
        self.credentials = list(zip(usernames, passwords))  # [(user1, pass1), (user2, pass2), ...]
        self.cache_hours = cache_hours

    def get_session(self, site_url: str, primary_username: str = None) -> Tuple[Optional[Dict], Optional[Tuple[str, str, str, str]]]:
        """
        Get valid session for a site (from cache or new login)

        Implements Swarm Strategy: tries primary username first, then all alternates

        Args:
            site_url: URL of the site
            primary_username: Last known working username for this site (or None)

        Returns: (session_data, error_info)
            - session_data: dict with access_token, access_id, merchant_id, cookies, successful_username (or None)
            - error_info: tuple of (code, emoji, short_desc, long_desc) (or None)
        """
        # Check cache first
        cached_session = self._get_cached_session(site_url)
        if cached_session and not cached_session.is_expired():
            logger.info(f"Using cached session for {site_url}")
            return {
                'access_token': cached_session.access_token,
                'access_id': cached_session.access_id,
                'merchant_id': cached_session.merchant_id,
                'cookies': json.loads(cached_session.cookies) if cached_session.cookies else {},
                'successful_username': None  # From cache, username already known
            }, None

        # Cache miss or expired - perform fresh login with Swarm Strategy
        logger.info(f"Performing fresh login for {site_url} (Swarm Strategy)")
        session_data, error_info = self._perform_login_swarm(site_url, primary_username)

        if session_data:
            self._cache_session(site_url, session_data)
            return session_data, None

        return None, error_info

    def _get_cached_session(self, site_url: str) -> Optional[SessionCache]:
        """Retrieve session from cache"""
        return self.db.query(SessionCache).filter(
            SessionCache.mirror_site_url == site_url,
            SessionCache.is_valid == True
        ).first()

    def _cache_session(self, site_url: str, session_data: Dict):
        """Cache session credentials for 6 hours"""
        # Remove old cache entry if exists
        old_cache = self._get_cached_session(site_url)
        if old_cache:
            self.db.delete(old_cache)

        # Create new cache entry
        cache_entry = SessionCache(
            mirror_site_url=site_url,
            access_token=session_data['access_token'],
            access_id=session_data['access_id'],
            merchant_id=session_data['merchant_id'],
            cookies=json.dumps(session_data.get('cookies', {})),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=self.cache_hours),
            is_valid=True
        )

        self.db.add(cache_entry)
        self.db.commit()
        logger.info(f"Cached session for {site_url} (valid for {self.cache_hours} hours)")

    def _perform_login_swarm(self, site_url: str, primary_username: str = None) -> Tuple[Optional[Dict], Optional[Tuple[str, str, str, str]]]:
        """
        Perform login with Swarm Strategy: try primary first, then all alternates

        Args:
            site_url: URL to login to
            primary_username: Last known working username (or None to start with first)

        Returns: (session_data_with_username, error_info)
            session_data includes 'successful_username' field
        """
        # Order credentials: primary first, then all others
        ordered_credentials = []
        tried_usernames = []

        if primary_username:
            # Find primary credentials
            for username, password in self.credentials:
                if username == primary_username:
                    ordered_credentials.append((username, password))
                    break

        # Add all other credentials
        for username, password in self.credentials:
            if username != primary_username:
                ordered_credentials.append((username, password))

        # Try each credential set
        last_error = None
        for username, password in ordered_credentials:
            tried_usernames.append(username)
            logger.debug(f"Trying username {username} for {site_url}")

            session_data, error_info = self._perform_login(site_url, username, password)

            if session_data:
                # Success! Add the successful username to the session data
                session_data['successful_username'] = username
                session_data['alts_tried'] = json.dumps(tried_usernames)
                logger.info(f"✓ Login successful with username {username} for {site_url}")
                return session_data, None
            else:
                # This username failed, remember error and try next
                last_error = error_info
                logger.debug(f"✗ Login failed with username {username} for {site_url}")

        # All usernames failed
        logger.error(f"✗ All {len(tried_usernames)} usernames failed for {site_url}")
        # Return the error from the last attempt
        return None, last_error if last_error else map_auth_error('login_failed')

    def _perform_login(self, site_url: str, username: str, password: str) -> Tuple[Optional[Dict], Optional[Tuple[str, str, str, str]]]:
        """
        Perform actual login to casino site with specific credentials

        Steps:
        1. Load homepage and extract merchantId from HTML
        2. Submit login form
        3. Extract accessToken and accessId from response
        4. Return session data

        Returns: (session_data, error_info)
        """
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        try:
            # Step 1: Load homepage to get merchantId
            logger.debug(f"Loading homepage: {site_url}")
            response = session.get(site_url, timeout=30)
            response.raise_for_status()

            merchant_id = self._extract_merchant_id(response.text)
            if not merchant_id:
                error_info = map_auth_error('no_merchant_id')
                logger.error(f"Could not extract merchantId from {site_url}")
                return None, error_info

            logger.debug(f"Extracted merchantId: {merchant_id}")

            # Step 2: Perform login
            login_data = {
                'username': username,
                'password': password,
                'merchantId': merchant_id,
            }

            # Try common login endpoints
            login_endpoints = [
                f"{site_url}/api/v1/index.php",
                f"{site_url}/api/login",
                f"{site_url}/login",
            ]

            access_token = None
            access_id = None
            last_error = None

            for login_url in login_endpoints:
                try:
                    logger.debug(f"Attempting login at: {login_url}")
                    login_response = session.post(login_url, json=login_data, timeout=30)

                    if login_response.status_code == 200:
                        login_result = login_response.json()

                        # Extract tokens from response
                        access_token = login_result.get('accessToken') or login_result.get('token')
                        access_id = login_result.get('accessId') or login_result.get('userId') or login_result.get('id')

                        if access_token and access_id:
                            logger.info(f"Login successful at {login_url}")
                            break
                        else:
                            last_error = map_auth_error('no_login_data')
                    else:
                        # Map HTTP error
                        last_error = map_exception_to_error(requests.HTTPError(response=login_response))
                except Exception as e:
                    logger.debug(f"Login attempt failed at {login_url}: {e}")
                    last_error = map_exception_to_error(e)
                    continue

            if not access_token or not access_id:
                error_info = last_error if last_error else map_auth_error('login_failed')
                logger.error(f"Login failed for {site_url}")
                return None, error_info

            # Step 3: Return session data
            return {
                'access_token': access_token,
                'access_id': access_id,
                'merchant_id': merchant_id,
                'cookies': session.cookies.get_dict()
            }, None

        except Exception as e:
            error_info = map_auth_error('exception', e)
            logger.error(f"Login error for {site_url}: {e}")
            return None, error_info

    def _extract_merchant_id(self, html: str) -> Optional[str]:
        """
        Extract merchantId from HTML

        Common locations:
        - window.merchantId = "123"
        - var config = { merchantId: "123" }
        - data-merchant-id="123"
        """
        import re

        # Pattern 1: window.merchantId or var merchantId
        patterns = [
            r'merchantId["\']?\s*[:=]\s*["\']?(\w+)["\']?',
            r'merchant_id["\']?\s*[:=]\s*["\']?(\w+)["\']?',
            r'data-merchant-id=["\'](\w+)["\']',
            r'MERCHANT_ID["\']?\s*[:=]\s*["\']?(\w+)["\']?',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)

        # Pattern 2: Try parsing as JSON config
        try:
            soup = BeautifulSoup(html, 'lxml')
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'merchantId' in script.string:
                    # Try to extract from JSON-like structure
                    match = re.search(r'["\']merchantId["\']\s*:\s*["\']?(\w+)["\']?', script.string)
                    if match:
                        return match.group(1)
        except Exception:
            pass

        return None

    def invalidate_session(self, site_url: str):
        """Invalidate cached session (force fresh login next time)"""
        cached_session = self._get_cached_session(site_url)
        if cached_session:
            cached_session.is_valid = False
            self.db.commit()
            logger.info(f"Invalidated session cache for {site_url}")
