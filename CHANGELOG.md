# 📋 Changelog

All notable changes to **TelegramUserCheckBot** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.3.0] — 2026-05-11

### 🔐 Fragment Collectible Username Verification

#### 🐛 Fixed
- **False positives for collectible/auction usernames** — Usernames like `@squatting` that are on Fragment auction were incorrectly reported as "available" because the `t.me` page shows the same generic contact page as truly available usernames
- **Root cause** — The detection only checked `t.me` pages, which cannot distinguish between freely registerable usernames and collectible usernames reserved in the Fragment/TON auction system

#### ✨ Added — Two-Stage Detection
- **Stage 1: t.me page scraping** (existing) — Profile photo, display name, subscriber count, bio analysis
- **Stage 2: Fragment verification** (new) — When t.me reports "available", cross-checks `fragment.com/username/{name}` for collectible status
  - `tm-status-avail` → Collectible username on auction → **Taken** (not freely available)
  - `tm-status-taken` → Registered collectible → **Taken** (already caught by stage 1)
  - `tm-status-unavail` → Not a collectible → **Available** ✅ (confirmed free to register)
- **`_check_fragment_collectible()` method** in `TelegramUsernameClient` — Verifies username against Fragment with timeout and error handling
- **Web App Fragment check** — `checkFragmentCollectible()` JS function mirrors Python logic for Web App users

#### 🔧 Changed
- **`checker/telegram_client.py`** — `_parse_page()` now calls Fragment verification before returning AVAILABLE
  - Added `_FRAGMENT_STATUS_RE` compiled regex for Fragment status parsing
  - Added `_FRAGMENT_URL` constant for Fragment check URL
  - Updated class docstring and `check()` method docstring with two-stage detection docs
- **`webapp/index.html`** — `checkAvailability()` now performs Fragment cross-check after t.me looks available
  - Added `checkFragmentCollectible()` async function
  - Uses same `tm-status-avail` regex pattern as Python code
- **`bot/handlers.py`** — Version bump to 3.3
- **`README.md`** — Updated architecture diagram, detection docs, feature table, and FAQ

#### 📝 Documentation
- **README.md** — Updated "How It Works" section with two-stage detection flow diagram
- **README.md** — Added Fragment Verification to Features table
- **README.md** — Added "What's new in v3.3?" FAQ entry
- **CHANGELOG.md** — Added v3.3.0 release notes

---

## [3.2.0] — 2026-05-04

### 🌐 Full Web App (Mini App) Overhaul

#### ✨ Added — Web App Features
- **Complete page-based UI** — Home, Single Check, Batch Check, Generate, Pattern, History, Settings
- **Batch checking** — Check up to 200 usernames at once with real-time progress bar
- **Generate & Check** — Random, Word Combo, and Mixed generation modes with configurable count (10/20/50/100)
- **Pattern templates** — Full pattern syntax with `?`=letter `#`=digit `!`=alnum, quick-tap symbol insert, and 6 preset templates
- **Session statistics** — Live stats bar on home page (checked, available, taken, hit rate)
- **Check history** — Scrollable history with timestamps, export to `.txt`, and clear
- **Settings page** — Configure username length, character set, generation mode, and request delay
- **Export functionality** — Download available names or full history as text files
- **Haptic feedback** — Impact and notification haptics on all interactions
- **Toast notifications** — Lightweight toast popups for actions
- **Smooth animations** — fadeIn, slideUp, bounce, and scale transitions
- **Telegram theme** — Automatic dark/light mode from Telegram theme colors
- **CloudStorage sync** — Settings persist via Telegram CloudStorage
- **Rich result cards** — Available names get Open, Copy, and Claim buttons
- **Progress tracking** — Real-time progress bar with speed indicator for batch/generate/pattern
- **Smart sorting** — Available names sorted to top in batch results
- **Concurrent checking** — 3 parallel requests with configurable delay

#### ✨ Added — Bot Handler
- **`batch_result` action** — Bot receives batch check summary with available names list
- **`generate_result` action** — Bot receives generation results with mode and stats
- **`pattern_result` action** — Bot receives pattern check results with template used
- **`export` action** — Bot receives exported available names for forwarding
- **Rich bot responses** — All webapp results render as formatted cards with inline keyboard buttons

#### 🔧 Changed
- **`webapp/index.html`** — Complete rewrite from single-checker to full mini-app
- **`bot/handlers.py`** — `handle_webapp_data()` expanded to handle 5 action types

---

## [3.1.0] — 2026-05-04

