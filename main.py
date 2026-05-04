#!/usr/bin/env python3
"""
TelegramUserCheckBot — Telegram Username Availability Checker.

Usage:
    python main.py                          # Interactive mode (prompts for config)
    python main.py --token X --chat-id Y    # CLI args
    python main.py --config config.json     # From JSON file
    python main.py --env                    # From environment variables

Environment variables:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, USERNAME_LENGTH, CHARACTER_SET,
    MODE, MAX_ATTEMPTS, STOP_AFTER_HITS, MAX_WORKERS, DELAY,
    USE_PROXIES, PROXY_FILE, PROXY_URL, USE_WORDLIST, WORDLIST_PATH,
    WORDLIST_URL, SAVE_HITS, OUTPUT_FILE, GENERATION_MODE, USE_PATTERN, PATTERN
"""

import argparse
import sys

from checker.config import Config
from checker.core import Checker


BANNER = """
\033[2;36m══════════════════════════════════════════════════
  🔍 TelegramUserCheckBot v3.0 — CLI Mode
══════════════════════════════════════════════════\033[0m
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="🔍 Telegram Username Availability Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Telegram
    parser.add_argument("--token", "-t", help="Telegram Bot Token (for notifications)")
    parser.add_argument("--chat-id", "-c", help="Telegram Chat ID (for notifications)")

    # Username generation
    parser.add_argument("--length", "-l", type=int, default=5, help="Username length (default: 5, min: 5, max: 32)")
    parser.add_argument("--chars", help="Character set for generation")
    parser.add_argument("--no-start-underscore", action="store_true", help="Avoid usernames starting with underscore")
    parser.add_argument("--no-end-underscore", action="store_true", help="Avoid usernames ending with underscore")

    # Generation mode
    parser.add_argument("--gen-mode", choices=["random", "word_combo", "mixed"],
                        help="Generation strategy (default: random)")
    parser.add_argument("--pattern", help="Pattern template: ?=letter #=digit !=alnum _=underscore")

    # Wordlist
    parser.add_argument("--wordlist", "-w", help="Path to username wordlist file")
    parser.add_argument("--wordlist-url", help="URL to username wordlist")

    # Run mode
    parser.add_argument("--mode", "-m", choices=["continuous", "count", "hits"], default="continuous",
                        help="Run mode (default: continuous)")
    parser.add_argument("--max-attempts", type=int, default=100, help="Max attempts for 'count' mode")
    parser.add_argument("--stop-after", type=int, default=10, help="Stop after N hits for 'hits' mode")

    # Performance
    parser.add_argument("--workers", "-W", type=int, default=10, help="Thread count (default: 10)")
    parser.add_argument("--delay", "-d", type=float, default=1.0, help="Delay between requests in seconds")
    parser.add_argument("--proxy-file", help="Path to proxy list file")
    parser.add_argument("--proxy-url", help="URL to proxy list")

    # Output
    parser.add_argument("--output", "-o", default="available_usernames.txt", help="Output file for hits")
    parser.add_argument("--no-save", action="store_true", help="Don't save hits to file")

    # Config file
    parser.add_argument("--config", help="Path to JSON config file")
    parser.add_argument("--env", action="store_true", help="Load config from environment variables only")

    return parser.parse_args()


def build_config(args) -> Config:
    """Build Config from CLI args, falling back to env/interactive."""

    if args.config:
        return Config.from_json(args.config)

    if args.env:
        return Config.from_env()

    # Start with env defaults
    cfg = Config.from_env()

    # Override with CLI args
    if args.token:
        cfg.telegram_token = args.token
    if args.chat_id:
        cfg.telegram_chat_id = args.chat_id
    if args.length:
        cfg.username_length = args.length
    if args.chars:
        cfg.character_set = args.chars
    if args.no_start_underscore:
        cfg.avoid_start_underscore = False
    if args.no_end_underscore:
        cfg.avoid_end_underscore = False
    if args.gen_mode:
        cfg.generation_mode = args.gen_mode
    if args.pattern:
        cfg.use_pattern = True
        cfg.pattern = args.pattern
    if args.wordlist:
        cfg.use_wordlist = True
        cfg.wordlist_path = args.wordlist
    if args.wordlist_url:
        cfg.use_wordlist = True
        cfg.wordlist_url = args.wordlist_url
    if args.mode:
        cfg.mode = args.mode
    if args.max_attempts:
        cfg.max_attempts = args.max_attempts
    if args.stop_after:
        cfg.stop_after_hits = args.stop_after
    if args.workers:
        cfg.max_workers = args.workers
    if args.delay is not None:
        cfg.delay = args.delay
    if args.proxy_file:
        cfg.use_proxies = True
        cfg.proxy_file = args.proxy_file
    if args.proxy_url:
        cfg.use_proxies = True
        cfg.proxy_url = args.proxy_url
    if args.output:
        cfg.output_file = args.output
    if args.no_save:
        cfg.save_hits = False

    # Interactive fallback if token/chat-id missing
    if not cfg.telegram_token:
        cfg.telegram_token = input("🔑 Telegram Bot Token: ").strip()
    if not cfg.telegram_chat_id:
        cfg.telegram_chat_id = input("💬 Telegram Chat ID: ").strip()

    return cfg


def main():
    print(BANNER)
    args = parse_args()
    config = build_config(args)

    # Validate pattern if provided
    if config.use_pattern:
        from checker.generator import UsernameGenerator
        valid, err = UsernameGenerator.validate_pattern(config.pattern)
        if not valid:
            print(f"\033[1;31m❌ Invalid pattern: {err}\033[0m", file=sys.stderr)
            print(f"\033[2m   Example: --pattern 'user_????' or --pattern 'test_##'\033[0m", file=sys.stderr)
            sys.exit(1)

    # Validate
    errors = config.validate()
    if errors:
        for e in errors:
            print(f"\033[1;31m❌ {e}\033[0m", file=sys.stderr)
        sys.exit(1)

    checker = Checker(config)

    # Handle Ctrl+C gracefully
    import signal
    signal.signal(signal.SIGINT, lambda *_: checker.stop())

    stats = checker.run()
    sys.exit(0 if stats.hits > 0 else 1)


if __name__ == "__main__":
    main()
