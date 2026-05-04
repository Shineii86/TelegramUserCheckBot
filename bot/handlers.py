"""
Telegram Bot — interactive Telegram username checker.

Commands:
    /start          — Welcome screen with feature overview
    /help           — Detailed help & username rules
    /check <name>   — Check a single username
    /batch <names>  — Check multiple usernames (comma-separated)
    /generate [N]   — Generate & check random usernames
    /pattern <tmpl> — Generate from pattern template
    /settings       — View/change settings with inline buttons
    /stats          — Session statistics with visual bars
    /history        — View recent check history
    /ping           — Check bot responsiveness
    /about          — Bot info & credits
    /stop           — Stop current batch/generation
    /cancel         — Alias for /stop
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from checker.telegram_client import (
    TelegramUsernameClient,
    AVAILABLE, TAKEN, INVALID, RATE_LIMITED, ERROR,
    is_valid_username,
)
from checker.generator import UsernameGenerator
from checker.telegram_client import is_valid_username


# ── Constants ──
VERSION = "2.1"
DIVIDER = "─" * 26
THICK_DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━"
THIN_DIVIDER = "· · · · · · · · · · · · · ·"
BOT_USERNAME = "TelegramUserCheckBot"
BOT_AUTHOR = "@Shineii86"
MAX_HISTORY = 20
START_TIME = time.time()


# ── Emoji Map ──
E = {
    "check": "🔍", "hit": "✅", "taken": "❌", "invalid": "🚫",
    "rate": "⚠️", "error": "💥", "stats": "📊", "settings": "⚙️",
    "stop": "🛑", "start": "🚀", "user": "👤", "id": "🆔",
    "pack": "📦", "clock": "🕐", "fire": "🔥", "star": "⭐",
    "back": "🔙", "yes": "✅", "no": "❌", "telegram": "📱",
    "link": "🔗", "magic": "✨", "target": "🎯", "wave": "👋",
    "bulb": "💡", "gear": "⚙️", "chart": "📈", "trophy": "🏆",
    "dart": "🎯", "sparkle": "✨", "wave2": "🤙", "pin": "📌",
    "shield": "🛡️", "zap": "⚡", "memo": "📝", "globe": "🌐",
    "ping": "🏓", "about": "ℹ️", "history": "📜", "copy": "📋",
    "heart": "❤️", "rocket": "🚀", "diamond": "💎", "crown": "👑",
    "time": "⏰", "refresh": "🔄", "export": "📤", "folder": "📁",
    "lightning": "⚡", "rainbow": "🌈", "party": "🎉", "wave3": "🤚",
    "eyes": "👀", "brain": "🧠", "magnifier": "🔎", "crystal": "🔮",
}


# ── Progress Bar ──
def progress_bar(current: int, total: int, length: int = 10) -> str:
    """Generate a text progress bar."""
    if total == 0:
        return "░" * length
    filled = int(length * current / total)
    return "█" * filled + "░" * (length - filled)


def pct(current: int, total: int) -> str:
    """Calculate percentage string."""
    if total == 0:
        return "0%"
    return f"{int(100 * current / total)}%"


def format_uptime(seconds: float) -> str:
    """Format seconds into human-readable uptime."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"


def format_time_ago(dt: datetime) -> str:
    """Format a datetime as a relative time string."""
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    else:
        return f"{int(seconds // 86400)}d ago"


# ── User Session ──
class UserSession:
    """Per-user session state."""

    def __init__(self):
        self.checked = 0
        self.hits = 0
        self.taken = 0
        self.invalid = 0
        self.rate_limited = 0
        self.errors = 0
        self.available: list = []
        self.running = False
        self.should_stop = False

        # History log (recent checks)
        self.history: list = []  # list of (timestamp, username, status)

        # Settings
        self.username_length = 5
        self.char_set = "abcdefghijklmnopqrstuvwxyz0123456789_"
        self.delay = 1.0
        self.max_workers = 5
        self.generation_mode = "random"  # "random", "word_combo", "mixed"
        self.pattern = ""  # Pattern template for /pattern

    def reset_stats(self):
        self.checked = 0
        self.hits = 0
        self.taken = 0
        self.invalid = 0
        self.rate_limited = 0
        self.errors = 0
        self.available = []

    def record(self, status: str, username: str):
        self.checked += 1
        # Add to history (keep last MAX_HISTORY)
        self.history.append((datetime.now(timezone.utc), username, status))
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

        if status == AVAILABLE:
            self.hits += 1
            self.available.append(username)
        elif status == TAKEN:
            self.taken += 1
        elif status == INVALID:
            self.invalid += 1
        elif status == RATE_LIMITED:
            self.rate_limited += 1
        elif status == ERROR:
            self.errors += 1

    @property
    def char_set_label(self) -> str:
        """Human-readable label for current character set."""
        sets = {
            "abcdefghijklmnopqrstuvwxyz0123456789_": "a-z 0-9 _",
            "abcdefghijklmnopqrstuvwxyz": "a-z only",
            "abcdefghijklmnopqrstuvwxyz0123456789": "a-z 0-9",
            "0123456789": "0-9 only",
        }
        return sets.get(self.char_set, self.char_set)

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        return (self.hits / self.checked * 100) if self.checked > 0 else 0.0

    def status_emoji(self, status: str) -> str:
        """Get emoji for a status."""
        return {
            AVAILABLE: E["hit"],
            TAKEN: E["taken"],
            INVALID: E["invalid"],
            RATE_LIMITED: E["rate"],
            ERROR: E["error"],
        }.get(status, E["error"])


# ── Global State ──
sessions: dict[int, UserSession] = {}
client: Optional[TelegramUsernameClient] = None