### 🔍 Inline Query Mode & Compatibility Fixes

#### ✨ Added
- **Inline Query Mode** — Check usernames directly from any chat using `@botname username`
  - Available usernames show green checkmark with claim link
  - Taken usernames show red X with suggestion to try `/generate`
  - Invalid usernames show validation rules
  - Error states handled gracefully with retry guidance

#### 🐛 Fixed
- **`InlineQueryResultArticle` crash** — Replaced deprecated `thumb_url` with `thumbnail_url` for `python-telegram-bot` v20+ compatibility
- **Stale v2.1 references** — Cleaned up outdated version refs in README banner and FAQ
- **Export button callback** — Fixed `send_finish` export button callback_data mapping

#### 🔧 Changed
- **Notebook cleanup** — Removed unused `fix_cell.py` from notebooks directory

---

## [3.0.0] — 2026-05-04

### 🎨 v3.0 — Full UI/UX Overhaul

#### ✨ Added
- **Unified renderers** — `render_start()`, `render_help()`, `render_settings()`, `render_stats()`, `render_history()`, `render_export()` eliminate code duplication between command and callback handlers
- **`safe_edit()` helper** — Silently handles "message is not modified" errors instead of crashing
- **`_render_check_result()` shared renderer** — Single source of truth for check results (used by `/check`, quick check, and retry callback)
- **Unified `_run_generation()` engine** — Handles `/generate`, `/pattern`, and all callback-triggered generation in one function (eliminated duplicate `_run_pattern_cb`)
- **Toast notifications** — Settings changes now show `query.answer()` toasts instead of replacing the entire settings screen
- **`/cancel` command** — Alias for `/stop`
- **Stop callback handler** — `x` callback from notifier buttons now properly handled

#### 🔧 Changed — Callback Data Overhaul
- **Shortened all callback_data** to stay well under Telegram's 64-byte limit:
  - `back_start` → `b`
  - `quick_generate` → `qg`
  - `settings` → `s`
  - `stats` → `st`
  - `history` → `hi`
  - `help` → `hp`
  - `export_hits` → `ex`
  - `set_length` → `sl`, `len_5` → `l:5`
  - `set_chars` → `sc`, `chars_default` → `ch:d`
  - `set_delay` → `sd`, `delay_1.0` → `d:1.0`
  - `set_workers` → `sw`, `workers_5` → `w:5`
  - `set_gen_mode` → `sg`, `gen_random` → `gm:random`
  - `pattern_menu` → `pm`
  - `pattern_tpl_user_????` → `pt:u4` (mapped via `tpl_map`)
  - `confirm_reset_settings` → `crs`, `reset_settings` → `rs`
  - `confirm_reset_stats` → `crst`, `reset_stats` → `rst`
  - `copy_username` → `c:username`
  - `retry_username` → `r:username`
  - `stop_check` → `x`
- **Payload format** — Uses colon separator (`l:5`, `ch:d`, `d:1.0`, `gm:random`, `c:name`, `r:name`) for compact variable data

#### 🐛 Fixed
- **"message is not modified" crash** — All `edit_text` calls wrapped in `safe_edit()`
- **stop_check callback not handled** — Added `x` handler
- **Duplicate code eliminated** — Settings/stats/history/help screens no longer rendered twice (once in command, once in callback)
- **Pattern template callback overflow** — `pattern_tpl_user_????` could exceed 64-byte limit; now uses `pt:u4` mapping

#### 📝 Documentation
- **CHANGELOG.md** — v3.0.0 release notes
- **README.md** — Version bump, updated features

---

## [2.1.1] — 2026-05-04

### 🐛 Colab/Jupyter Event Loop Fix

#### 🐛 Fixed
- **`Cannot close a running event loop`** — Fixed for Jupyter/Colab notebooks
  - `nest_asyncio.apply()` now called inside `run_bot()` before `run_polling()`
  - Auto-detects notebook environment and applies patch automatically
  - Auto-installs `nest_asyncio` if missing in notebook environments
- **run_bot.py** — Added `_is_notebook()` detection for Jupyter/Colab
- **Notebook Cell 9** — Updated bot launcher with `nest_asyncio` fix

#### 🔧 Changed
- **`bot/handlers.py`** — `run_bot()` now detects notebook environment
  - CLI: Uses standard `run_polling()` (blocking)
  - Notebook: Applies `nest_asyncio` then `run_polling()`
- **`run_bot.py`** — Imports `asyncio`, detects notebook shell

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
