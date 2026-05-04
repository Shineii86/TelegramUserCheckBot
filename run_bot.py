#!/usr/bin/env python3
"""
TelegramUserCheckBot — Telegram Bot Entry Point.

Usage:
    python run_bot.py                    # Interactive (prompts for token)
    python run_bot.py --token YOUR_TOKEN # From CLI arg
    TELEGRAM_BOT_TOKEN=... python run_bot.py  # From env var
"""

import argparse
import os
import sys

from bot.handlers import run_bot


def main():
    parser = argparse.ArgumentParser(description="🤖 TelegramUserCheckBot — Telegram Bot")
    parser.add_argument("--token", "-t", help="Telegram Bot Token (from @BotFather)")
    args = parser.parse_args()

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN") or input("🔑 Bot Token: ").strip()
    if not token:
        print("❌ Bot token is required.", file=sys.stderr)
        sys.exit(1)

    run_bot(token)


if __name__ == "__main__":
    main()
