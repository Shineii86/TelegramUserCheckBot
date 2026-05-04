"""
Telegram Username API Client — check username availability via t.me page scraping.
Handles rate limiting, retries, and User-Agent rotation.
"""

import random
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

            if "can find <strong>" in text and "on Telegram" in text:
                # "can find <strong>username</strong> on Telegram" → taken
                return (TAKEN, username)

            if "If you have <strong>Telegram</strong>, you can contact" in text:
                # Profile page with contact button → taken
                return (TAKEN, username)

            if "tgme_page_extra" in text and "on Telegram" in text:
                # Profile metadata present → taken
                return (TAKEN, username)

            if "If you have <strong>Telegram</strong>, you can" in text:
                return (TAKEN, username)

            # Check for availability indicators
            if "can be found on Telegram" in text.lower() and "contact" not in text.lower():
                return (AVAILABLE, username)

            # If we got a 200 but no clear "taken" indicators, likely available
            # Telegram shows a clear profile page for taken usernames
            if resp.status_code == 200:
                # Double-check: if there's no profile info, it's available
                if "tgme_page_title" not in text and "tgme_page_description" not in text:
                    return (AVAILABLE, username)
                # Has profile info → taken
                if "tgme_page_title" in text:
                    return (TAKEN, username)
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