def get_session(user_id: int) -> UserSession:
    if user_id not in sessions:
        sessions[user_id] = UserSession()
    return sessions[user_id]


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /start — welcome screen with time-aware greeting."""
    user = update.effective_user
    hour = datetime.now(timezone.utc).hour
    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 17:
        greeting = "Good afternoon"
    elif 17 <= hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Hey"

    # Add /pattern to start text
    text = (
        f"{E['wave']} <b>{greeting}, {user.first_name}!</b>\n"
        f"\n"
        f"{E['telegram']} <b>{BOT_USERNAME}</b> <i>v{VERSION}</i>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"{E['magnifier']} <b>Telegram Username Availability Checker</b>\n"
        f"{E['lightning']} Fast  {E['shield']} Reliable  {E['sparkle']} Free\n"
        f"\n"
        f"<b>{E['pin']} Quick Actions:</b>\n"
        f"\n"
        f"  {E['check']}  <b>/check</b> <code>username</code> — Check one name\n"
        f"  {E['pack']}  <b>/batch</b> <code>a,b,c</code> — Check multiple\n"
        f"  {E['magic']}  <b>/generate</b> <code>[N]</code> — Random names\n"
        f"  {E['crystal']}  <b>/pattern</b> <code>tmpl</code> — Pattern templates\n"
        f"  {E['settings']}  <b>/settings</b> — Tune your preferences\n"
        f"  {E['stats']}  <b>/stats</b> — View session stats\n"
        f"  {E['history']}  <b>/history</b> — Recent check log\n"
        f"  {E['ping']}  <b>/ping</b> — Bot status & uptime\n"
        f"  {E['bulb']}  <b>/help</b> — Full guide & rules\n"
        f"\n"
        f"{THIN_DIVIDER}\n"
        f"{E['sparkle']} <i>Just type a username to quick-check it!</i>"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{E['check']} Quick Check", switch_inline_query_current_chat=""),
            InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate"),
        ],
        [
            InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings"),
            InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats"),
        ],
        [
            InlineKeyboardButton(f"{E['history']} History", callback_data="history"),
            InlineKeyboardButton(f"{E['bulb']} Help", callback_data="help"),
        ],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /help — detailed guide with better formatting."""
    text = (
        f"{E['bulb']} <b>How to Use {BOT_USERNAME}</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"<b>{E['check']} /check</b> <code>username</code>\n"
        f"Check if a single username is available.\n"
        f"<i>Example:</i> <code>/check coolname123</code>\n"
        f"\n"
        f"<b>{E['pack']} /batch</b> <code>user1,user2,user3</code>\n"
        f"Check multiple usernames at once (comma-separated).\n"
        f"<i>Example:</i> <code>/batch abc,xyz,test123</code>\n"
        f"\n"
        f"<b>{E['magic']} /generate</b> <code>[N]</code>\n"
        f"Generate random usernames and check them.\n"
        f"<i>Example:</i> <code>/generate 50</code> (default: 20)\n"
        f"\n"
        f"<b>{E['settings']} /settings</b>\n"
        f"Configure: length, character set, delay, workers.\n"
        f"\n"
        f"<b>{E['stats']} /stats</b>\n"
        f"View session stats: checked, hits, taken, errors.\n"
        f"\n"
        f"<b>{E['history']} /history</b>\n"
        f"View your recent check log with status indicators.\n"
        f"\n"
        f"<b>{E['ping']} /ping</b>\n"
        f"Check bot responsiveness and uptime.\n"
        f"\n"
        f"<b>{E['about']} /about</b>\n"
        f"Bot info, version, and credits.\n"
        f"\n"
        f"<b>{E['stop']} /stop</b>\n"
        f"Stop any running batch or generation.\n"
        f"\n"
        f"{THIN_DIVIDER}\n"
        f"\n"
        f"{E['pin']} <b>Telegram Username Rules:</b>\n"
        f"  {E['yes']} 5–32 characters\n"
        f"  {E['yes']} a-z, 0-9, underscores only\n"
        f"  {E['yes']} Must start with a letter\n"
        f"  {E['no']} No double underscores ( __ )\n"
        f"  {E['no']} Can't end with underscore\n"
        f"\n"
        f"{E['sparkle']} <i>Tip: Just type any username to quick-check!</i>\n"
        f"\n"
        f"{THICK_DIVIDER}\n"
        f"<i>{E['heart']} Made with love by {BOT_AUTHOR}</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['back']} Back to Start", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /check <username> with enhanced result cards."""
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/check username</code>\n\n"
            f"<i>Example:</i> <code>/check coolname123</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    username = ctx.args[0].strip().lower().lstrip("@")
    if not username:
        await update.message.reply_text(f"{E['error']} Provide a username.")
        return

    if not is_valid_username(username):
        await update.message.reply_text(
            f"{E['invalid']} <b>Invalid Username</b>\n"
            f"{DIVIDER}\n"
            f"<code>@{username}</code> doesn't follow Telegram's rules:\n"
            f"\n"
            f"  {E['no']} Must be 5–32 characters\n"
            f"  {E['no']} Must start with a letter\n"
            f"  {E['no']} Only a-z, 0-9, underscores\n"
            f"  {E['no']} No double underscores\n"
            f"  {E['no']} Can't end with underscore\n"
            f"\n"
            f"{E['bulb']} <i>Try a different name!</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    session = get_session(update.effective_user.id)
    msg = await update.message.reply_text(
        f"{E['clock']} <b>Checking...</b>\n"
        f"{DIVIDER}\n"
        f"{E['user']} <code>@{username}</code>\n"
        f"{THIN_DIVIDER}\n"
        f"<i>Scanning t.me/{username}</i>",
        parse_mode=ParseMode.HTML,
    )

    status, _ = await asyncio.to_thread(client.check, username, session.delay)
    session.record(status, username)

    if status == AVAILABLE:
        text = (
            f"{E['party']} <b>AVAILABLE!</b> {E['sparkle']}\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['user']} <b>Username:</b> <code>@{username}</code>\n"
            f"  {E['link']} <b>Link:</b> <a href=\"https://t.me/{username}\">t.me/{username}</a>\n"
            f"\n"
            f"{THICK_DIVIDER}\n"
            f"  {E['chart']} Session: {session.checked} checked  {E['diamond']} {session.hits} hits\n"
            f"\n"
            f"{E['rocket']} <i>Claim it now before someone else does!</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['link']} Open in Telegram", url=f"https://t.me/{username}")],
            [
                InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
                InlineKeyboardButton(f"{E['copy']} Copy Name", callback_data=f"copy_{username}"),
            ],
        ])
    elif status == TAKEN:
        text = (
            f"{E['taken']} <b>Taken</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['user']} <code>@{username}</code> is already registered.\n"
            f"\n"
            f"{E['bulb']} <i>Try /generate to find available names!</i>"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
                InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate"),
            ],
        ])
    elif status == INVALID:
        text = (
            f"{E['invalid']} <b>Invalid</b>\n"
            f"{DIVIDER}\n"
            f"<code>@{username}</code> is not a valid Telegram username."
        )
        kb = None
    elif status == RATE_LIMITED:
        text = (
            f"{E['rate']} <b>Rate Limited</b>\n"
            f"{DIVIDER}\n"
            f"Too many requests. Try again later or configure a proxy."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings")],
        ])
    else:
        text = (
            f"{E['error']} <b>Error</b>\n"
            f"{DIVIDER}\n"
            f"Failed to check <code>@{username}</code>. Please try again."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['refresh']} Retry", callback_data=f"retry_{username}")],
        ])

    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_batch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /batch user1,user2,user3 with enhanced progress."""
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/batch user1,user2,user3</code>\n\n"
            f"<i>Example:</i> <code>/batch abc,xyz,test123</code>\n"
            f"<i>You can also send a list separated by spaces or newlines.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = " ".join(ctx.args)
    usernames = [u.strip().lower().lstrip("@") for u in raw.replace("\n", ",").replace(" ", ",").split(",") if u.strip()]
    if not usernames:
        await update.message.reply_text(f"{E['error']} No usernames provided.")
        return

    if len(usernames) > 200:
        await update.message.reply_text(
            f"{E['rate']} <b>Too many!</b>\n\n"
            f"Maximum 200 usernames per batch. You provided {len(usernames)}.\n\n"
            f"<i>Split into smaller batches.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    session = get_session(update.effective_user.id)
    session.running = True
    session.should_stop = False

    bar = progress_bar(0, len(usernames))
    msg = await update.message.reply_text(
        f"{E['start']} <b>Batch Check Started</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['pack']} <b>Usernames:</b> {len(usernames)}\n"
        f"  {E['clock']} <b>Delay:</b> {session.delay}s\n"
        f"\n"
        f"<code>{bar}</code> 0/{len(usernames)}\n"
        f"\n"
        f"<i>{E['rocket']} Launching...</i>",
        parse_mode=ParseMode.HTML,
    )

    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    start_time = time.time()

    for i, username in enumerate(usernames):
        if session.should_stop:
            break

        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        results[status].append(username)

        # Update progress every 3 checks or on last
        if (i + 1) % 3 == 0 or i == len(usernames) - 1:
            try:
                bar = progress_bar(i + 1, len(usernames))
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                await msg.edit_text(
                    f"{E['fire']} <b>Batch Check Running</b>\n"
                    f"{THICK_DIVIDER}\n"
                    f"\n"
                    f"<code>{bar}</code> {i + 1}/{len(usernames)} ({pct(i + 1, len(usernames))})\n"
                    f"\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['invalid']} Invalid: {len(results[INVALID])}\n"
                    f"  {E['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n"
                    f"\n"
                    f"<i>{E['clock']} Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False
    elapsed = time.time() - start_time

    # Final report
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    stopped = f"{E['stop']} <b>Stopped by user</b>\n\n" if session.should_stop else ""

    bar = progress_bar(len(usernames), len(usernames))
    text = (
        f"{stopped}"
        f"{E['trophy']} <b>Batch Check Complete</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"<code>{bar}</code> {len(usernames)}/{len(usernames)} (100%)\n"
        f"\n"
        f"  {E['chart']} <b>Results:</b>\n"
        f"    {E['magnifier']} Total: {len(usernames)}\n"
        f"    {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
        f"    {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"    {E['invalid']} Invalid: {len(results[INVALID])}\n"
        f"    {E['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n"
        f"    {E['time']} Time: {format_uptime(elapsed)}\n"
        f"\n"
        f"  {E['target']} <b>Available Usernames:</b>\n"
        f"{hit_list}"
    )

    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(
            f"{E['export']} Export All Hits ({len(results[AVAILABLE])})",
            callback_data="export_hits"
        )])
    buttons.append([
        InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
        InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate"),
    ])

    kb = InlineKeyboardMarkup(buttons)
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _run_generation(update, session, count, message):
    """Run generation with the configured mode."""
    session.running = True
    session.should_stop = False

    gen = UsernameGenerator(
        length=session.username_length,
        chars=session.char_set,
    )

    # Choose stream based on generation mode
    if session.generation_mode == "word_combo":
        gen_stream = gen.word_combo_stream()
        mode_label = "Word Combos"
        mode_icon = E['brain']
    elif session.generation_mode == "mixed":
        gen_stream = gen.mixed_stream()
        mode_label = "Mixed"
        mode_icon = E['rainbow']
    else:
        gen_stream = gen.random_stream()
        mode_label = "Random"
        mode_icon = E['fire']

    bar = progress_bar(0, count)
    msg = await message.reply_text(
        f"{mode_icon} <b>Generating & Checking</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['gear']} <b>Mode:</b> {mode_label}\n"
        f"  {E['settings']} <b>Length:</b> {session.username_length} chars\n"
        f"  {E['gear']} <b>Chars:</b> <code>{session.char_set_label}</code>\n"
        f"  {E['clock']} <b>Delay:</b> {session.delay}s\n"
        f"\n"
        f"<code>{bar}</code> 0/{count}\n"
        f"\n"
        f"<i>{E['crystal']} Conjuring usernames...</i>",
        parse_mode=ParseMode.HTML,
    )

    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    start_time = time.time()

    for i in range(count):
        if session.should_stop:
            break

        username = next(gen_stream)
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        results[status].append(username)

        if (i + 1) % 3 == 0 or i == count - 1:
            try:
                bar = progress_bar(i + 1, count)
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                await msg.edit_text(
                    f"{mode_icon} <b>Generating & Checking</b>\n"
                    f"{THICK_DIVIDER}\n"
                    f"\n"
                    f"  {E['gear']} Mode: {mode_label}\n"
                    f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
                    f"\n"
                    f"<code>{bar}</code> {i + 1}/{count} ({pct(i + 1, count)})\n"
                    f"\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n"
                    f"\n"
                    f"<i>{E['clock']} Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False
    elapsed = time.time() - start_time

    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    stopped = f"{E['stop']} <b>Stopped by user</b>\n\n" if session.should_stop else ""

    bar = progress_bar(count, count)
    text = (
        f"{stopped}"
        f"{E['trophy']} <b>Generation Complete</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['gear']} Mode: {mode_label}\n"
        f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
        f"\n"
        f"<code>{bar}</code> {count}/{count} (100%)\n"
        f"\n"
        f"  {E['chart']} <b>Results:</b>\n"
        f"    {E['magnifier']} Checked: {count}\n"
        f"    {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
        f"    {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"    {E['invalid']} Invalid: {len(results[INVALID])}\n"
        f"    {E['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n"
        f"    {E['time']} Time: {format_uptime(elapsed)}\n"
        f"\n"
        f"  {E['target']} <b>Available Usernames:</b>\n"
        f"{hit_list}"
    )

    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(
            f"{E['export']} Export Hits ({len(results[AVAILABLE])})",
            callback_data="export_hits"
        )])
    buttons.extend([
        [InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="quick_generate")],
        [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
    ])

    kb = InlineKeyboardMarkup(buttons)
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /generate — generate and check random usernames."""
    session = get_session(update.effective_user.id)
    count = 20

    if ctx.args:
        try:
            count = int(ctx.args[0])
            count = max(1, min(count, 100))
        except ValueError:
            # Check if it's a mode keyword
            if ctx.args[0] in ("random", "word_combo", "mixed"):
                session.generation_mode = ctx.args[0]
                if len(ctx.args) > 1:
                    try:
                        count = max(1, min(int(ctx.args[1]), 100))
                    except ValueError:
                        pass

    await _run_generation(update, session, count, update.message)


async def cmd_pattern(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /pattern — generate from a pattern template.

    Pattern syntax:
        ? = random letter (a-z)
        # = random digit (0-9)
        _ = literal underscore
        @ = random char (a-z, 0-9, _)
        ! = random letter or digit

    Examples:
        /pattern user_????
        /pattern test_##_ab
        /pattern my_!_!_name
    """
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/pattern template</code>\n\n"
            f"<b>Pattern syntax:</b>\n"
            f"  <code>?</code> = random letter (a-z)\n"
            f"  <code>#</code> = random digit (0-9)\n"
            f"  <code>_</code> = literal underscore\n"
            f"  <code>@</code> = random char (a-z, 0-9, _)\n"
            f"  <code>!</code> = random letter or digit\n"
            f"  any other = literal character\n\n"
            f"<b>Examples:</b>\n"
            f"  <code>/pattern user_????</code>\n"
            f"  <code>/pattern test_##_ab</code>\n"
            f"  <code>/pattern my_!_!_name</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    pattern = ctx.args[0]

    # Validate pattern
    valid, err = UsernameGenerator.validate_pattern(pattern)
    if not valid:
        await update.message.reply_text(
            f"{E['invalid']} <b>Invalid Pattern</b>\n"
            f"{DIVIDER}\n"
            f"{err}\n\n"
            f"<i>Use /pattern for syntax help.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    session = get_session(update.effective_user.id)
    session.pattern = pattern
    count = 20
    if len(ctx.args) > 1:
        try:
            count = max(1, min(int(ctx.args[1]), 100))
        except ValueError:
            pass

    await _run_pattern_generation(update, session, count, pattern, update.message)


async def _run_pattern_generation(update, session, count, pattern, message):
    """Run pattern-based generation."""
    session.running = True
    session.should_stop = False

    gen = UsernameGenerator(
        length=session.username_length,
        chars=session.char_set,
    )

    bar = progress_bar(0, count)
    msg = await message.reply_text(
        f"{E['crystal']} <b>Pattern Generation</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['pin']} <b>Pattern:</b> <code>{pattern}</code>\n"
        f"  {E['pack']} <b>Count:</b> {count}\n"
        f"  {E['clock']} <b>Delay:</b> {session.delay}s\n"
        f"\n"
        f"<code>{bar}</code> 0/{count}\n"
        f"\n"
        f"<i>{E['crystal']} Generating from pattern...</i>",
        parse_mode=ParseMode.HTML,
    )

    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    gen_iter = gen.pattern_stream(pattern)
    start_time = time.time()

    for i in range(count):
        if session.should_stop:
            break

        username = next(gen_iter)
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        results[status].append(username)

        if (i + 1) % 3 == 0 or i == count - 1:
            try:
                bar = progress_bar(i + 1, count)
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                await msg.edit_text(
                    f"{E['crystal']} <b>Pattern Generation</b>\n"
                    f"{THICK_DIVIDER}\n"
                    f"\n"
                    f"  {E['pin']} Pattern: <code>{pattern}</code>\n"
                    f"\n"
                    f"<code>{bar}</code> {i + 1}/{count} ({pct(i + 1, count)})\n"
                    f"\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n"
                    f"\n"
                    f"<i>{E['clock']} Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False
    elapsed = time.time() - start_time

    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    stopped = f"{E['stop']} <b>Stopped by user</b>\n\n" if session.should_stop else ""

    bar = progress_bar(count, count)
    text = (
        f"{stopped}"
        f"{E['trophy']} <b>Pattern Generation Complete</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['pin']} Pattern: <code>{pattern}</code>\n"
        f"\n"
        f"<code>{bar}</code> {count}/{count} (100%)\n"
        f"\n"
        f"  {E['chart']} <b>Results:</b>\n"
        f"    {E['magnifier']} Checked: {count}\n"
        f"    {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
        f"    {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"    {E['time']} Time: {format_uptime(elapsed)}\n"
        f"\n"
        f"  {E['target']} <b>Available Usernames:</b>\n"
        f"{hit_list}"
    )

    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(
            f"{E['export']} Export Hits ({len(results[AVAILABLE])})",
            callback_data="export_hits"
        )])
    buttons.extend([
        [InlineKeyboardButton(f"{E['crystal']} Generate More", callback_data=f"pattern_more_{pattern}")],
        [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
    ])

    kb = InlineKeyboardMarkup(buttons)
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _run_pattern_from_callback(query, session, count, pattern):
    """Run pattern generation from a callback query (shared by pattern_tpl_ and pattern_more_)."""
    session.running = True
    session.should_stop = False

    gen = UsernameGenerator(length=session.username_length, chars=session.char_set)
    gen_stream = gen.pattern_stream(pattern)

    bar = progress_bar(0, count)
    await query.edit_message_text(
        f"{E['crystal']} <b>Pattern Generation</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['pin']} Pattern: <code>{pattern}</code>\n"
        f"\n"
        f"<code>{bar}</code> 0/{count}\n"
        f"\n"
        f"<i>{E['crystal']} Generating from pattern...</i>",
        parse_mode=ParseMode.HTML,
    )

    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    start_time = time.time()

    for i in range(count):
        if session.should_stop:
            break
        username = next(gen_stream)
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        results[status].append(username)

        if (i + 1) % 3 == 0 or i == count - 1:
            try:
                bar = progress_bar(i + 1, count)
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                await query.edit_message_text(
                    f"{E['crystal']} <b>Pattern Generation</b>\n"
                    f"{THICK_DIVIDER}\n"
                    f"\n"
                    f"  {E['pin']} Pattern: <code>{pattern}</code>\n"
                    f"\n"
                    f"<code>{bar}</code> {i + 1}/{count} ({pct(i + 1, count)})\n"
                    f"\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n"
                    f"\n"
                    f"<i>{E['clock']} Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False
    elapsed = time.time() - start_time

    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    bar = progress_bar(count, count)
    text = (
        f"{E['trophy']} <b>Pattern Complete</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['pin']} Pattern: <code>{pattern}</code>\n"
        f"\n"
        f"<code>{bar}</code> {count}/{count} (100%)\n"
        f"\n"
        f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
        f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"  {E['time']} Time: {format_uptime(elapsed)}\n"
        f"\n"
        f"  {E['target']} <b>Available Usernames:</b>\n"
        f"{hit_list}"
    )
    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(
            f"{E['export']} Export Hits ({len(results[AVAILABLE])})",
            callback_data="export_hits"
        )])
    buttons.extend([
        [InlineKeyboardButton(f"{E['crystal']} Generate More", callback_data=f"pattern_more_{pattern}")],
        [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
    ])
    kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /stats with enhanced visual display."""
    session = get_session(update.effective_user.id)

    hit_bar = progress_bar(session.hits, max(session.checked, 1), 12)

    text = (
        f"{E['stats']} <b>Session Statistics</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['chart']} <b>Overview:</b>\n"
        f"    {E['magnifier']} Checked: <b>{session.checked}</b>\n"
        f"    {E['hit']} Available: <b>{session.hits}</b>\n"
        f"    {E['taken']} Taken: <b>{session.taken}</b>\n"
        f"    {E['invalid']} Invalid: <b>{session.invalid}</b>\n"
        f"    {E['rate']} Rate Limit: <b>{session.rate_limited}</b>\n"
        f"    {E['error']} Errors: <b>{session.errors}</b>\n"
        f"\n"
        f"  {E['target']} <b>Hit Rate:</b>\n"
        f"    <code>{hit_bar}</code> {session.hit_rate:.1f}%\n"
    )

    if session.available:
        recent = session.available[-8:]
        hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in recent)
        text += f"\n  {E['star']} <b>Recent Hits:</b>\n{hit_list}"
        if len(session.available) > 8:
            text += f"\n    <i>{E['eyes']} ... and {len(session.available) - 8} more</i>"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{E['export']} Export Hits", callback_data="export_hits"),
            InlineKeyboardButton(f"{E['history']} History", callback_data="history"),
        ],
        [
            InlineKeyboardButton(f"{E['refresh']} Reset Stats", callback_data="confirm_reset_stats"),
            InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start"),
        ],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /history — show recent check log."""
    session = get_session(update.effective_user.id)

    if not session.history:
        await update.message.reply_text(
            f"{E['history']} <b>Check History</b>\n"
            f"{DIVIDER}\n"
            f"\n"
            f"  {E['no']} No checks yet.\n\n"
            f"<i>Start with /check, /batch, or /generate!</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = []
    for ts, username, status in reversed(session.history[-15:]):
        emoji = session.status_emoji(status)
        time_str = format_time_ago(ts)
        lines.append(f"  {emoji} <code>@{username}</code>  <i>{time_str}</i>")

    history_text = "\n".join(lines)

    text = (
        f"{E['history']} <b>Recent Checks</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"{history_text}\n"
        f"\n"
        f"{THIN_DIVIDER}\n"
        f"  {E['chart']} Total: {session.checked} checked  {E['diamond']} {session.hits} hits"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats"),
            InlineKeyboardButton(f"{E['export']} Export Hits", callback_data="export_hits"),
        ],
        [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /ping — show bot responsiveness and uptime."""
    uptime = time.time() - START_TIME
    session = get_session(update.effective_user.id)

    text = (
        f"{E['ping']} <b>Pong!</b>\n"
        f"{DIVIDER}\n"
        f"\n"
        f"  {E['zap']} <b>Uptime:</b> {format_uptime(uptime)}\n"
        f"  {E['telegram']} <b>Version:</b> v{VERSION}\n"
        f"  {E['chart']} <b>Your Stats:</b> {session.checked} checked, {session.hits} hits\n"
        f"\n"
        f"{E['rocket']} <i>All systems operational!</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /about — bot info and credits."""
    text = (
        f"{E['about']} <b>About {BOT_USERNAME}</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['magnifier']} <b>What:</b> Telegram Username\n"
        f"       Availability Checker\n"
        f"\n"
        f"  {E['globe']} <b>How:</b> Scrapes t.me pages\n"
        f"       No API keys needed!\n"
        f"\n"
        f"  {E['lightning']} <b>Features:</b>\n"
        f"       Single & batch checking\n"
        f"       Random name generation\n"
        f"       Proxy rotation support\n"
        f"       Real-time notifications\n"
        f"\n"
        f"  {E['gear']} <b>Version:</b> {VERSION}\n"
        f"  {E['brain']} <b>Author:</b> {BOT_AUTHOR}\n"
        f"  {E['link']} <b>Source:</b> GitHub\n"
        f"\n"
        f"{THIN_DIVIDER}\n"
        f"{E['heart']} <i>Star the repo if you find it useful!</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['link']} GitHub Repo", url="https://github.com/Shineii86/TelegramUserCheckBot")],
        [InlineKeyboardButton(f"{E['star']} Star on GitHub", url="https://github.com/Shineii86/TelegramUserCheckBot/stargazers")],
        [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /stop and /cancel."""
    session = get_session(update.effective_user.id)
    if session.running:
        session.should_stop = True
        await update.message.reply_text(
            f"{E['stop']} <b>Stopping...</b>\n"
            f"{DIVIDER}\n"
            f"Will finish the current check shortly.\n\n"
            f"<i>{E['clock']} Wrapping up...</i>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"{E['bulb']} Nothing is running right now.\n\n"
            f"<i>Start a check with /check, /batch, or /generate.</i>",
            parse_mode=ParseMode.HTML,
        )


async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /settings."""
    session = get_session(update.effective_user.id)
    await show_settings(update.message, session)


async def show_settings(message, session: UserSession):
    """Show settings menu with inline buttons."""
    text = (
        f"{E['settings']} <b>Settings</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['memo']} <b>Current Configuration:</b>\n"
        f"\n"
        f"    📏 <b>Length:</b> {session.username_length} chars\n"
        f"    🔤 <b>Chars:</b> <code>{session.char_set_label}</code>\n"
        f"    {E['clock']} <b>Delay:</b> {session.delay}s\n"
        f"    🧵 <b>Workers:</b> {session.max_workers}\n"
        f"\n"
        f"  {E['bulb']} <i>Tap a setting to change it:</i>"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"📏 Length ({session.username_length})", callback_data="set_length"),
            InlineKeyboardButton(f"🔤 Chars", callback_data="set_chars"),
        ],
        [
            InlineKeyboardButton(f"{E['clock']} Delay ({session.delay}s)", callback_data="set_delay"),
            InlineKeyboardButton(f"🧵 Workers ({session.max_workers})", callback_data="set_workers"),
        ],
        [
            InlineKeyboardButton(f"{E['gear']} Gen Mode ({session.generation_mode})", callback_data="set_gen_mode"),
            InlineKeyboardButton(f"{E['crystal']} Pattern", callback_data="pattern_menu"),
        ],
        [
            InlineKeyboardButton(f"{E['refresh']} Reset All", callback_data="confirm_reset_settings"),
            InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start"),
        ],
    ])
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ============================================================================
# CALLBACK QUERY HANDLERS
# ============================================================================

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = get_session(user_id)
    data = query.data

    # ── Navigation ──
    if data == "back_start":
        user = query.from_user
        text = (
            f"{E['wave']} <b>Hey {user.first_name}!</b>\n"
            f"\n"
            f"{E['telegram']} <b>{BOT_USERNAME}</b> <i>v{VERSION}</i>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['check']}  <b>/check</b> — Check one username\n"
            f"  {E['pack']}  <b>/batch</b> — Check multiple at once\n"
            f"  {E['magic']}  <b>/generate</b> — Generate & check random names\n"
            f"  {E['crystal']}  <b>/pattern</b> — Generate from pattern template\n"
            f"  {E['settings']}  <b>/settings</b> — Configure preferences\n"
            f"  {E['stats']}  <b>/stats</b> — View session statistics\n"
            f"  {E['history']}  <b>/history</b> — Recent check log\n"
            f"  {E['ping']}  <b>/ping</b> — Bot status & uptime\n"
            f"  {E['bulb']}  <b>/help</b> — Full guide & username rules\n"
            f"\n"
            f"{THIN_DIVIDER}\n"
            f"{E['sparkle']} <i>Just type a username to quick-check!</i>"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['check']} Quick Check", switch_inline_query_current_chat=""),
                InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate"),
            ],
            [
                InlineKeyboardButton(f"{E['crystal']} Pattern", callback_data="pattern_menu"),
                InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings"),
            ],
            [
                InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats"),
                InlineKeyboardButton(f"{E['history']} History", callback_data="history"),
            ],
            [
                InlineKeyboardButton(f"{E['bulb']} Help", callback_data="help"),
            ],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "quick_generate":
        # Use configured generation mode
        session.running = True
        session.should_stop = False
        count = 20

        gen = UsernameGenerator(length=session.username_length, chars=session.char_set)

        # Choose stream based on generation mode
        if session.generation_mode == "word_combo":
            gen_stream = gen.word_combo_stream()
            mode_label = "Word Combos"
            mode_icon = E['brain']
        elif session.generation_mode == "mixed":
            gen_stream = gen.mixed_stream()
            mode_label = "Mixed"
            mode_icon = E['rainbow']
        else:
            gen_stream = gen.random_stream()
            mode_label = "Random"
            mode_icon = E['fire']

        bar = progress_bar(0, count)
        await query.edit_message_text(
            f"{mode_icon} <b>Generating & Checking</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['gear']} Mode: {mode_label}\n"
            f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
            f"\n"
            f"<code>{bar}</code> 0/{count}\n"
            f"\n"
            f"<i>{E['crystal']} Conjuring usernames...</i>",
            parse_mode=ParseMode.HTML,
        )

        results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
        start_time = time.time()

        for i in range(count):
            if session.should_stop:
                break
            username = next(gen_stream)
            status, _ = await asyncio.to_thread(client.check, username, session.delay)
            session.record(status, username)
            results[status].append(username)

            if (i + 1) % 3 == 0 or i == count - 1:
                try:
                    bar = progress_bar(i + 1, count)
                    elapsed = time.time() - start_time
                    speed = (i + 1) / elapsed if elapsed > 0 else 0
                    await query.edit_message_text(
                        f"{E['fire']} <b>Generating & Checking</b>\n"
                        f"{THICK_DIVIDER}\n"
                        f"\n"
                        f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
                        f"\n"
                        f"<code>{bar}</code> {i + 1}/{count} ({pct(i + 1, count)})\n"
                        f"\n"
                        f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                        f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                        f"  {E['zap']} Speed: {speed:.1f}/sec\n"
                        f"\n"
                        f"<i>{E['clock']} Checking...</i>",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass

        session.running = False
        elapsed = time.time() - start_time

        hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
        bar = progress_bar(count, count)
        text = (
            f"{E['trophy']} <b>Generation Complete</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"<code>{bar}</code> {count}/{count} (100%)\n"
            f"\n"
            f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
            f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
            f"  {E['time']} Time: {format_uptime(elapsed)}\n"
            f"\n"
            f"  {E['target']} <b>Available Usernames:</b>\n"
            f"{hit_list}"
        )
        buttons = []
        if results[AVAILABLE]:
            buttons.append([InlineKeyboardButton(
                f"{E['export']} Export Hits ({len(results[AVAILABLE])})",
                callback_data="export_hits"
            )])
        buttons.extend([
            [InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="quick_generate")],
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
        ])
        kb = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Copy username ──
    elif data.startswith("copy_"):
        username = data[5:]
        await query.edit_message_text(
            f"{E['copy']} <b>Username ready to copy!</b>\n"
            f"{DIVIDER}\n"
            f"\n"
            f"<code>@{username}</code>\n"
            f"\n"
            f"<i>Select and copy the name above.</i>",
            parse_mode=ParseMode.HTML,
        )

    # ── Retry check ──
    elif data.startswith("retry_"):
        username = data[6:]
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)

        if status == AVAILABLE:
            text = (
                f"{E['party']} <b>AVAILABLE!</b> {E['sparkle']}\n"
                f"{THICK_DIVIDER}\n"
                f"\n"
                f"  {E['user']} <b>Username:</b> <code>@{username}</code>\n"
                f"  {E['link']} <b>Link:</b> <a href=\"https://t.me/{username}\">t.me/{username}</a>\n"
                f"\n"
                f"{E['rocket']} <i>Claim it now!</i>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{E['link']} Open in Telegram", url=f"https://t.me/{username}")],
                [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
            ])
        elif status == TAKEN:
            text = f"{E['taken']} <code>@{username}</code> is still taken."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
            ])
        else:
            text = f"{E['error']} Still having trouble checking <code>@{username}</code>."
            kb = None

        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── History ──
    elif data == "history":
        if not session.history:
            text = (
                f"{E['history']} <b>Check History</b>\n"
                f"{DIVIDER}\n"
                f"\n"
                f"  {E['no']} No checks yet.\n\n"
                f"<i>Start with /check, /batch, or /generate!</i>"
            )
        else:
            lines = []
            for ts, username, status in reversed(session.history[-15:]):
                emoji = session.status_emoji(status)
                time_str = format_time_ago(ts)
                lines.append(f"  {emoji} <code>@{username}</code>  <i>{time_str}</i>")
            history_text = "\n".join(lines)
            text = (
                f"{E['history']} <b>Recent Checks</b>\n"
                f"{THICK_DIVIDER}\n"
                f"\n"
                f"{history_text}\n"
                f"\n"
                f"{THIN_DIVIDER}\n"
                f"  {E['chart']} Total: {session.checked} checked  {E['diamond']} {session.hits} hits"
            )

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats"),
                InlineKeyboardButton(f"{E['export']} Export Hits", callback_data="export_hits"),
            ],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Settings ──
    elif data == "settings":
        text = (
            f"{E['settings']} <b>Settings</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  📏 <b>Length:</b> {session.username_length} chars\n"
            f"  🔤 <b>Chars:</b> <code>{session.char_set_label}</code>\n"
            f"  {E['clock']} <b>Delay:</b> {session.delay}s\n"
            f"  🧵 <b>Workers:</b> {session.max_workers}\n"
            f"  {E['gear']} <b>Gen Mode:</b> {session.generation_mode}\n"
            f"  {E['crystal']} <b>Pattern:</b> {session.pattern or 'none'}\n"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"📏 Length ({session.username_length})", callback_data="set_length"),
                InlineKeyboardButton(f"🔤 Chars", callback_data="set_chars"),
            ],
            [
                InlineKeyboardButton(f"{E['clock']} Delay ({session.delay}s)", callback_data="set_delay"),
                InlineKeyboardButton(f"🧵 Workers ({session.max_workers})", callback_data="set_workers"),
            ],
            [
                InlineKeyboardButton(f"{E['gear']} Gen Mode ({session.generation_mode})", callback_data="set_gen_mode"),
                InlineKeyboardButton(f"{E['crystal']} Pattern", callback_data="pattern_menu"),
            ],
            [
                InlineKeyboardButton(f"{E['refresh']} Reset All", callback_data="confirm_reset_settings"),
                InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start"),
            ],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "set_length":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{'👉 ' if i == session.username_length else ''}{i} chars",
                callback_data=f"len_{i}"
            ) for i in [5, 6, 7]],
            [InlineKeyboardButton(
                f"{'👉 ' if i == session.username_length else ''}{i} chars",
                callback_data=f"len_{i}"
            ) for i in [8, 10, 12]],
            [InlineKeyboardButton(
                f"{'👉 ' if i == session.username_length else ''}{i} chars",
                callback_data=f"len_{i}"
            ) for i in [15, 20, 25]],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"📏 <b>Choose Username Length</b>\n"
            f"{DIVIDER}\n"
            f"<i>Telegram allows 5–32 characters</i>\n\n"
            f"Current: <b>{session.username_length}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("len_"):
        session.username_length = int(data.split("_")[1])
        await query.edit_message_text(
            f"{E['yes']} Length set to <b>{session.username_length} chars</b>\n\n"
            f"<i>Use /generate to try it out!</i>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "set_chars":
        current = session.char_set_label
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{'👉 ' if current == 'a-z 0-9 _' else ''}a-z 0-9 _  {E['star'] if current == 'a-z 0-9 _' else ''}",
                callback_data="chars_default"
            )],
            [InlineKeyboardButton(
                f"{'👉 ' if current == 'a-z only' else ''}a-z only",
                callback_data="chars_alpha"
            )],
            [InlineKeyboardButton(
                f"{'👉 ' if current == 'a-z 0-9' else ''}a-z 0-9",
                callback_data="chars_alnum"
            )],
            [InlineKeyboardButton(
                f"{'👉 ' if current == '0-9 only' else ''}0-9 only",
                callback_data="chars_digits"
            )],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"🔤 <b>Choose Character Set</b>\n"
            f"{DIVIDER}\n"
            f"Current: <code>{session.char_set_label}</code>\n\n"
            f"<i>Characters used when generating random names.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("chars_"):
        sets = {
            "chars_default": "abcdefghijklmnopqrstuvwxyz0123456789_",
            "chars_alpha": "abcdefghijklmnopqrstuvwxyz",
            "chars_alnum": "abcdefghijklmnopqrstuvwxyz0123456789",
            "chars_digits": "0123456789",
        }
        session.char_set = sets.get(data, sets["chars_default"])
        await query.edit_message_text(
            f"{E['yes']} Character set updated!\n"
            f"{DIVIDER}\n"
            f"New set: <code>{session.char_set}</code>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "set_delay":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{'👉 ' if d == session.delay else ''}{d}s",
                    callback_data=f"delay_{d}"
                ) for d in [0.5, 1.0, 2.0]
            ],
            [
                InlineKeyboardButton(
                    f"{'👉 ' if d == session.delay else ''}{d}s",
                    callback_data=f"delay_{d}"
                ) for d in [3.0, 5.0]
            ],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"{E['clock']} <b>Choose Delay</b>\n"
            f"{DIVIDER}\n"
            f"Current: <b>{session.delay}s</b>\n\n"
            f"<i>Higher = safer from rate limits</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("delay_"):
        session.delay = float(data.split("_")[1])
        await query.edit_message_text(
            f"{E['yes']} Delay set to <b>{session.delay}s</b>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "set_workers":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{'👉 ' if i == session.max_workers else ''}{i} workers",
                callback_data=f"workers_{i}"
            ) for i in [1, 3, 5]],
            [InlineKeyboardButton(
                f"{'👉 ' if i == session.max_workers else ''}{i} workers",
                callback_data=f"workers_{i}"
            ) for i in [10, 20, 50]],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"🧵 <b>Choose Worker Count</b>\n"
            f"{DIVIDER}\n"
            f"Current: <b>{session.max_workers}</b>\n\n"
            f"<i>More workers = faster, but higher risk</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("workers_"):
        session.max_workers = int(data.split("_")[1])
        await query.edit_message_text(
            f"{E['yes']} Workers set to <b>{session.max_workers}</b>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "set_gen_mode":
        current = session.generation_mode
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{'👉 ' if current == 'random' else ''}🎲 Random",
                callback_data="gen_random"
            )],
            [InlineKeyboardButton(
                f"{'👉 ' if current == 'word_combo' else ''}🧠 Word Combos",
                callback_data="gen_word_combo"
            )],
            [InlineKeyboardButton(
                f"{'👉 ' if current == 'mixed' else ''}🌈 Mixed (Best)",
                callback_data="gen_mixed"
            )],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"{E['gear']} <b>Choose Generation Mode</b>\n"
            f"{DIVIDER}\n"
            f"Current: <b>{current}</b>\n\n"
            f"  🎲 <b>Random</b> — Pure random characters\n"
            f"  🧠 <b>Word Combos</b> — Adjective+noun+number\n"
            f"  🌈 <b>Mixed</b> — Best of both worlds",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("gen_"):
        mode = data[4:]
        session.generation_mode = mode
        mode_labels = {"random": "🎲 Random", "word_combo": "🧠 Word Combos", "mixed": "🌈 Mixed"}
        label = mode_labels.get(mode, mode)
        await query.edit_message_text(
            f"{E['yes']} Generation mode set to <b>{label}</b>\n\n"
            f"<i>Use /generate to try it out!</i>",
            parse_mode=ParseMode.HTML,
        )

    # ── Confirmations ──
    elif data == "confirm_reset_settings":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['yes']} Yes, Reset", callback_data="reset_settings"),
                InlineKeyboardButton(f"{E['no']} Cancel", callback_data="settings"),
            ],
        ])
        await query.edit_message_text(
            f"{E['stop']} <b>Reset all settings?</b>\n"
            f"{DIVIDER}\n"
            f"This will restore defaults:\n"
            f"  • Length: 5\n"
            f"  • Chars: a-z 0-9 _\n"
            f"  • Delay: 1.0s\n"
            f"  • Workers: 5",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data == "reset_settings":
        session.username_length = 5
        session.char_set = "abcdefghijklmnopqrstuvwxyz0123456789_"
        session.delay = 1.0
        session.max_workers = 5
        session.generation_mode = "random"
        session.pattern = ""
        await query.edit_message_text(
            f"{E['yes']} <b>Settings reset to defaults!</b>\n\n"
            f"<i>Use /settings to view current config.</i>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "confirm_reset_stats":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['yes']} Yes, Reset", callback_data="reset_stats"),
                InlineKeyboardButton(f"{E['no']} Cancel", callback_data="stats"),
            ],
        ])
        await query.edit_message_text(
            f"{E['stop']} <b>Reset all statistics?</b>\n"
            f"{DIVIDER}\n"
            f"This will clear:\n"
            f"  • {session.checked} checked usernames\n"
            f"  • {session.hits} available hits\n"
            f"  • All other counters\n"
            f"  • Check history",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data == "reset_stats":
        session.reset_stats()
        session.history.clear()
        await query.edit_message_text(
            f"{E['yes']} <b>Statistics reset!</b>\n\n"
            f"<i>Start fresh with /check, /batch, or /generate.</i>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "export_hits":
        if session.available:
            hit_list = "\n".join(f"@{u}" for u in session.available)
            await query.edit_message_text(
                f"{E['export']} <b>Your Available Usernames ({len(session.available)})</b>\n"
                f"{THICK_DIVIDER}\n"
                f"\n"
                f"<code>{hit_list}</code>\n"
                f"\n"
                f"{THIN_DIVIDER}\n"
                f"{E['copy']} <i>Select and copy the names above!</i>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text(
                f"{E['no']} No available usernames found yet.\n\n"
                f"<i>Run /check, /batch, or /generate first.</i>",
                parse_mode=ParseMode.HTML,
            )

    # ── Stats ──
    elif data == "stats":
        hit_bar = progress_bar(session.hits, max(session.checked, 1), 12)

        text = (
            f"{E['stats']} <b>Session Statistics</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['magnifier']} Checked: <b>{session.checked}</b>\n"
            f"  {E['hit']} Available: <b>{session.hits}</b>\n"
            f"  {E['taken']} Taken: <b>{session.taken}</b>\n"
            f"  {E['invalid']} Invalid: <b>{session.invalid}</b>\n"
            f"  {E['rate']} Rate Limit: <b>{session.rate_limited}</b>\n"
            f"  {E['error']} Errors: <b>{session.errors}</b>\n"
            f"\n"
            f"  {E['target']} <b>Hit Rate:</b>\n"
            f"    <code>{hit_bar}</code> {session.hit_rate:.1f}%\n"
        )
        if session.available:
            recent = session.available[-5:]
            hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in recent)
            text += f"\n  {E['star']} <b>Recent Hits:</b>\n{hit_list}"

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['export']} Export Hits", callback_data="export_hits"),
                InlineKeyboardButton(f"{E['history']} History", callback_data="history"),
            ],
            [
                InlineKeyboardButton(f"{E['refresh']} Reset", callback_data="confirm_reset_stats"),
                InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start"),
            ],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Help ──
    elif data == "help":
        text = (
            f"{E['bulb']} <b>Quick Help</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['check']} <b>/check</b> <code>username</code> — Check one\n"
            f"  {E['pack']} <b>/batch</b> <code>a,b,c</code> — Check multiple\n"
            f"  {E['magic']} <b>/generate</b> <code>[N]</code> — Random names\n"
            f"  {E['crystal']} <b>/pattern</b> <code>tmpl</code> — Pattern templates\n"
            f"  {E['settings']} <b>/settings</b> — Configure\n"
            f"  {E['stats']} <b>/stats</b> — View stats\n"
            f"  {E['history']} <b>/history</b> — Recent checks\n"
            f"  {E['ping']} <b>/ping</b> — Bot status\n"
            f"  {E['about']} <b>/about</b> — Bot info\n"
            f"  {E['stop']} <b>/stop</b> — Stop operation\n"
            f"\n"
            f"  {E['sparkle']} <b>Quick Check:</b> Just type a username!\n"
            f"\n"
            f"{E['pin']} <b>Username Rules:</b>\n"
            f"  5–32 chars • a-z, 0-9, _ • starts with letter\n"
            f"  No double __ • Can't end with _\n"
            f"\n"
            f"{E['crystal']} <b>Pattern Syntax:</b>\n"
            f"  <code>?</code>=letter <code>#</code>=digit <code>!</code>=alnum <code>_</code>=underscore"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Pattern Menu ──
    elif data == "pattern_menu":
        text = (
            f"{E['crystal']} <b>Pattern Templates</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  Generate usernames from a pattern!\n"
            f"\n"
            f"  <b>Syntax:</b>\n"
            f"    <code>?</code> = random letter (a-z)\n"
            f"    <code>#</code> = random digit (0-9)\n"
            f"    <code>!</code> = random letter or digit\n"
            f"    <code>_</code> = literal underscore\n"
            f"    any other = literal character\n"
            f"\n"
            f"  <b>Quick Templates:</b>\n"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("user_????", callback_data="pattern_tpl_user_????")],
            [InlineKeyboardButton("name_##_ab", callback_data="pattern_tpl_name_##_ab")],
            [InlineKeyboardButton("my_!_!_!_tag", callback_data="pattern_tpl_my_!_!_!_tag")],
            [InlineKeyboardButton("pro_####", callback_data="pattern_tpl_pro_####")],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Pattern quick template ──
    elif data.startswith("pattern_tpl_"):
        pattern = data[len("pattern_tpl_"):]
        session.pattern = pattern
        await _run_pattern_from_callback(query, session, 20, pattern)

    # ── Pattern more ──
    elif data.startswith("pattern_more_"):
        pattern = data[len("pattern_more_"):]
        session.pattern = pattern
        await _run_pattern_from_callback(query, session, 20, pattern)


# ============================================================================
# MESSAGE HANDLER (Quick check by just typing a username)
# ============================================================================

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages as quick username checks."""
    text = update.message.text.strip().lstrip("@").lower()

    # Only check if it looks like a username
    if len(text) < 5 or len(text) > 32:
        return
    if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in text):
        return
    if not text[0].isalpha():
        return

    session = get_session(update.effective_user.id)

    if not is_valid_username(text):
        await update.message.reply_text(
            f"{E['invalid']} <code>@{text}</code> is not a valid Telegram username.\n\n"
            f"<i>Rules: 5–32 chars, a-z/0-9/_ only, starts with letter.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    msg = await update.message.reply_text(
        f"{E['clock']} <b>Checking</b> <code>@{text}</code>...\n"
        f"{THIN_DIVIDER}",
        parse_mode=ParseMode.HTML,
    )

    status, _ = await asyncio.to_thread(client.check, text, session.delay)
    session.record(status, text)

    if status == AVAILABLE:
        result = (
            f"{E['party']} <b>AVAILABLE!</b> {E['sparkle']}\n"
            f"{DIVIDER}\n"
            f"  {E['user']} <code>@{text}</code>\n"
            f"  {E['link']} <a href=\"https://t.me/{text}\">t.me/{text}</a>\n"
            f"\n"
            f"  {E['chart']} Session: {session.checked} checked  {E['diamond']} {session.hits} hits"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['link']} Open in Telegram", url=f"https://t.me/{text}")],
            [
                InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
                InlineKeyboardButton(f"{E['copy']} Copy", callback_data=f"copy_{text}"),
            ],
        ])
    elif status == TAKEN:
        result = (
            f"{E['taken']} <code>@{text}</code> is taken.\n"
            f"\n"
            f"{E['bulb']} <i>Try /generate to find available names!</i>"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
                InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate"),
            ],
        ])
    elif status == INVALID:
        result = f"{E['invalid']} <code>@{text}</code> is invalid."
        kb = None
    elif status == RATE_LIMITED:
        result = f"{E['rate']} Rate limited. Try again later."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings")],
        ])
    else:
        result = (
            f"{E['error']} Error checking <code>@{text}</code>.\n\n"
            f"<i>Tap retry to try again.</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['refresh']} Retry", callback_data=f"retry_{text}")],
        ])

    await msg.edit_text(result, parse_mode=ParseMode.HTML, reply_markup=kb)


# ============================================================================
# BOT RUNNER
# ============================================================================

def run_bot(token: str):
    """Initialize and run the Telegram bot."""
    global client
    client = TelegramUsernameClient(user_agents=[
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ])

    app = Application.builder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("batch", cmd_batch))
    app.add_handler(CommandHandler("generate", cmd_generate))
    app.add_handler(CommandHandler("pattern", cmd_pattern))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("cancel", cmd_stop))

    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Message handler for quick checks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"🤖 {BOT_USERNAME} v{VERSION} is running...")
    print("Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)
