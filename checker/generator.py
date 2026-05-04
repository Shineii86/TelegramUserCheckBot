"""
Username Generator — random generation and wordlist loading.
Generates Telegram-compliant usernames (5-32 chars, a-z, 0-9, underscores).
"""

import random
import requests
from typing import Iterator, List


class UsernameGenerator:
    """Generates or loads usernames to check."""

    def __init__(
        self,
        length: int = 5,
        chars: str = "abcdefghijklmnopqrstuvwxyz0123456789_",
        avoid_start_underscore: bool = True,
        avoid_end_underscore: bool = True,
        avoid_double_underscore: bool = True,
        avoid_start_number: bool = False,
    ):
        self.length = max(5, min(32, length))  # Telegram: 5-32 chars
        self.chars = chars
        self.filters = []

        # Always enforce Telegram rules
        self.filters.append(lambda u: u[0].isalpha())  # Must start with letter
        self.filters.append(lambda u: len(u) >= 5)      # Min 5 chars

        if avoid_start_underscore:
            self.filters.append(lambda u: u[0] != "_")
        if avoid_end_underscore:
            self.filters.append(lambda u: u[-1] != "_")
        if avoid_double_underscore:
            self.filters.append(lambda u: "__" not in u)
        if avoid_start_number:
            self.filters.append(lambda u: not u[0].isdigit())

    def _is_valid(self, username: str) -> bool:
        """Check if username passes all filters."""
        return all(f(username) for f in self.filters)

    def random_stream(self) -> Iterator[str]:
        """Yield random usernames indefinitely."""
        # Ensure we always have at least one alpha char for the start
        alpha_chars = [c for c in self.chars if c.isalpha()]
        if not alpha_chars:
            alpha_chars = list("abcdefghijklmnopqrstuvwxyz")

        while True:
            # First char must be a letter (Telegram rule)
            first = random.choice(alpha_chars)
            rest = "".join(random.choice(self.chars) for _ in range(self.length - 1))
            username = first + rest
            if self._is_valid(username):
                yield username

    @staticmethod
    def load_from_file(path: str) -> List[str]:
        """Load usernames from a local file (one per line)."""
        try:
            with open(path, "r") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"[!] Failed to load wordlist from {path}: {e}")
            return []

    @staticmethod
    def load_from_url(url: str) -> List[str]:
        """Load usernames from a remote URL (one per line)."""
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return [line.strip() for line in resp.text.splitlines() if line.strip()]
        except Exception as e:
            print(f"[!] Failed to load wordlist from URL: {e}")
            return []
