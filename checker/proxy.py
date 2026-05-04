"""
Proxy Manager — load, rotate, and manage HTTP/HTTPS/SOCKS proxies.
"""

import random
import requests
from typing import Optional, Dict, List


class ProxyManager:
    """Manages a pool of proxies for request rotation."""

    def __init__(self):
        self.proxies: List[str] = []

    def load_from_file(self, path: str) -> int:
        """Load proxies from a local file (one per line)."""
        try:
            with open(path, "r") as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            return len(self.proxies)
        except Exception as e:
            print(f"[!] Failed to load proxies from {path}: {e}")
            return 0

    def load_from_url(self, url: str) -> int:
        """Load proxies from a remote URL (one per line)."""
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            self.proxies = [line.strip() for line in resp.text.splitlines() if line.strip()]
            return len(self.proxies)
        except Exception as e:
            print(f"[!] Failed to load proxies from URL: {e}")
            return 0

    def get_random(self) -> Optional[Dict[str, str]]:
        """Return a random proxy dict for requests, or None if no proxies."""
        if not self.proxies:
            return None
        proxy = random.choice(self.proxies)
        return {"http": proxy, "https": proxy}

    @property
    def count(self) -> int:
        return len(self.proxies)
