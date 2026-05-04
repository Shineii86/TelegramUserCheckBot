"""
Configuration — all settings in one place.
Supports environment variables, CLI args, and defaults.
"""

import os
import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    """Bot configuration with sensible defaults."""

    # Telegram Bot (for notifications & interactive bot)
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # Username generation
    username_length: int = 5
    character_set: str = "abcdefghijklmnopqrstuvwxyz0123456789_"
    avoid_start_underscore: bool = True
    avoid_end_underscore: bool = True
    avoid_double_underscore: bool = True
    avoid_start_number: bool = False
    min_length: int = 5
    max_length: int = 32
    generation_mode: str = "random"  # "random", "word_combo", "mixed"

    # Pattern templates
    use_pattern: bool = False
    pattern: str = ""  # e.g., "user_????", "test_##"

    # Wordlist
    use_wordlist: bool = False
    wordlist_path: str = ""
    wordlist_url: str = ""

    # Run mode: "continuous", "count", "hits"
    mode: str = "continuous"
    max_attempts: int = 100
    stop_after_hits: int = 10

    # Performance
    max_workers: int = 10
    delay: float = 1.0
    use_proxies: bool = False
    proxy_file: str = ""
    proxy_url: str = ""

    # Retry behavior
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    auto_adjust_delay: bool = True  # Auto-increase delay on rate limits

    # Output
    save_hits: bool = True
    output_file: str = "available_usernames.txt"

    # Notification style
    notify_on_hit: bool = True
    notify_on_finish: bool = True
    notify_progress_interval: int = 50  # Send progress update every N checks

    # User-Agent rotation
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ])

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables."""
        return cls(
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            username_length=int(os.getenv("USERNAME_LENGTH", "5")),
            character_set=os.getenv("CHARACTER_SET", "abcdefghijklmnopqrstuvwxyz0123456789_"),
            avoid_start_underscore=os.getenv("AVOID_START_UNDERSCORE", "true").lower() == "true",
            avoid_end_underscore=os.getenv("AVOID_END_UNDERSCORE", "true").lower() == "true",
            avoid_double_underscore=os.getenv("AVOID_DOUBLE_UNDERSCORE", "true").lower() == "true",
            avoid_start_number=os.getenv("AVOID_START_NUMBER", "false").lower() == "true",
            min_length=int(os.getenv("MIN_LENGTH", "5")),
            max_length=int(os.getenv("MAX_LENGTH", "32")),
            generation_mode=os.getenv("GENERATION_MODE", "random"),
            use_pattern=os.getenv("USE_PATTERN", "false").lower() == "true",
            pattern=os.getenv("PATTERN", ""),
            use_wordlist=os.getenv("USE_WORDLIST", "false").lower() == "true",
            wordlist_path=os.getenv("WORDLIST_PATH", ""),
            wordlist_url=os.getenv("WORDLIST_URL", ""),
            mode=os.getenv("MODE", "continuous"),
            max_attempts=int(os.getenv("MAX_ATTEMPTS", "100")),
            stop_after_hits=int(os.getenv("STOP_AFTER_HITS", "10")),
            max_workers=int(os.getenv("MAX_WORKERS", "10")),
            delay=float(os.getenv("DELAY", "1.0")),
            use_proxies=os.getenv("USE_PROXIES", "false").lower() == "true",
            proxy_file=os.getenv("PROXY_FILE", ""),
            proxy_url=os.getenv("PROXY_URL", ""),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_backoff_base=float(os.getenv("RETRY_BACKOFF_BASE", "2.0")),
            auto_adjust_delay=os.getenv("AUTO_ADJUST_DELAY", "true").lower() == "true",
            save_hits=os.getenv("SAVE_HITS", "true").lower() == "true",
            output_file=os.getenv("OUTPUT_FILE", "available_usernames.txt"),
            notify_on_hit=os.getenv("NOTIFY_ON_HIT", "true").lower() == "true",
            notify_on_finish=os.getenv("NOTIFY_ON_FINISH", "true").lower() == "true",
            notify_progress_interval=int(os.getenv("NOTIFY_PROGRESS_INTERVAL", "50")),
        )

    @classmethod
    def from_json(cls, path: str) -> "Config":
        """Load config from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> List[str]:
        """Validate config. Returns list of error messages."""
        errors = []
        if not self.telegram_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not self.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID is required")
        if self.mode not in ("continuous", "count", "hits"):
            errors.append(f"Invalid MODE: {self.mode}")
        if self.max_workers < 1:
            errors.append("MAX_WORKERS must be >= 1")
        if self.delay < 0:
            errors.append("DELAY must be >= 0")
        if self.username_length < 5:
            errors.append("USERNAME_LENGTH must be >= 5 (Telegram minimum)")
        if self.username_length > 32:
            errors.append("USERNAME_LENGTH must be <= 32 (Telegram maximum)")
        if self.generation_mode not in ("random", "word_combo", "mixed"):
            errors.append(f"Invalid GENERATION_MODE: {self.generation_mode}")
        if self.use_pattern and not self.pattern:
            errors.append("PATTERN is required when USE_PATTERN is true")
        if self.max_retries < 0:
            errors.append("MAX_RETRIES must be >= 0")
        if self.notify_progress_interval < 1:
            errors.append("NOTIFY_PROGRESS_INTERVAL must be >= 1")
        return errors
