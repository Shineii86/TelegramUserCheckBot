# 📋 Changelog

All notable changes to **TelegramUserCheckBot** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] — 2026-05-04

### 🧬 Generation Engine, Retry Logic & Rich Notifications

#### ✨ Added — Generation Engine
- **Word Combo Generator** — Adjective + noun + number combinations
  - 60+ adjectives (fast, cool, cyber, pixel, quantum, etc.)
  - 60+ nouns (coder, ninja, dragon, phoenix, etc.)
  - Smart number suffixes (1-999) with 60% probability
  - Always produces Telegram-valid usernames
- **Pattern Template Generator** — Generate from custom patterns
  - `/pattern user_????` — random letters
  - `/pattern test_##` — random digits
  - `/pattern my_!_!_name` — mixed alphanumeric
  - Full syntax: `?`=letter `#`=digit `!`=alnum `_`=underscore `@`=any
- **Mixed Generation Mode** — Round-robin across random + word combo
- **Smart Dedup** — Tracks all generated usernames to prevent duplicates
- **Generation Mode Selector** — New setting in /settings
  - 🎲 Random — Pure random characters
  - 🧠 Word Combos — Adjective+noun+number
  - 🌈 Mixed — Best of both worlds
- **Pattern Quick Templates** — One-tap pattern generation from menu
  - user_????, name_##_ab, my_!_!_!_tag, pro_####
- **New `/pattern` command** — Full pattern template support
  - Syntax help on empty invocation
  - Pattern validation with clear error messages
  - "Generate More" button for continuous pattern hunting

#### ✨ Added — Retry Logic & Backoff
- **Exponential backoff** on rate limits (base 2.0, max 30s)
  - Automatic retry up to 3 times per request
  - Jitter added to prevent thundering herd
  - UA rotation on each retry attempt
- **Auto-adjust delay** — Automatically increases delay after consecutive rate limits
  - 1+ rate limits → 2.0s delay
  - 3+ rate limits → 3.0s delay
  - 5+ rate limits → 5.0s delay
- **`recommended_delay` property** — Dynamic delay based on rate limit history
- **`is_rate_limited` property** — Track consecutive rate limit hits

#### ✨ Added — Rich Notifications
- **Rich hit alerts** — Expanded notification with inline buttons
  - "Open in Telegram" + "Copy Name" buttons
  - "Stats" + "Stop" buttons for control
  - Better formatting with emoji and dividers
- **Progress notifications** — Periodic updates every N checks
  - Configurable interval via `notify_progress_interval`
  - Progress bar with percentage (count mode)
- **Rate limit notification** — Alert when rate limited
- **Enhanced finish notification** — Summary with hit rate + export button
- **`send_progress()` method** — Progress bar in notifications
- **`send_rate_limit()` method** — Rate limit warnings
- **Configurable notifications** — `notify_on_hit`, `notify_on_finish`, `notify_progress_interval`

#### ✨ Added — CLI Improvements
- **Colored banner** — Startup banner with cyan borders
- **Spinner animation** — ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ during checks
- **Live stats line** — Overwriting progress line in count mode
- **Colored summary** — Emoji-rich completion report
- **Speed display** — Checks/sec in summary
- **Hit rate display** — Percentage in summary
- **Pattern support** — `--pattern` CLI argument
- **Generation mode** — `--gen-mode` CLI argument
- **Better error messages** — Pattern validation with examples

#### 🔧 Changed
- **`checker/telegram_client.py`** — Added retry with exponential backoff
  - `_calculate_backoff()` helper function
  - Max 3 retries per request
  - UA rotation between retries
  - Rate limit tracking (consecutive count)
- **`checker/generator.py`** — Major expansion
  - Added `_ADJECTIVES` and `_NOUNS` word lists
  - Added `_PATTERN_MAP` for pattern template parsing
  - `word_combo_stream()` — Word combination generator
  - `pattern_stream()` — Pattern template generator
  - `mixed_stream()` — Mixed strategy generator
  - `_is_unique()` — Smart dedup with seen set
  - `validate_pattern()` — Pattern validation
  - `seen_count` property and `clear_seen()` method
- **`checker/config.py`** — New config fields
  - `generation_mode` — "random", "word_combo", "mixed"
  - `use_pattern` / `pattern` — Pattern template support
  - `max_retries` / `retry_backoff_base` — Retry configuration
  - `auto_adjust_delay` — Dynamic delay adjustment
  - `notify_on_hit` / `notify_on_finish` / `notify_progress_interval`
- **`checker/core.py`** — Enhanced CLI output
  - `_print_banner()` — Colored startup banner
  - `_spinner()` — Animated spinner
  - `_progress_bar()` — Colored progress bar
  - `_print_live_stats()` — Overwriting progress line
  - `_get_generator_stream()` — Mode-aware stream selection
  - Pattern support in `_username_source()`
  - Better summary with emoji, speed, hit rate
- **`checker/telegram_notifier.py`** — Rich notifications
  - `_post()` helper for Bot API calls
  - `buttons` parameter on `send()` method
  - Enhanced `send_hit()` with inline buttons
  - Enhanced `send_finish()` with summary + export button
  - New `send_progress()` and `send_rate_limit()` methods
