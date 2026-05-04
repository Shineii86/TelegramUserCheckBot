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

from bot.handlers import run_bot, BOT_USERNAME, VERSION


BANNER = f"""
\033[2;36m╔══════════════════════════════════════════════════╗
║                                                  ║
║   🤖  TelegramUserCheckBot  v{VERSION:<18}║
║                                                  ║
║   🔍  Username Availability Checker              ║
║   ⚡  Fast • Free • No API Keys                  ║
║                                                  ║
╚══════════════════════════════════════════════════╝\033[0m
"""


def main():
    parser = argparse.ArgumentParser(description="🤖 TelegramUserCheckBot — Telegram Bot")
    parser.add_argument("--token", "-t", help="Telegram Bot Token (from @BotFather)")
    args = parser.parse_args()

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN") or input("🔑 Bot Token: ").strip()
    if not token:
        print("\033[1;31m❌ Bot token is required.\033[0m", file=sys.stderr)
        print("\033[2m   Get one from @BotFather on Telegram.\033[0m", file=sys.stderr)
        sys.exit(1)

    print(BANNER)
    run_bot(token)


if __name__ == "__main__":
    main()
