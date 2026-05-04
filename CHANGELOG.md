# 📋 Changelog

All notable changes to **TelegramUserCheckBot** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-05-04

### 🚀 Colab, Detection & Stability Update

#### ✨ Added — Colab Notebook
- **Telegram Bot Launcher (Step 3B)** — Run the interactive bot directly from Colab
  - Paste bot token, click ▶️, bot stays alive while cell runs
  - Styled info box with instructions
  - Commands: `/start`, `/check`, `/batch`, `/generate`, `/settings`, `/stats`, `/stop`
- **Textarea Widget (Step 5)** — Multi-line username input using `ipywidgets.Textarea`
  - Replaces broken `{type:"raw"}` param (Colab doesn't render it as an input field)
  - Clickable **🔍 Run Check** button to trigger batch checking
- **Step-by-step notebook flow** — 6 clear steps with descriptions
  - Step 1: Setup (clone + install)
  - Step 2: Configuration (sliders, dropdowns, toggles)
  - Step 3: Run Checker (CLI mode)
  - Step 3B: Launch Telegram Bot
  - Step 4: Quick Single Check
  - Step 5: Batch Check (textarea + button)

#### 🐛 Fixed
- **`TimeoutError` in `as_completed`** — Dynamic timeout based on delay (`max(delay*2, 5.0s)`)
  - Previously crashed when delay > 1.0s (the hardcoded timeout)
  - Now gracefully handles slow requests and processes completed futures
- **Username detection accuracy** — Improved `t.me` page parsing
  - Checks for actual profile data: photo, display name, subscribers, bio
  - Generic "Contact @username" pages without profile data → correctly detected as available
  - Channels/groups detected via subscriber count and descriptions
  - Users with profiles (photo, name, bio) → correctly detected as taken

#### 🔧 Changed
- **`checker/telegram_client.py`** — Rewritten detection logic
  - Uses compiled regex patterns for faster parsing
  - `_strip_html()` helper for clean text extraction
  - Checks 4 indicators: photo, name_title, subscribers, bio
  - Generic contact messages excluded from bio detection
- **`checker/core.py`** — Improved thread pool timeout handling
  - `TimeoutError` caught and processed gracefully
  - Completed futures processed even when some are still pending
- **`notebooks/TelegramUserCheckBot.ipynb`** — Complete rewrite
  - All cells restructured with proper metadata IDs
  - Removed broken `{type:"raw"}` param
  - Added `ipywidgets` for interactive multi-line input

#### 📝 Documentation
- **README.md** — Updated to v1.1
  - Added Colab Notebook Guide section with step-by-step table
  - Added Step 3B (bot launcher) documentation
  - Added Step 5 (textarea) documentation
  - New FAQ: "Can I use it without installing anything?"
  - New FAQ: "How do I run the bot from Colab?"
  - Updated Features table with Colab-specific features
- **CHANGELOG.md** — Added v1.1.0 release notes

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