- **`bot/handlers.py`** — New commands and UI
  - `/pattern` command with full syntax help
  - `_run_generation()` helper for mode-aware generation
  - `_run_pattern_generation()` for pattern-based flow
  - Generation mode selector in settings
  - Pattern menu with quick templates
  - Pattern_more callback for continuous hunting
  - Settings shows gen mode and pattern
  - Reset clears gen mode and pattern
  - Help updated with /pattern and pattern syntax
  - Start menu includes /pattern
- **`main.py`** — New CLI arguments
  - `--gen-mode` — random/word_combo/mixed
  - `--pattern` — Pattern template
  - Pattern validation before run
  - Startup banner
- **`run_bot.py`** — Better startup banner
- **`config.example.json`** — New fields documented
- **`requirements.txt`** — Version ranges pinned

#### 📝 Documentation
- **README.md** — Updated to v2.1
  - New features in Features table
  - New /pattern command in Bot Commands
  - Updated "What's new?" FAQ
- **CHANGELOG.md** — Added v2.1.0 release notes

---

## [2.0.0] — 2026-05-04

### 🎨 UI/UX Overhaul & New Commands

#### ✨ Added — New Bot Commands
- **`/history`** — View recent check log with status indicators and timestamps
  - Shows last 15 checks with ✅/❌/🚫/⚠️/💥 status emojis
  - Relative timestamps ("just now", "5m ago", "2h ago")
  - Total checked & hits summary at bottom
- **`/ping`** — Check bot responsiveness and uptime
  - Shows uptime (formatted as Xm Xs / Xh Xm)
  - Displays bot version and user's session stats
  - "All systems operational!" status message
- **`/about`** — Bot info, version, and credits
  - Links to GitHub repo and star page
  - Feature summary and author attribution

#### ✨ Added — Enhanced UX Features
- **Time-aware greeting** — `/start` adapts message based on time of day (Good morning/afternoon/evening/Hey)
- **Speed tracking** — Real-time checks/sec displayed during batch and generate operations
- **Elapsed time** — Total time shown in batch/generate completion reports
- **Retry on error** — One-tap "🔄 Retry" button when a check fails
- **Copy username** — "📋 Copy Name" button on available username results
- **Export hits button** — Added to batch/generate completion screens (not just stats)
- **Session uptime** — Displayed in `/ping` command
- **History tracking** — All checks automatically logged with timestamps
- **Batch size limit** — Max 200 usernames per batch with clear error message
- **Status emoji helper** — Consistent emoji mapping across all status displays
- **Uptime formatter** — Human-readable duration formatting (Xs, Xm Xs, Xh Xm)

#### 🔧 Changed — Bot UI Improvements
- **`/start` welcome screen** — Redesigned with "Quick Actions" section header
  - Added `/ping` and `/history` to command list
  - Uses `· · ·` thin divider for visual separation
  - Lightning/shield/sparkle tagline: "Fast ⚡ Reliable 🛡️ Free ✨"
- **`/help` command** — Added `/history`, `/ping`, `/about` entries with descriptions
  - Added author credit line with heart emoji
- **`/check` results** — Enhanced result cards
  - Available: Added "Copy Name" button alongside "Check Another"
  - Taken: Added "Try /generate" suggestion with Generate button
  - Rate Limited: Added Settings button for proxy configuration
  - Error: Added Retry button for one-tap re-check
  - Checking animation: Shows "Scanning t.me/{username}" during check
- **`/batch` improvements** — Enhanced progress display
  - Real-time speed indicator (X.X/sec) during batch
  - Elapsed time in completion report
  - Export hits button on completion
  - Generate button alongside Check Another
  - Max 200 limit with clear error message
  - Better input parsing (supports spaces and newlines as separators)
- **`/generate` improvements** — Enhanced generation flow
  - "Conjuring usernames..." placeholder text
  - Real-time speed indicator during generation
  - Elapsed time in completion report
  - Export hits button on completion
  - Generate More button preserved after completion
- **`/stats` layout** — Restructured button grid
  - Export Hits + History on top row
  - Reset Stats + Back on bottom row
- **`/settings` layout** — Added Back button alongside Reset All
- **Quick check (plain text)** — Enhanced all result types
  - Available: Session stats shown, Copy button added
  - Taken: Suggestion to use /generate with Generate button
  - Rate Limited: Settings button for proxy setup
  - Error: Retry button for re-check
  - Checking animation: Thin divider separator
- **Callback handlers** — New handlers added
  - `copy_{username}` — Shows username in code block for easy copying
  - `retry_{username}` — Re-checks a username from error state
  - `history` — Shows check history from inline button
- **Button layouts** — Improved keyboard grids
  - Start screen: 3 rows (Quick Check/Generate, Settings/Stats, History/Help)
  - Help screen: Added /about reference
  - Length selector: Added 15, 20, 25 options
  - Chars selector: Shows star emoji on current selection
  - All settings screens: Show current value in description
- **Message formatting** — Consistent use of dividers
  - THICK_DIVIDER (━) for section headers
  - DIVIDER (─) for sub-sections
  - THIN_DIVIDER (· · ·) for subtle separations

#### 📝 Documentation
- **README.md** — Updated to v2.0
  - Added version badge
  - New Features table entries (history, ping, about, retry, copy, speed tracking, etc.)
  - New Bot Commands table entries (/history, /ping, /about)
  - Updated "What's new in v2.0?" FAQ entry
  - Updated batch limits note
  - Updated speed FAQ with real-time display mention
- **CHANGELOG.md** — Added v2.0.0 release notes

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
- Telegram username validation (5–32 chars, a-z/0-9/_, letter start, no double `__`)
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
