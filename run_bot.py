#!/usr/bin/env python3
"""
TelegramUserCheckBot — Telegram Bot Entry Point.

Usage:
    python run_bot.py                    # Interactive (prompts for token)
    python run_bot.py --token YOUR_TOKEN # From CLI arg
    TELEGRAM_BOT_TOKEN=... python run_bot.py  # From env var
"""

import argparse
import asyncio
import os
import sys

from bot.handlers import run_bot, VERSION


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


def _is_notebook() -> bool:
    """Detect if running inside Jupyter/Colab notebook."""
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter
        if shell == "Shell":
            return True  # Colab (sometimes)
    except (ImportError, NameError):
        pass
    # Also check for Colab's specific module
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        pass
    return False


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

    if _is_notebook():
        # In Jupyter/Colab, apply nest_asyncio to allow nested event loops
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            # If nest_asyncio not available, try to install it
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "nest_asyncio"])
                import nest_asyncio
                nest_asyncio.apply()
            except Exception:
                print("⚠️  Install nest_asyncio for notebook support: pip install nest_asyncio")

    run_bot(token)


if __name__ == "__main__":
    main()
