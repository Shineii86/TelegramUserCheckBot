<div align="center">

![Telegram User Checker Banner](https://capsule-render.vercel.app/api?type=waving&color=0088cc,00aced&height=200&section=header&text=Telegram%20User%20Check%20Bot&fontSize=70&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Telegram%20Username%20Availability%20Checker%20v2.1&descSize=20)

[![Open in Google Colab](https://img.shields.io/badge/Open%20in-Colab-f9ab00?logo=google-colab&logoColor=white)](https://colab.research.google.com/github/Shineii86/TelegramUserCheckBot/blob/main/notebooks/TelegramUserCheckBot.ipynb)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](https://github.com/Shineii86/TelegramUserCheckBot/pulls)
[![Version](https://img.shields.io/badge/Version-3.0-blue.svg)](https://github.com/Shineii86/TelegramUserCheckBot/releases)

[![GitHub Stars](https://img.shields.io/github/stars/Shineii86/TelegramUserCheckBot?style=social)](https://github.com/Shineii86/TelegramUserCheckBot/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Shineii86/TelegramUserCheckBot?style=social)](https://github.com/Shineii86/TelegramUserCheckBot/fork)
[![GitHub Issues](https://img.shields.io/github/issues/Shineii86/TelegramUserCheckBot?style=social)](https://github.com/Shineii86/TelegramUserCheckBot/issues)

**The ultimate Telegram username availability checker — CLI, Telegram Bot, or Google Colab.**

*Mass-check usernames with multi-threading, proxy rotation, pattern templates, and instant Telegram alerts.*

</div>

---

## 📖 Table of Contents

- [🧠 How It Works](#-how-it-works)
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
  - [Telegram Bot](#-telegram-bot)
  - [CLI Tool](#-cli-tool)
  - [Google Colab](#-google-colab)
- [📓 Colab Notebook Guide](#-colab-notebook-guide)
- [🤖 Bot Commands](#-bot-commands)
- [🧬 Generation Modes](#-generation-modes)
- [📚 CLI Reference](#-cli-reference)
- [⚙️ Configuration](#️-configuration)
- [📁 Project Structure](#-project-structure)
- [🌐 Proxy Support](#-proxy-support)
- [📌 Username Rules](#-username-rules)
- [❓ FAQ](#-faq)
- [📄 License](#-license)

---

## 🧠 How It Works

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│  Generate / Load │────▶│  Check t.me  │────▶│  Parse Result │
│   Usernames      │     │   Pages      │     │  (HTML)       │
└─────────────────┘     └──────────────┘     └───────┬───────┘
                                                      │
                              ┌────────────────────────┼────────────────┐
                              ▼                        ▼                ▼
                        ┌──────────┐            ┌──────────┐      ┌──────────┐
                        │ ✅ Available│          │ ❌ Taken  │      │ ⚠️ Error  │
                        └──────────┘            └──────────┘      └──────────┘
```

**Detection method:** Scrapes `t.me/{username}` pages and analyzes profile data:

| Indicator | Found? | Result |
|-----------|--------|--------|
| 📸 Profile photo | Yes | **Taken** |
| 👤 Display name | Yes | **Taken** |
| 📊 Subscriber count | Yes | **Taken** (channel/group) |
| 📝 Bio/description | Yes | **Taken** |
| 🚫 No profile data | Yes | **Available** ✅ |

> **No API keys needed** for checking — only the Bot Token is needed for the interactive bot & notifications.

---

## ✨ Features

| Category | Feature | Description |
|----------|---------|-------------|
| 🔍 **Modes** | Single Check | Check one username via `/check` or CLI |
| | Batch Check | Check multiple via `/batch` or `--wordlist` |
| | Random Generation | Generate & check via `/generate` or CLI |
| | Pattern Templates | Generate from patterns via `/pattern` |
| | Word Combos | Adjective + noun + number names |
| 🧬 **Generation** | Random | Pure random character usernames |
| | Word Combos | `fastcoder42`, `coolhacker`, `wildwolf7` |
| | Mixed | Round-robin across strategies for variety |
| | Pattern Templates | `user_????`, `test_##`, `my_!_!_name` |
| | Smart Dedup | Never checks the same username twice |
| 🚀 **Performance** | Multi-threading | Configurable worker count (1–50) |
| | Proxy Rotation | HTTP/HTTPS/SOCKS from file or URL |
| | Smart Detection | Profile data analysis for accurate results |
| | UA Rotation | Rotates across 6 browser fingerprints |
| | Retry Logic | Exponential backoff on rate limits (3 retries) |
| | Auto Delay | Automatically increases delay when rate limited |
| 📲 **Telegram** | Interactive Bot | Full inline keyboard UI |
| | Rich Hit Alerts | Notifications with Open/Stop buttons |
| | Progress Updates | Periodic stats every N checks |
| | Settings Panel | Change length, chars, delay, gen mode in-chat |
| | Quick Check | Just type a username — no command needed! |
| | Check History | View recent checks with `/history` |
| | Bot Status | Check uptime & responsiveness with `/ping` |
| | About Page | Bot info & credits via `/about` |
| | Retry on Error | One-tap retry for failed checks |
| | Copy to Clipboard | Quick-copy available usernames |
| | Speed Tracking | Real-time checks/sec in batch & generate |
| | Time-Aware Greeting | Welcome message adapts to time of day |
| 📓 **Colab** | One-Click Bot | Launch Telegram bot directly from notebook |
| | Textarea Input | Multi-line username input with Run button |
| | Config Sliders | Sliders, dropdowns, and toggles for all settings |
| 💾 **Output** | Auto-Save | Hits saved to file in real-time |
| | Export Hits | Export all available names from any session |
| 🛡️ **Safety** | Thread-Safe Stats | Locked counters, proper stop conditions |
| | Validation | Telegram username rules enforced (5–32 chars) |
| | Rate Limit Detection | Counted separately, not silently skipped |
| | Batch Limits | Max 200 per batch to prevent abuse |

---

## 🚀 Quick Start

### 🤖 Telegram Bot

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

### 💻 CLI Tool

```bash
# Interactive (prompts for token/chat-id)
python main.py

# With arguments
python main.py --token TOKEN --chat-id CHAT_ID --mode hits --stop-after 5

# With pattern template
python main.py --token TOKEN --chat-id CHAT_ID --pattern "user_????" --mode hits

# With word combo generation
python main.py --token TOKEN --chat-id CHAT_ID --gen-mode word_combo

# With config file
python main.py --config config.json

# With wordlist
python main.py --token TOKEN --chat-id CHAT_ID --wordlist usernames.txt
```

### 📓 Google Colab

Click the **Open in Colab** badge at the top. No install needed — runs in your browser.

---

## 📓 Colab Notebook Guide

The Colab notebook has **6 steps** — each one is a standalone cell:

| Step | What It Does | Effort |
|------|-------------|--------|
| **📦 Step 1** | Install & clone repo | Click ▶️ |
| **⚙️ Step 2** | Configure settings (sliders, dropdowns) | Fill in token |
| **🚀 Step 3** | Run multi-threaded checker (CLI mode) | Click ▶️ |
| **🤖 Step 3B** | Launch Telegram bot (interactive mode) | Paste token, click ▶️ |
| **🧪 Step 4** | Quick single username check | Type name, click ▶️ |
| **📋 Step 5** | Check multiple usernames (textarea) | Paste names, click Run |

### Step 3B — Launch Telegram Bot

The easiest way to run the bot — no terminal, no install:

1. Get a token from [@BotFather](https://t.me/BotFather) → `/newbot`
2. Paste it in the token field
3. Click ▶️ to run the cell
4. Open Telegram → find your bot → send `/start`
5. **Keep the cell running** — stopping it kills the bot

### Step 5 — Check Multiple Usernames

A textarea widget lets you paste multiple usernames (one per line), then click the **🔍 Run Check** button to check them all.

---

## 🤖 Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome screen with quick-action buttons | `/start` |
| `/help` | Show all commands, rules & pattern syntax | `/help` |
| `/check username` | Check a single username | `/check coolname123` |
| `/batch user1,user2,user3` | Check multiple (comma/space/newline) | `/batch abc,xyz,test` |
| `/generate` | Generate & check 20 random usernames | `/generate` |
| `/generate 50` | Generate & check N random usernames | `/generate 50` |
| `/generate 50 word_combo` | Generate with word combos | `/generate 50 word_combo` |
| `/pattern template` | Generate from pattern template | `/pattern user_????` |
| `/pattern tmpl 50` | Pattern with custom count | `/pattern test_## 50` |
| `/settings` | View/change length, chars, delay, gen mode | `/settings` |
| `/stats` | Show session statistics with hit rate | `/stats` |
| `/history` | View recent check log with timestamps | `/history` |
| `/ping` | Check bot uptime & responsiveness | `/ping` |
| `/about` | Bot info, version, and credits | `/about` |
| `/stop` | Stop current batch/generation | `/stop` |

**💡 Quick check:** Just type a username as a message (no command needed) — the bot checks it instantly.

**🎮 Inline keyboard:** All commands have interactive button menus. Settings, stats, and results include action buttons for common workflows.

---

## 🧬 Generation Modes

### 🎲 Random (default)
Pure random characters from the configured character set.
```
a8kx2m, q3z9bp, w7fn1t
```

### 🧠 Word Combos
Adjective + noun + optional number. Produces memorable, pronounceable names.
```
fastcoder42, coolhacker, wildwolf7, proninja, cyberdragon99
```

### 🌈 Mixed
Round-robin across random and word combo strategies for maximum variety.

### 🔮 Pattern Templates
Generate from custom patterns using special characters:

| Symbol | Meaning | Example |
|--------|---------|---------|
| `?` | Random letter (a-z) | `user_????` → `user_abcd` |
| `#` | Random digit (0-9) | `test_##` → `test_42` |
| `!` | Random letter or digit | `name_!_!` → `name_a3` |
| `@` | Any valid char (a-z, 0-9, _) | `x@` → `x_k` |
| `_` | Literal underscore | `my_name` → `my_name` |
| Other | Literal character | `pro_v1` → `pro_v1` |

**Examples:**
```
/pattern user_????        → user_abcd, user_wxyz, ...
/pattern test_##_ab       → test_42_ab, test_07_ab, ...
/pattern my_!_!_!_tag     → my_a3b_tag, my_x7y_tag, ...
/pattern pro_####         → pro_1234, pro_5678, ...
```

---

## 📚 CLI Reference

```
usage: python main.py [options]

Telegram:
  --token, -t           Telegram Bot Token
  --chat-id, -c         Telegram Chat ID

Username Generation:
  --length, -l          Username length (default: 5, min: 5, max: 32)
  --chars               Character set
  --no-start-underscore Don't avoid starting with underscore
  --no-end-underscore   Don't avoid ending with underscore
  --gen-mode            random | word_combo | mixed (default: random)
  --pattern             Pattern template (?=letter #=digit !=alnum)

Wordlist:
  --wordlist, -w        Path to wordlist file
  --wordlist-url        URL to wordlist

Run Mode:
  --mode, -m            continuous | count | hits (default: continuous)
  --max-attempts        Max checks for 'count' mode (default: 100)
  --stop-after          Stop after N hits for 'hits' mode (default: 10)

Performance:
  --workers, -W         Thread count (default: 10)
  --delay, -d           Delay between requests in seconds (default: 1.0)
  --proxy-file          Path to proxy list file
  --proxy-url           URL to proxy list

Output:
  --output, -o          Output file (default: available_usernames.txt)
  --no-save             Don't save hits to file

Config:
  --config              Path to JSON config file
  --env                 Load from environment variables only
```

---

## ⚙️ Configuration

### JSON Config File

```json
{
  "telegram_token": "1234567890:ABC...",
  "telegram_chat_id": "987654321",
  "username_length": 5,
  "character_set": "abcdefghijklmnopqrstuvwxyz0123456789_",
  "generation_mode": "random",
  "use_pattern": false,
  "pattern": "",
  "mode": "hits",
  "stop_after_hits": 10,
  "max_workers": 10,
  "delay": 1.0,
  "max_retries": 3,
  "retry_backoff_base": 2.0,
  "auto_adjust_delay": true,
  "use_proxies": true,
  "proxy_url": "https://example.com/proxies.txt",
  "save_hits": true,
  "output_file": "available_usernames.txt",
  "notify_on_hit": true,
  "notify_on_finish": true,
  "notify_progress_interval": 50
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | — | Your Telegram user ID |
| `USERNAME_LENGTH` | 5 | Length of generated usernames |
| `CHARACTER_SET` | `a-z0-9_` | Characters for random generation |
| `GENERATION_MODE` | random | random, word_combo, or mixed |
| `USE_PATTERN` | false | Enable pattern template mode |
| `PATTERN` | — | Pattern template string |
| `MODE` | continuous | continuous, count, or hits |
| `MAX_ATTEMPTS` | 100 | Max checks for `count` mode |
| `STOP_AFTER_HITS` | 10 | Stop after N hits for `hits` mode |
| `MAX_WORKERS` | 10 | Thread count |
| `DELAY` | 1.0 | Seconds between requests |
| `MAX_RETRIES` | 3 | Retries per request on failure |
| `RETRY_BACKOFF_BASE` | 2.0 | Base seconds for exponential backoff |
| `AUTO_ADJUST_DELAY` | true | Auto-increase delay on rate limits |
| `USE_PROXIES` | false | Enable proxy rotation |
| `PROXY_FILE` / `PROXY_URL` | — | Proxy source |
| `SAVE_HITS` | true | Save available names to file |
| `OUTPUT_FILE` | available_usernames.txt | Output filename |
| `NOTIFY_ON_HIT` | true | Send Telegram alert on available username |
| `NOTIFY_ON_FINISH` | true | Send Telegram alert when check completes |
| `NOTIFY_PROGRESS_INTERVAL` | 50 | Send progress update every N checks |

---

## 📁 Project Structure

```
TelegramUserCheckBot/
├── main.py                  # CLI entry point
├── run_bot.py               # Telegram bot entry point
├── requirements.txt         # Python dependencies
├── config.example.json      # Sample configuration
├── README.md                # This file
├── CHANGELOG.md             # Version history
├── LICENSE                  # MIT License
├── .gitignore               # Git ignore rules
│
├── checker/                 # 🔧 Core checking engine
│   ├── __init__.py
│   ├── config.py            # Configuration dataclass (env, JSON, CLI)
│   ├── telegram_client.py   # Username checker with retry & backoff
│   ├── telegram_notifier.py # Rich Telegram notifications with buttons
│   ├── generator.py         # Random, word combo, pattern, & mixed generation
│   ├── proxy.py             # Proxy manager (HTTP/SOCKS rotation)
│   └── core.py              # CLI orchestrator (threading, stats, banner)
│
├── bot/                     # 🤖 Telegram bot interface
│   ├── __init__.py
│   └── handlers.py          # All /commands, callbacks, settings UI
│
└── notebooks/               # 📓 Google Colab
    └── TelegramUserCheckBot.ipynb
```

---

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

---

## 📌 Username Rules

Telegram enforces strict username rules:

| Rule | Valid | Invalid |
|------|-------|---------|
| Length: 5–32 chars | `hello` | `ab` (too short) |
| Start with letter | `test123` | `1abc` (starts with number) |
| a-z, 0-9, `_` only | `my_name` | `my-name` (hyphen) |
| No double `__` | `my_name` | `my__name` (double underscore) |
| Can't end with `_` | `my_name` | `my_name_` (trailing underscore) |

---

## ❓ FAQ

<details>
<summary><b>How do I get a bot token?</b></summary>

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, choose a name and username
3. Copy the token — that's your `TELEGRAM_BOT_TOKEN`
</details>

<details>
<summary><b>How do I get my chat ID?</b></summary>

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It replies with your ID — that's your `TELEGRAM_CHAT_ID`
</details>

<details>
<summary><b>How fast is it?</b></summary>

- With default settings (10 workers, 1.0s delay): ~10 usernames/sec
- With 50 workers and 0.5s delay: ~100 usernames/sec
- Use proxies to avoid rate limits at higher speeds
- Speed is displayed in real-time during batch/generate operations
- Auto-adjusts delay when rate limited (exponential backoff)
</details>

<details>
<summary><b>Does it need Telegram API credentials?</b></summary>

**No!** It checks via `t.me` page scraping — no Telegram API keys needed. Only the bot token is needed for the interactive bot & notifications.
</details>

<details>
<summary><b>Why are short random names mostly taken?</b></summary>

Telegram has billions of users and bots. Short usernames (5–8 chars) are almost all registered. Try:
- Longer names (10+ chars)
- **Word combo mode:** `/generate 50 word_combo` — produces memorable names like `fastcoder42`
- **Pattern templates:** `/pattern my_!_!_!_name` — structured names with variety
- Mix of letters + numbers: `ab12cd34`
- Underscore patterns: `my_name_123`
</details>

<details>
<summary><b>What are pattern templates?</b></summary>

Patterns let you generate usernames from a template. Use special characters as placeholders:
- `?` = random letter, `#` = random digit, `!` = letter or digit
- Example: `/pattern user_????` generates `user_abcd`, `user_wxyz`, etc.
- Example: `/pattern pro_####` generates `pro_1234`, `pro_5678`, etc.
- Any other character is used literally: `/pattern test_v1_??` → `test_v1_ab`
</details>

<details>
<summary><b>What's the difference between generation modes?</b></summary>

- **Random** — Pure random characters. Fast but names are hard to remember.
- **Word Combos** — Adjective + noun + number. Produces pronounceable names like `coolhacker` or `wildwolf7`. Better for finding names people actually want.
- **Mixed** — Combines both strategies for variety. Best for long hunting sessions.
- Use `/settings` → Gen Mode to switch, or `--gen-mode word_combo` in CLI.
</details>

<details>
<summary><b>Can I use it without installing anything?</b></summary>

**Yes!** Use the Google Colab notebook — click the badge at the top. It has:
- One-click setup
- Config sliders
- A Telegram bot launcher (Step 3B)
- Multi-line username checker with textarea
</details>

<details>
<summary><b>How do I run the bot from Colab?</b></summary>

1. Open the notebook (badge at top)
2. Run Step 1 (setup)
3. Go to Step 3B — paste your bot token
4. Click ▶️ — the bot starts!
5. Open Telegram → find your bot → `/start`
6. Keep the cell running while you use the bot
</details>

<details>
<summary><b>What's new in v2.1?</b></summary>

- **Pattern templates:** `/pattern user_????` — generate from custom patterns
- **Word combos:** `/generate 50 word_combo` — memorable names like `fastcoder42`
- **Mixed generation:** Best of random + word combos
- **Smart dedup:** Never checks the same username twice
- **Retry logic:** Exponential backoff on rate limits (3 retries)
- **Auto delay:** Automatically slows down when rate limited
- **Rich notifications:** Hit alerts with Open/Stop buttons
- **Progress updates:** Periodic stats during long runs
- **Generation mode selector** in /settings
- **Pattern quick templates** menu
- See [CHANGELOG.md](CHANGELOG.md) for full details
</details>

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

## ⚠️ Disclaimer

Educational and personal use only. Automated checks may be rate-limited by Telegram. Use responsibly and at your own risk.

---

<div align="center">

**Made with ❤️ by [@Shineii86](https://github.com/Shineii86)**

⭐ Star this repo if it helped you find a great username!

</div>
