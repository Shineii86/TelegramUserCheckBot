# 📋 Changelog

All notable changes to **TelegramUserCheckBot** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-05-04

### 🎉 Initial Release

#### ✨ Added
- **Telegram Bot** — Interactive bot with full inline keyboard UI
  - `/check username` — Single username check
  - `/batch user1,user2,user3` — Batch checking (comma-separated)
  - `/generate [N]` — Generate & check random usernames
  - `/settings` — View/change length, chars, delay, workers via buttons
  - `/stats` — Session statistics with reset option
  - `/stop` — Stop any running operation
  - Quick check — Just type a username as a message
  - Inline keyboard menus for all settings
- **CLI Tool** — Full-featured command-line interface
  - Interactive mode (prompts for config)
  - CLI arguments mode
  - JSON config file support
  - Environment variables support
  - Three run modes: `continuous`, `count`, `hits`
  - Color-coded console output
- **Google Colab Notebook** — Zero-install browser experience
  - Step-by-step guided flow
  - Single username quick checker
  - Wordlist batch checker
  - Config sliders and dropdowns
- **Core Engine** (`checker/`)
  - Username availability detection via `t.me` page scraping
  - Profile data analysis (photo, name, subscribers, bio)
  - Multi-threaded checking with configurable workers
  - Thread-safe stats counters
  - Proxy rotation (HTTP/HTTPS/SOCKS)
  - User-Agent rotation (6 browser fingerprints)
  - Username generation with Telegram rules enforcement
  - Wordlist loading from file or URL
  - Real-time hit notifications via Telegram Bot API
  - Auto-save hits to file

#### 🛡️ Safety
- Telegram username validation (5-32 chars, a-z/0-9/_, letter start, no double `__`)
- Rate limit detection (counted separately, not silently skipped)
- Graceful Ctrl+C handling
- Thread-safe counters with locks

#### 📁 Project Structure
```
TelegramUserCheckBot/
├── main.py                  # CLI entry point
├── run_bot.py               # Telegram bot entry point
├── requirements.txt
├── config.example.json
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
├── checker/                 # Core checking engine
│   ├── config.py
│   ├── telegram_client.py
│   ├── telegram_notifier.py
│   ├── generator.py
│   ├── proxy.py
│   └── core.py
├── bot/                     # Telegram bot interface
│   └── handlers.py
└── notebooks/
    └── TelegramUserCheckBot.ipynb
```

---

## [Unreleased]

### 🔮 Planned
- SOCKS5 proxy authentication support
- Export results to CSV/JSON formats
- Username pattern templates (e.g., `prefix_???_suffix`)
- Rate limit auto-retry with exponential backoff
- Multi-language support (i18n)
- Web dashboard for monitoring
- Parallel proxy pool rotation
- Username similarity suggestions (Levenshtein distance)

---

<div align="center">

**[⬆ Back to Top](#-changelog)**

</div>
