"""
Telegram Bot — interactive Telegram username checker.

Commands:
    /start          — Welcome screen with feature overview
    /help           — Detailed help & username rules
    /check <name>   — Check a single username
    /batch <names>  — Check multiple usernames (comma-separated)
    /generate [N]   — Generate & check random usernames
    /settings       — View/change settings with inline buttons
    /stats          — Session statistics with visual bars
    /stop           — Stop current batch/generation
    /cancel         — Alias for /stop
"""

import asyncio
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
from checker.proxy import ProxyManager
from checker.generator import UsernameGenerator


# ── Constants ──
VERSION = "1.1"
DIVIDER = "─" * 26
THICK_DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━"
BOT_USERNAME = "TelegramUserCheckBot"


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

        # Settings
        self.username_length = 5
        self.char_set = "abcdefghijklmnopqrstuvwxyz0123456789_"
        self.delay = 1.0
        self.max_workers = 5

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
    """Handle /start — welcome screen."""
    user = update.effective_user
    text = (
        f"{E['wave']} <b>Hey {user.first_name}!</b>\n"
        f"\n"
        f"{E['telegram']} <b>{BOT_USERNAME} v{VERSION}</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"{E['check']} <b>Check Telegram username availability</b>\n"
        f"{E['zap']} Fast • Free • No API keys needed\n"
        f"\n"
        f"<b>{E['pin']} What I can do:</b>\n"
        f"\n"
        f"  {E['check']} <b>/check</b> — Check one username\n"
        f"  {E['pack']} <b>/batch</b> — Check multiple at once\n"
        f"  {E['magic']} <b>/generate</b> — Generate & check random names\n"
        f"  {E['settings']} <b>/settings</b> — Configure length, delay, chars\n"
        f"  {E['stats']} <b>/stats</b> — View your session statistics\n"
        f"  {E['stop']} <b>/stop</b> — Stop any running operation\n"
        f"  {E['bulb']} <b>/help</b> — Full guide & username rules\n"
        f"\n"
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
            InlineKeyboardButton(f"{E['bulb']} Help", callback_data="help"),
        ],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /help — detailed guide."""
    text = (
        f"{E['bulb']} <b>How to Use {BOT_USERNAME}</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"<b>{E['check']} /check username</b>\n"
        f"Check if a single username is available.\n"
        f"<i>Example:</i> <code>/check coolname123</code>\n"
        f"\n"
        f"<b>{E['pack']} /batch user1,user2,user3</b>\n"
        f"Check multiple usernames (comma-separated).\n"
        f"<i>Example:</i> <code>/batch abc,xyz,test123</code>\n"
        f"\n"
        f"<b>{E['magic']} /generate [N]</b>\n"
        f"Generate random usernames and check them.\n"
        f"<i>Example:</i> <code>/generate 50</code> (default: 20)\n"
        f"\n"
        f"<b>{E['settings']} /settings</b>\n"
        f"Configure: length, character set, delay, workers.\n"
        f"\n"
        f"<b>{E['stats']} /stats</b>\n"
        f"View session stats: checked, hits, taken, errors.\n"
        f"\n"
        f"<b>{E['stop']} /stop</b>\n"
        f"Stop any running batch or generation.\n"
        f"\n"
        f"{E['pin']} <b>Telegram Username Rules:</b>\n"
        f"{DIVIDER}\n"
        f"  {E['yes']} 5-32 characters\n"
        f"  {E['yes']} a-z, 0-9, underscores only\n"
        f"  {E['yes']} Must start with a letter\n"
        f"  {E['no']} No double underscores ( __ )\n"
        f"  {E['no']} Can't end with underscore\n"
        f"\n"
        f"{E['sparkle']} <i>Tip: Just type any username to quick-check!</i>\n"
        f"\n"
        f"{THICK_DIVIDER}\n"
        f"<i>Made with {E['hit']} by @Shineii86</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['back']} Back to Start", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /check <username>."""
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
            f"  {E['no']} Must be 5-32 characters\n"
            f"  {E['no']} Must start with a letter\n"
            f"  {E['no']} Only a-z, 0-9, underscores\n"
            f"  {E['no']} No double underscores\n"
            f"  {E['no']} Can't end with underscore",
            parse_mode=ParseMode.HTML,
        )
        return

    session = get_session(update.effective_user.id)
    msg = await update.message.reply_text(
        f"{E['clock']} <b>Checking...</b>\n"
        f"{DIVIDER}\n"
        f"{E['user']} <code>@{username}</code>",
        parse_mode=ParseMode.HTML,
    )

    status, _ = await asyncio.to_thread(client.check, username, session.delay)
    session.record(status, username)

    if status == AVAILABLE:
        text = (
            f"{E['hit']} <b>AVAILABLE!</b> {E['sparkle']}\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"{E['user']} <b>Username:</b> <code>@{username}</code>\n"
            f"{E['link']} <b>Link:</b> <a href=\"https://t.me/{username}\">t.me/{username}</a>\n"
            f"\n"
            f"{THICK_DIVIDER}\n"
            f"{E['stats']} Checked: {session.checked} {DIVIDER} Hits: {session.hits}\n"
            f"\n"
            f"{E['bulb']} <i>Claim it now before someone else does!</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['link']} Open in Telegram", url=f"https://t.me/{username}")],
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
        ])
    elif status == TAKEN:
        text = (
            f"{E['taken']} <b>Taken</b>\n"
            f"{DIVIDER}\n"
            f"{E['user']} <code>@{username}</code> is already registered."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
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
            f"Too many requests. Try again later or use a proxy."
        )
        kb = None
    else:
        text = (
            f"{E['error']} <b>Error</b>\n"
            f"{DIVIDER}\n"
            f"Failed to check <code>@{username}</code>. Try again."
        )
        kb = None

    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_batch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /batch user1,user2,user3."""
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/batch user1,user2,user3</code>\n\n"
            f"<i>Example:</i> <code>/batch abc,xyz,test123</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = " ".join(ctx.args)
    usernames = [u.strip().lower().lstrip("@") for u in raw.split(",") if u.strip()]
    if not usernames:
        await update.message.reply_text(f"{E['error']} No usernames provided.")
        return

    session = get_session(update.effective_user.id)
    session.running = True
    session.should_stop = False

    bar = progress_bar(0, len(usernames))
    msg = await update.message.reply_text(
        f"{E['start']} <b>Batch Check Started</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"{E['pack']} <b>Usernames:</b> {len(usernames)}\n"
        f"{E['clock']} <b>Delay:</b> {session.delay}s\n"
        f"\n"
        f"<code>{bar}</code> 0/{len(usernames)}\n"
        f"\n"
        f"<i>Starting...</i>",
        parse_mode=ParseMode.HTML,
    )

    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}

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
                await msg.edit_text(
                    f"{E['start']} <b>Batch Check Running</b>\n"
                    f"{THICK_DIVIDER}\n"
                    f"\n"
                    f"<code>{bar}</code> {i + 1}/{len(usernames)} ({pct(i + 1, len(usernames))})\n"
                    f"\n"
                    f"  {E['hit']} Available: {len(results[AVAILABLE])}\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['invalid']} Invalid: {len(results[INVALID])}\n"
                    f"  {E['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n"
                    f"\n"
                    f"<i>Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False

    # Final report
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    stopped = f"{E['stop']} <b>Stopped!</b>\n\n" if session.should_stop else ""

    bar = progress_bar(len(usernames), len(usernames))
    text = (
        f"{stopped}"
        f"{E['trophy']} <b>Batch Check Complete</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"<code>{bar}</code> {len(usernames)}/{len(usernames)} (100%)\n"
        f"\n"
        f"  {E['chart']} <b>Results:</b>\n"
        f"    {E['check']} Total: {len(usernames)}\n"
        f"    {E['hit']} Available: {len(results[AVAILABLE])}\n"
        f"    {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"    {E['invalid']} Invalid: {len(results[INVALID])}\n"
        f"    {E['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n"
        f"\n"
        f"  {E['target']} <b>Available Usernames:</b>\n"
        f"{hit_list}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
    ]) if results[AVAILABLE] else None

    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /generate — generate and check random usernames."""
    session = get_session(update.effective_user.id)
    count = 20

    if ctx.args:
        try:
            count = int(ctx.args[0])
            count = min(count, 100)
        except ValueError:
            pass

    session.running = True
    session.should_stop = False

    gen = UsernameGenerator(
        length=session.username_length,
        chars=session.char_set,
    )

    bar = progress_bar(0, count)
    msg = await update.message.reply_text(
        f"{E['fire']} <b>Generating & Checking</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['pack']} <b>Count:</b> {count}\n"
        f"  {E['settings']} <b>Length:</b> {session.username_length} chars\n"
        f"  {E['gear']} <b>Chars:</b> <code>{session.char_set_label}</code>\n"
        f"  {E['clock']} <b>Delay:</b> {session.delay}s\n"
        f"\n"
        f"<code>{bar}</code> 0/{count}\n"
        f"\n"
        f"<i>Starting...</i>",
        parse_mode=ParseMode.HTML,
    )

    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    gen_iter = gen.random_stream()

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
                await msg.edit_text(
                    f"{E['fire']} <b>Generating & Checking</b>\n"
                    f"{THICK_DIVIDER}\n"
                    f"\n"
                    f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
                    f"\n"
                    f"<code>{bar}</code> {i + 1}/{count} ({pct(i + 1, count)})\n"
                    f"\n"
                    f"  {E['hit']} Available: {len(results[AVAILABLE])}\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['invalid']} Invalid: {len(results[INVALID])}\n"
                    f"  {E['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n"
                    f"\n"
                    f"<i>Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False

    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    stopped = f"{E['stop']} <b>Stopped!</b>\n\n" if session.should_stop else ""

    bar = progress_bar(count, count)
    text = (
        f"{stopped}"
        f"{E['trophy']} <b>Generation Complete</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
        f"\n"
        f"<code>{bar}</code> {count}/{count} (100%)\n"
        f"\n"
        f"  {E['chart']} <b>Results:</b>\n"
        f"    {E['check']} Checked: {count}\n"
        f"    {E['hit']} Available: {len(results[AVAILABLE])}\n"
        f"    {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"    {E['invalid']} Invalid: {len(results[INVALID])}\n"
        f"    {E['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n"
        f"\n"
        f"  {E['target']} <b>Available Usernames:</b>\n"
        f"{hit_list}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="quick_generate")],
        [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
    ]) if results[AVAILABLE] else InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="quick_generate")],
    ])

    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /stats."""
    session = get_session(update.effective_user.id)

    # Visual bar for hit rate
    hit_rate = (session.hits / session.checked * 100) if session.checked > 0 else 0
    hit_bar = progress_bar(session.hits, max(session.checked, 1), 12)

    text = (
        f"{E['stats']} <b>Session Statistics</b>\n"
        f"{THICK_DIVIDER}\n"
        f"\n"
        f"  {E['chart']} <b>Overview:</b>\n"
        f"    {E['check']} Checked: <b>{session.checked}</b>\n"
        f"    {E['hit']} Available: <b>{session.hits}</b>\n"
        f"    {E['taken']} Taken: <b>{session.taken}</b>\n"
        f"    {E['invalid']} Invalid: <b>{session.invalid}</b>\n"
        f"    {E['rate']} Rate Limit: <b>{session.rate_limited}</b>\n"
        f"    {E['error']} Errors: <b>{session.errors}</b>\n"
        f"\n"
        f"  {E['target']} <b>Hit Rate:</b>\n"
        f"    <code>{hit_bar}</code> {hit_rate:.1f}%\n"
    )

    if session.available:
        recent = session.available[-8:]
        hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in recent)
        text += f"\n  {E['star']} <b>Recent Hits:</b>\n{hit_list}"
        if len(session.available) > 8:
            text += f"\n    <i>... and {len(session.available) - 8} more</i>"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{E['hit']} Export Hits", callback_data="export_hits"),
            InlineKeyboardButton(f"{E['stop']} Reset", callback_data="confirm_reset_stats"),
        ],
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
            f"Will finish the current check shortly.",
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
            InlineKeyboardButton(f"{E['back']} Reset All to Defaults", callback_data="confirm_reset_settings"),
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
            f"{E['telegram']} <b>{BOT_USERNAME} v{VERSION}</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['check']} <b>/check</b> — Check one username\n"
            f"  {E['pack']} <b>/batch</b> — Check multiple at once\n"
            f"  {E['magic']} <b>/generate</b> — Generate & check random names\n"
            f"  {E['settings']} <b>/settings</b> — Configure length, delay, chars\n"
            f"  {E['stats']} <b>/stats</b> — View your session statistics\n"
            f"  {E['bulb']} <b>/help</b> — Full guide & username rules\n"
            f"\n"
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
                InlineKeyboardButton(f"{E['bulb']} Help", callback_data="help"),
            ],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "quick_generate":
        # Trigger a quick generate with defaults
        session.running = True
        session.should_stop = False
        count = 20

        gen = UsernameGenerator(length=session.username_length, chars=session.char_set)

        bar = progress_bar(0, count)
        await query.edit_message_text(
            f"{E['fire']} <b>Generating & Checking</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
            f"\n"
            f"<code>{bar}</code> 0/{count}\n"
            f"\n"
            f"<i>Starting...</i>",
            parse_mode=ParseMode.HTML,
        )

        results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
        gen_iter = gen.random_stream()

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
                    await query.edit_message_text(
                        f"{E['fire']} <b>Generating & Checking</b>\n"
                        f"{THICK_DIVIDER}\n"
                        f"\n"
                        f"  {E['settings']} Length: {session.username_length} {DIVIDER} Chars: <code>{session.char_set_label}</code>\n"
                        f"\n"
                        f"<code>{bar}</code> {i + 1}/{count} ({pct(i + 1, count)})\n"
                        f"\n"
                        f"  {E['hit']} Available: {len(results[AVAILABLE])}\n"
                        f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                        f"\n"
                        f"<i>Checking...</i>",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass

        session.running = False

        hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
        bar = progress_bar(count, count)
        text = (
            f"{E['trophy']} <b>Generation Complete</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"<code>{bar}</code> {count}/{count} (100%)\n"
            f"\n"
            f"  {E['hit']} Available: {len(results[AVAILABLE])}\n"
            f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
            f"\n"
            f"  {E['target']} <b>Available Usernames:</b>\n"
            f"{hit_list}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="quick_generate")],
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
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
            [InlineKeyboardButton(f"{E['back']} Reset All", callback_data="confirm_reset_settings")],
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
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"📏 <b>Choose Username Length</b>\n"
            f"{DIVIDER}\n"
            f"<i>Telegram allows 5-32 characters</i>",
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
                f"{'👉 ' if current == 'a-z 0-9 _' else ''}a-z 0-9 _",
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
            f"<i>Current: <code>{session.char_set_label}</code></i>",
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
        await query.edit_message_text(
            f"{E['yes']} <b>Settings reset to defaults!</b>",
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
            f"  • All other counters",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data == "reset_stats":
        session.reset_stats()
        await query.edit_message_text(
            f"{E['yes']} <b>Statistics reset!</b>\n\n"
            f"<i>Start a new check with /check, /batch, or /generate.</i>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "export_hits":
        if session.available:
            hit_list = "\n".join(f"@{u}" for u in session.available)
            await query.edit_message_text(
                f"{E['memo']} <b>Your Available Usernames ({len(session.available)})</b>\n"
                f"{THICK_DIVIDER}\n"
                f"\n"
                f"<code>{hit_list}</code>\n"
                f"\n"
                f"<i>Copy and save these!</i>",
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
        hit_rate = (session.hits / session.checked * 100) if session.checked > 0 else 0
        hit_bar = progress_bar(session.hits, max(session.checked, 1), 12)

        text = (
            f"{E['stats']} <b>Session Statistics</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['check']} Checked: <b>{session.checked}</b>\n"
            f"  {E['hit']} Available: <b>{session.hits}</b>\n"
            f"  {E['taken']} Taken: <b>{session.taken}</b>\n"
            f"  {E['invalid']} Invalid: <b>{session.invalid}</b>\n"
            f"  {E['rate']} Rate Limit: <b>{session.rate_limited}</b>\n"
            f"  {E['error']} Errors: <b>{session.errors}</b>\n"
            f"\n"
            f"  {E['target']} <b>Hit Rate:</b>\n"
            f"    <code>{hit_bar}</code> {hit_rate:.1f}%\n"
        )
        if session.available:
            recent = session.available[-5:]
            hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in recent)
            text += f"\n  {E['star']} <b>Recent Hits:</b>\n{hit_list}"

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['hit']} Export Hits", callback_data="export_hits"),
                InlineKeyboardButton(f"{E['stop']} Reset", callback_data="confirm_reset_stats"),
            ],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Help ──
    elif data == "help":
        text = (
            f"{E['bulb']} <b>Quick Help</b>\n"
            f"{THICK_DIVIDER}\n"
            f"\n"
            f"  {E['check']} <b>/check username</b> — Check one\n"
            f"  {E['pack']} <b>/batch a,b,c</b> — Check multiple\n"
            f"  {E['magic']} <b>/generate [N]</b> — Random names\n"
            f"  {E['settings']} <b>/settings</b> — Configure\n"
            f"  {E['stats']} <b>/stats</b> — View stats\n"
            f"  {E['stop']} <b>/stop</b> — Stop operation\n"
            f"\n"
            f"  {E['sparkle']} <b>Quick Check:</b> Just type a username!\n"
            f"\n"
            f"{E['pin']} <b>Username Rules:</b>\n"
            f"  5-32 chars • a-z, 0-9, _ • starts with letter"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


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
            f"<i>Rules: 5-32 chars, a-z/0-9/_ only, starts with letter.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    msg = await update.message.reply_text(
        f"{E['clock']} <b>Checking</b> <code>@{text}</code>...",
        parse_mode=ParseMode.HTML,
    )

    status, _ = await asyncio.to_thread(client.check, text, session.delay)
    session.record(status, text)

    if status == AVAILABLE:
        result = (
            f"{E['hit']} <b>AVAILABLE!</b> {E['sparkle']}\n"
            f"{DIVIDER}\n"
            f"{E['user']} <code>@{text}</code>\n"
            f"{E['link']} <a href=\"https://t.me/{text}\">t.me/{text}</a>\n"
            f"\n"
            f"{E['stats']} Checked: {session.checked} {DIVIDER} Hits: {session.hits}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['link']} Open", url=f"https://t.me/{text}")],
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
        ])
    elif status == TAKEN:
        result = f"{E['taken']} <code>@{text}</code> is taken."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")],
        ])
    elif status == INVALID:
        result = f"{E['invalid']} <code>@{text}</code> is invalid."
        kb = None
    elif status == RATE_LIMITED:
        result = f"{E['rate']} Rate limited. Try again later."
        kb = None
    else:
        result = f"{E['error']} Error checking <code>@{text}</code>."
        kb = None

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
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("cancel", cmd_stop))

    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Message handler for quick checks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"🤖 {BOT_USERNAME} v{VERSION} is running...")
    print("Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)
