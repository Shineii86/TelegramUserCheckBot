"""
Telegram Username API Client — check username availability via t.me page scraping.
Handles rate limiting, retries, and User-Agent rotation.

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
import requests
from typing import Optional, Tuple

from .proxy import ProxyManager

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

    def _get_ua(self) -> str:
        return random.choice(self.user_agents)

    def check(self, username: str, delay: float = 1.0) -> Tuple[str, str]:
        """
        Check a single username availability.

        Returns:
            (status, username) where status is AVAILABLE, TAKEN, INVALID, RATE_LIMITED, or ERROR
        """
        # Validate format first
        if not is_valid_username(username):
            return (INVALID, username)

        proxy = self.proxy_mgr.get_random() if self.proxy_mgr else None
        headers = {"User-Agent": self._get_ua()}
        url = self.TME_URL.format(username=username)

        try:
            resp = self._session.get(url, headers=headers, proxies=proxy, timeout=15)
            text = resp.text

            # Rate limiting detection
            if resp.status_code == 429:
                return (RATE_LIMITED, username)

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
                return (TAKEN, username)

            # No profile data → AVAILABLE (Telegram shows generic contact page)
            if resp.status_code == 200:
                return (AVAILABLE, username)

            return (ERROR, username)

        except requests.exceptions.Timeout:
            return (ERROR, username)
        except requests.exceptions.ConnectionError:
            return (ERROR, username)
        except Exception:
            return (ERROR, username)
        finally:
            if delay > 0:
                time.sleep(delay)
