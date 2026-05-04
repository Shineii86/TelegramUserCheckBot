"""
Username Generator — random generation, pattern templates, word combos, and wordlist loading.
Generates Telegram-compliant usernames (5-32 chars, a-z, 0-9, underscores).
"""

import random
import re
import requests
from typing import Iterator, List, Set


# Common English words for word-combo generation
_ADJECTIVES = [
    "fast", "cool", "dark", "fire", "wild", "blue", "red", "gold", "neo", "pro",
    "mega", "ultra", "hyper", "cyber", "pixel", "crypto", "quantum", "storm",
    "shadow", "frost", "blaze", "viper", "wolf", "eagle", "titan", "alpha",
    "omega", "prime", "turbo", "swift", "bright", "sharp", "steel", "iron",
    "cosmic", "lunar", "solar", "nova", "star", "glow", "volt", "spark",
    "fierce", "silent", "rapid", "grand", "royal", "noble", "epic", "bold",
]

_NOUNS = [
    "coder", "hacker", "maker", "player", "hunter", "rider", "driver", "pilot",
    "ghost", "ninja", "knight", "wizard", "dragon", "phoenix", "tiger", "lion",
    "hawk", "bear", "fox", "wolf", "snake", "panther", "falcon", "shark",
    "king", "queen", "lord", "boss", "chief", "master", "legend", "hero",
    "tech", "dev", "bit", "byte", "data", "code", "net", "web", "app", "hub",
    "zone", "realm", "space", "world", "verse", "core", "node", "link", "sync",
    "cloud", "stack", "flow", "wave", "pulse", "signal", "matrix", "vector",
]

# Pattern template placeholders:
#   ? = random letter (a-z)
#   # = random digit (0-9)
#   _ = literal underscore
#   @ = random char from charset (a-z, 0-9, _)
#   ! = random letter or digit (a-z, 0-9)
_PATTERN_MAP = {
    "?": lambda: random.choice("abcdefghijklmnopqrstuvwxyz"),
    "#": lambda: random.choice("0123456789"),
    "_": lambda: "_",
    "@": lambda: random.choice("abcdefghijklmnopqrstuvwxyz0123456789_"),
    "!": lambda: random.choice("abcdefghijklmnopqrstuvwxyz0123456789"),
}


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
        self._seen: Set[str] = set()  # Dedup tracking

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

    def _is_unique(self, username: str) -> bool:
        """Check if username hasn't been generated before (smart dedup)."""
        if username in self._seen:
            return False
        self._seen.add(username)
        return True

    def random_stream(self) -> Iterator[str]:
        """Yield random usernames indefinitely (with dedup)."""
        alpha_chars = [c for c in self.chars if c.isalpha()]
        if not alpha_chars:
            alpha_chars = list("abcdefghijklmnopqrstuvwxyz")

        while True:
            first = random.choice(alpha_chars)
            rest = "".join(random.choice(self.chars) for _ in range(self.length - 1))
            username = first + rest
            if self._is_valid(username) and self._is_unique(username):
                yield username

    def word_combo_stream(self) -> Iterator[str]:
        """Generate usernames by combining adjectives + nouns + optional numbers.

        Examples: fastcoder42, coolhacker, wildwolf7, proninja
        """
        while True:
            adj = random.choice(_ADJECTIVES)
            noun = random.choice(_NOUNS)
            base = adj + noun

            # Add random number suffix sometimes
            if random.random() < 0.6:
                num = random.randint(1, 999)
                username = f"{base}{num}"
            else:
                username = base

            # Ensure length is valid (5-32)
            if len(username) < 5:
                username = username + str(random.randint(100, 999))
            if len(username) > 32:
                username = username[:32]

            if self._is_valid(username) and self._is_unique(username):
                yield username

    def pattern_stream(self, pattern: str) -> Iterator[str]:
        """Generate usernames from a pattern template.

        Pattern syntax:
            ? = random letter (a-z)
            # = random digit (0-9)
            _ = literal underscore
            @ = random char (a-z, 0-9, _)
            ! = random letter or digit (a-z, 0-9)
            any other char = literal

        Examples:
            "user_????"  → user_abcd, user_wxyz, ...
            "test_##"    → test_42, test_07, ...
            "??_pro_##"  → ab_pro_42, xy_pro_07, ...
            "name_!_!_!" → name_a3b, name_x7y, ...
        """
        # Build parts list
        parts = []
        for char in pattern:
            if char in _PATTERN_MAP:
                parts.append(_PATTERN_MAP[char])
            else:
                parts.append(lambda c=char: c)

        while True:
            username = "".join(p() for p in parts)

            # Ensure starts with letter (Telegram rule)
            if username and not username[0].isalpha():
                # Replace first char with a letter
                alpha_chars = [c for c in self.chars if c.isalpha()]
                if alpha_chars:
                    username = random.choice(alpha_chars) + username[1:]

            # Length checks
            if len(username) < 5:
                continue
            if len(username) > 32:
                username = username[:32]

            if self._is_valid(username) and self._is_unique(username):
                yield username

    def mixed_stream(self, count: int = 20) -> Iterator[str]:
        """Generate usernames using a mix of strategies.

        Yields from multiple streams in round-robin for variety.
        """
        streams = [
            self.random_stream(),
            self.word_combo_stream(),
            self.word_combo_stream(),  # Double weight for word combos
        ]

        idx = 0
        while True:
            username = next(streams[idx % len(streams)])
            idx += 1
            yield username

    @property
    def seen_count(self) -> int:
        """Number of unique usernames generated so far."""
        return len(self._seen)

    def clear_seen(self):
        """Reset the dedup set."""
        self._seen.clear()

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

    @staticmethod
    def validate_pattern(pattern: str) -> tuple:
        """Validate a pattern template. Returns (is_valid, error_message)."""
        if not pattern:
            return False, "Pattern cannot be empty"
        if len(pattern) > 32:
            return False, "Pattern too long (max 32 chars)"
        if len(pattern) < 5:
            return False, "Pattern too short (min 5 chars)"

        # Check that pattern produces a valid start char
        first = pattern[0]
        if first in ("#", "@"):
            return False, "Pattern must start with a letter or literal (not # or @)"
        if first == "!":
            return False, "Pattern must start with a letter or literal (not !)"

        return True, ""
