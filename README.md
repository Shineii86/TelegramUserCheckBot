<div align="center">

![Telegram User Checker Banner](https://capsule-render.vercel.app/api?type=waving&color=0088cc,00aced&height=200&section=header&text=Telegram%20User%20Checker&fontSize=70&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Telegram%20Username%20Availability%20Checker%20v1.0&descSize=20)

[![Open in Google Colab](https://img.shields.io/badge/Open%20in-Colab-f9ab00?logo=google-colab)](https://colab.research.google.com/github/Shineii86/TelegramUserCheckBot/blob/main/notebooks/TelegramUserCheckBot.ipynb)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

[![GitHub Stars](https://img.shields.io/github/stars/Shineii86/TelegramUserCheckBot?style=social)](https://github.com/Shineii86/TelegramUserCheckBot/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Shineii86/TelegramUserCheckBot?style=social)](https://github.com/Shineii86/TelegramUserCheckBot/fork)

</div>

Check Telegram username availability at scale. CLI tool, Telegram bot, or Google Colab — your choice.

## 📖 Table of Contents

- [Overview](#-overview)
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
  - [Telegram Bot](#telegram-bot)
  - [CLI Tool](#cli-tool)
  - [Google Colab](#google-colab)
- [🤖 Bot Commands](#-bot-commands)
- [📚 CLI Reference](#-cli-reference)
- [⚙️ Configuration](#%EF%B8%8F-configuration)
- [📁 Project Structure](#-project-structure)
- [🌐 Proxy Support](#-proxy-support)
- [FAQ](#-faq)
- [License](#-license)

## 📋 Overview

TelegramUserCheckBot checks Telegram username availability at scale. Three ways to use it:

| Mode | Best For | Run It |
|------|----------|--------|
| 🤖 **Telegram Bot** | Personal use, phone alerts, interactive | `python run_bot.py` |
| 💻 **CLI Tool** | Automation, scripts, batch jobs | `python main.py` |
| 📓 **Google Colab** | Quick start, no install | [Open notebook](#google-colab) |

## ✨ Features

| Category | Feature | Description |
|----------|---------|-------------|
| 🔍 **Modes** | Single Check | Check one username via `/check` or CLI |
| | Batch Check | Check multiple via `/batch` or `--wordlist` |
| | Random Generation | Generate & check via `/generate` or CLI |
| 🚀 **Performance** | Multi-threading | Configurable worker count |
| | Proxy Rotation | HTTP/HTTPS/SOCKS from file or URL |
| | Smart Detection | HTML parsing for accurate results |
| | UA Rotation | Rotates across 6 browser fingerprints |
| 📲 **Telegram** | Interactive Bot | Full inline keyboard UI |
| | Instant Alerts | Hit notifications with stats |
| | Settings Panel | Change length, chars, delay in-chat |
| | Quick Check | Just type a username — no command needed! |
| 💾 **Output** | Auto-Save | Hits saved to file in real-time |
| 🛡️ **Safety** | Thread-Safe Stats | Locked counters, proper stop conditions |
| | Validation | Telegram username rules enforced |
| | Rate Limit Detection | Counted separately, not silently skipped |

## 🚀 Quick Start

### Telegram Bot

```bash
# Clone & install
git clone https://github.com/Shineii86/TelegramUserCheckBot.git
cd TelegramUserCheckBot
pip install -r requirements.txt

# Run the bot
python run_bot.py --token YOUR_BOT_TOKEN
```

Or from environment:

```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABC..."
python run_bot.py
```

Then open your bot in Telegram and send `/start`.

### CLI Tool

```bash
# Interactive (prompts for token/chat-id)
python main.py

# With arguments
python main.py --token TOKEN --chat-id CHAT_ID --mode hits --stop-after 5

# With config file
python main.py --config config.json

# With wordlist
python main.py --token TOKEN --chat-id CHAT_ID --wordlist usernames.txt
```

### Google Colab

Click the **Open in Colab** badge at the top. Run both cells. Done.

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with quick-action buttons |
| `/help` | Show all commands |
| `/check username` | Check a single username |
| `/batch user1,user2,user3` | Check multiple (comma-separated) |
| `/generate` | Generate & check 20 random usernames |
| `/generate 50` | Generate & check N random usernames |
| `/settings` | View/change length, chars, delay, workers |
| `/stats` | Show session statistics |
| `/stop` | Stop current batch/generation |

**Quick check:** Just type a username as a message (no command needed) — the bot checks it instantly.

**Inline keyboard:** Settings, stats, and help all have interactive button menus.

## 📚 CLI Reference

```
usage: python main.py [options]

Telegram:
  --token, -t          Telegram Bot Token
  --chat-id, -c        Telegram Chat ID

Username Generation:
  --length, -l         Username length (default: 5, min: 5, max: 32)
  --chars              Character set
  --no-start-underscore Don't avoid starting with underscore
  --no-end-underscore  Don't avoid ending with underscore

Wordlist:
  --wordlist, -w       Path to wordlist file
  --wordlist-url       URL to wordlist

Run Mode:
  --mode, -m           continuous | count | hits (default: continuous)
  --max-attempts       Max checks for 'count' mode (default: 100)
  --stop-after         Stop after N hits for 'hits' mode (default: 10)

Performance:
  --workers, -W        Thread count (default: 10)
  --delay, -d          Delay between requests in seconds (default: 1.0)
  --proxy-file         Path to proxy list file
  --proxy-url          URL to proxy list

Output:
  --output, -o         Output file (default: available_usernames.txt)
  --no-save            Don't save hits to file

Config:
  --config             Path to JSON config file
  --env                Load from environment variables only
```

## ⚙️ Configuration

### JSON Config File

```json
{
  "telegram_token": "1234567890:ABC...",
  "telegram_chat_id": "987654321",
  "username_length": 5,
  "character_set": "abcdefghijklmnopqrstuvwxyz0123456789_",
  "mode": "hits",
  "stop_after_hits": 10,
  "max_workers": 10,
  "delay": 1.0,
  "use_proxies": true,
  "proxy_url": "https://example.com/proxies.txt"
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | — | Your Telegram user ID |
| `USERNAME_LENGTH` | 5 | Length of generated usernames |
| `MODE` | continuous | continuous, count, or hits |
| `MAX_WORKERS` | 10 | Thread count |
| `DELAY` | 1.0 | Seconds between requests |
| `USE_PROXIES` | false | Enable proxy rotation |
| `PROXY_FILE` / `PROXY_URL` | — | Proxy source |

## 📁 Project Structure

```
TelegramUserCheckBot/
├── main.py                  # CLI entry point
├── run_bot.py               # Telegram bot entry point
├── requirements.txt
├── README.md
├── LICENSE
├── checker/                 # Core checking engine
│   ├── __init__.py
│   ├── config.py            # Configuration dataclass
│   ├── telegram_client.py   # Username availability checker (t.me scraping)
│   ├── telegram_notifier.py # Telegram notification helper (for CLI mode)
│   ├── generator.py         # Username generation + wordlist loading
│   ├── proxy.py             # Proxy manager
│   └── core.py              # CLI orchestrator (threading, stats)
├── bot/                     # Telegram bot interface
│   ├── __init__.py
│   └── handlers.py          # All /commands, callbacks, settings UI
└── notebooks/
    └── TelegramUserCheckBot.ipynb  # Colab notebook
```

## 🌐 Proxy Support

One proxy per line:

```
http://user:pass@host:port
http://host:port
socks5://host:port
```

- **CLI:** `--proxy-file proxies.txt` or `--proxy-url https://...`
- **Bot:** Configure via environment variables before starting.

⚠️ Free proxies are unreliable. Use private/residential proxies for serious hunting.

## ❓ FAQ

**How do I get a bot token?**
- Message [@BotFather](https://t.me/BotFather) on Telegram
- Send `/newbot`, choose a name and username
- Copy the token — that's your `TELEGRAM_BOT_TOKEN`

**How do I get my chat ID?**
- Message [@userinfobot](https://t.me/userinfobot) on Telegram
- It replies with your ID — that's your `TELEGRAM_CHAT_ID`

**What are Telegram's username rules?**
- 5-32 characters
- a-z, 0-9, and underscores only
- Must start with a letter
- No double underscores (`__`)
- Can't end with underscore

**How fast is it?**
- Depends on delay and rate limits
- With default settings (10 workers, 1s delay): ~10 usernames/sec
- Use proxies for higher throughput

**Does it need API credentials?**
- No! It checks via `t.me` page scraping — no Telegram API keys needed
- Only the bot token is needed for the interactive bot & notifications

## 📄 License

MIT License — see [LICENSE](/Shineii86/TelegramUserCheckBot/blob/main/LICENSE).

---

⚠️ **Disclaimer:** Educational and personal use only. Automated checks may be rate-limited by Telegram. Use responsibly and at your own risk.

<div align="center">

**Made with ❤️ by [@Shineii86](https://github.com/Shineii86)**

</div>
