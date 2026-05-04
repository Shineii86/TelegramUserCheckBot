"""
Telegram Username API Client — check username availability via t.me page scraping.
Handles rate limiting, retries with exponential backoff, and User-Agent rotation.

Detection method:
    TAKEN indicators (any of these means the username is registered):
      - Profile photo (tgme_page_photo_image)       → real user/channel/group
      - Display name (tgme_page_title with content)  → real user/channel/group
      - Subscriber/member count (tgme_page_extra)    → channel/group
      - Actual bio text (not just generic contact)    → user with bio

    AVAILABLE indicators:
      - Only generic "If you have Telegram, you can contact @username right away."
      - No profile photo, no display name, no subscriber count, no real bio
      - Page has tgme_page_icon (generic icon) instead of tgme_page_photo
"""

import random
import re
import time
import logging
import requests
from typing import Optional, Tuple

from .proxy import ProxyManager

logger = logging.getLogger(__name__)

# Result constants
AVAILABLE = "available"
TAKEN = "taken"
INVALID = "invalid"
RATE_LIMITED = "rate_limited"
ERROR = "error"

# Telegram username rules: 5-32 chars, a-z, 0-9, underscores
# Must start with a letter, no double underscores, no trailing underscore
VALID_USERNAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_")

# Compiled regex patterns for detection
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_PHOTO_RE = re.compile(r'tgme_page_photo_image', re.IGNORECASE)
_NAME_TITLE_RE = re.compile(r'tgme_page_title[^>]*>(.*?)</div>', re.IGNORECASE | re.DOTALL)
_SUBS_RE = re.compile(r'tgme_page_extra[^>]*>(.*?)</div>', re.IGNORECASE | re.DOTALL)
_DESC_RE = re.compile(r'tgme_page_description[^>]*dir="auto">(.*?)</div>', re.IGNORECASE | re.DOTALL)

# Retry configuration
MAX_RETRIES = 3
BASE_BACKOFF = 2.0  # seconds
MAX_BACKOFF = 30.0  # seconds


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text).strip()


def is_valid_username(username: str) -> bool:
    """Check if username follows Telegram's rules."""
    if len(username) < 5 or len(username) > 32:
        return False
    if not username[0].isalpha():
        return False
    if username.endswith("_"):
        return False
    if "__" in username:
        return False
    return all(c in VALID_USERNAME_CHARS for c in username)


def _calculate_backoff(attempt: int, base: float = BASE_BACKOFF, maximum: float = MAX_BACKOFF) -> float:
    """Calculate exponential backoff with jitter."""
    backoff = min(base * (2 ** attempt), maximum)
    jitter = random.uniform(0, backoff * 0.3)
    return backoff + jitter


class TelegramUsernameClient:
    """Checks Telegram username availability via t.me page scraping."""

    TME_URL = "https://t.me/{username}"

    def __init__(self, user_agents: list, proxy_manager: Optional[ProxyManager] = None):
        self.user_agents = user_agents or [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        self.proxy_mgr = proxy_manager
        self._session = requests.Session()
        self._consecutive_rate_limits = 0

    def _get_ua(self) -> str:
        return random.choice(self.user_agents)

    def _parse_page(self, text: str, username: str) -> str:
        """Parse t.me page HTML to determine username status."""
        # Check for actual profile data (indicates a registered username)
        has_photo = bool(_PHOTO_RE.search(text))

        name_match = _NAME_TITLE_RE.search(text)
        has_name = bool(name_match and _strip_html(name_match.group(1)))

        subs_match = _SUBS_RE.search(text)
        has_subs = bool(subs_match and ("subscribers" in subs_match.group(1).lower()
                                        or "members" in subs_match.group(1).lower()))

        desc_match = _DESC_RE.search(text)
        has_bio = False
        if desc_match:
            desc_text = _strip_html(desc_match.group(1))
            # Generic contact message = not a real bio
            generic = f"you can contact @{username.lower()} right away"
            has_bio = bool(desc_text) and generic not in desc_text.lower()

        # Any real profile data → TAKEN
        if has_photo or has_name or has_subs or has_bio:
            return TAKEN

        # No profile data → AVAILABLE (Telegram shows generic contact page)
        return AVAILABLE

    def check(self, username: str, delay: float = 1.0) -> Tuple[str, str]:
        """
        Check a single username availability with retry logic.

        Returns:
            (status, username) where status is AVAILABLE, TAKEN, INVALID, RATE_LIMITED, or ERROR
        """
        # Validate format first
        if not is_valid_username(username):
            return (INVALID, username)

        proxy = self.proxy_mgr.get_random() if self.proxy_mgr else None
        headers = {"User-Agent": self._get_ua()}
        url = self.TME_URL.format(username=username)

        last_status = ERROR

        for attempt in range(MAX_RETRIES):
            try:
                resp = self._session.get(url, headers=headers, proxies=proxy, timeout=15)
                text = resp.text

                # Rate limiting detection
                if resp.status_code == 429:
                    self._consecutive_rate_limits += 1
                    last_status = RATE_LIMITED

                    # If we have retries left, wait with exponential backoff
                    if attempt < MAX_RETRIES - 1:
                        backoff = _calculate_backoff(attempt)
                        logger.warning(f"Rate limited on @{username}, retry {attempt + 1}/{MAX_RETRIES} in {backoff:.1f}s")
                        time.sleep(backoff)
                        # Rotate UA for retry
                        headers["User-Agent"] = self._get_ua()
                        proxy = self.proxy_mgr.get_random() if self.proxy_mgr else None
                        continue
                    return (RATE_LIMITED, username)

                # Success — reset consecutive rate limit counter
                self._consecutive_rate_limits = 0

                # Parse the page
                result = self._parse_page(text, username)

                if resp.status_code == 200:
                    return (result, username)

                # Non-200 but not 429 — error
                return (ERROR, username)

            except requests.exceptions.Timeout:
                last_status = ERROR
                if attempt < MAX_RETRIES - 1:
                    backoff = _calculate_backoff(attempt)
                    logger.warning(f"Timeout on @{username}, retry {attempt + 1}/{MAX_RETRIES} in {backoff:.1f}s")
                    time.sleep(backoff)
                    headers["User-Agent"] = self._get_ua()
                    continue

            except requests.exceptions.ConnectionError:
                last_status = ERROR
                if attempt < MAX_RETRIES - 1:
                    backoff = _calculate_backoff(attempt)
                    logger.warning(f"Connection error on @{username}, retry {attempt + 1}/{MAX_RETRIES} in {backoff:.1f}s")
                    time.sleep(backoff)
                    headers["User-Agent"] = self._get_ua()
                    continue

            except Exception as e:
                logger.debug(f"Unexpected error checking @{username}: {e}")
                last_status = ERROR
                break

        # Apply delay after all attempts
        if delay > 0:
            time.sleep(delay)

        return (last_status, username)

    @property
    def is_rate_limited(self) -> bool:
        """Check if we're hitting consecutive rate limits."""
        return self._consecutive_rate_limits >= 3

    @property
    def recommended_delay(self) -> float:
        """Get recommended delay based on rate limit history."""
        if self._consecutive_rate_limits >= 5:
            return 5.0
        elif self._consecutive_rate_limits >= 3:
            return 3.0
        elif self._consecutive_rate_limits >= 1:
            return 2.0
        return 1.0
