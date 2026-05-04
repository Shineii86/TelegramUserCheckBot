"""
Telegram Bot — interactive Telegram username checker.
v3.0 — Full UI/UX overhaul with short callback_data, unified renderers, and robust error handling.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, WebAppInfo, MenuButtonWebApp
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

from checker.telegram_client import (
    TelegramUsernameClient,
    AVAILABLE, TAKEN, INVALID, RATE_LIMITED, ERROR,
    is_valid_username,
)
from checker.generator import UsernameGenerator


# ── Constants ──
VERSION = "3.2"
DIVIDER = "─" * 26
THICK_DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━"
THIN_DIVIDER = "· · · · · · · · · · · · · ·"
BOT_USERNAME = "TelegramUserCheckBot"
BOT_AUTHOR = "@Shineii86"
WEBAPP_URL = "https://your-domain.com"  # ← Set your hosted webapp URL
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
    "dart": "🎯", "sparkle": "✨", "pin": "📌",
    "shield": "🛡️", "zap": "⚡", "memo": "📝", "globe": "🌐",
    "ping": "🏓", "about": "ℹ️", "history": "📜", "copy": "📋",
    "heart": "❤️", "rocket": "🚀", "diamond": "💎",
    "time": "⏰", "refresh": "🔄", "export": "📤", "folder": "📁",
    "lightning": "⚡", "rainbow": "🌈", "party": "🎉",
    "eyes": "👀", "brain": "🧠", "magnifier": "🔎", "crystal": "🔮",
}


# ── Helpers ──
def progress_bar(current: int, total: int, length: int = 10) -> str:
    if total == 0:
        return "░" * length
    filled = int(length * current / total)
    return "█" * filled + "░" * (length - filled)


def pct(current: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{int(100 * current / total)}%"


def format_uptime(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"


def format_time_ago(dt: datetime) -> str:
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


async def safe_edit(msg, text, **kwargs):
    """Edit a message, silently ignoring 'message is not modified' errors."""
    try:
        await msg.edit_text(text, **kwargs)
    except BadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise


# ── User Session ──
class UserSession:
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
        self.history: list = []
        self.username_length = 5
        self.char_set = "abcdefghijklmnopqrstuvwxyz0123456789_"
        self.delay = 1.0
        self.max_workers = 5
        self.generation_mode = "random"
        self.pattern = ""

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
        sets = {
            "abcdefghijklmnopqrstuvwxyz0123456789_": "a-z 0-9 _",
            "abcdefghijklmnopqrstuvwxyz": "a-z only",
            "abcdefghijklmnopqrstuvwxyz0123456789": "a-z 0-9",
            "0123456789": "0-9 only",
        }
        return sets.get(self.char_set, self.char_set)

    @property
    def hit_rate(self) -> float:
        return (self.hits / self.checked * 100) if self.checked > 0 else 0.0

    def status_emoji(self, status: str) -> str:
        return {
            AVAILABLE: E["hit"], TAKEN: E["taken"], INVALID: E["invalid"],
            RATE_LIMITED: E["rate"], ERROR: E["error"],
        }.get(status, E["error"])


# ── Global State ──
sessions: dict[int, UserSession] = {}
client: Optional[TelegramUsernameClient] = None


def get_session(user_id: int) -> UserSession:
    if user_id not in sessions:
        sessions[user_id] = UserSession()
    return sessions[user_id]


# ============================================================================
# UNIFIED RENDERERS — single source of truth for each screen
# ============================================================================

def render_start(user) -> tuple[str, InlineKeyboardMarkup]:
    hour = datetime.now(timezone.utc).hour
    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 17:
        greeting = "Good afternoon"
    elif 17 <= hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Hey"
    text = (
        f"{E['wave']} <b>{greeting}, {user.first_name}!</b>\n\n"
        f"{E['telegram']} <b>{BOT_USERNAME}</b> <i>v{VERSION}</i>\n"
        f"{THICK_DIVIDER}\n\n"
        f"{E['magnifier']} <b>Telegram Username Checker</b>\n"
        f"{E['lightning']} Fast  {E['shield']} Reliable  {E['sparkle']} Free\n\n"
        f"<b>{E['pin']} Quick Actions:</b>\n\n"
        f"  {E['check']}  <b>/check</b> <code>username</code> — Check one name\n"
        f"  {E['pack']}  <b>/batch</b> <code>a,b,c</code> — Check multiple\n"
        f"  {E['magic']}  <b>/generate</b> <code>[N]</code> — Random names\n"
        f"  {E['crystal']}  <b>/pattern</b> <code>tmpl</code> — Pattern templates\n"
        f"  {E['settings']}  <b>/settings</b> — Tune your preferences\n"
        f"  {E['stats']}  <b>/stats</b> — View session stats\n"
        f"  {E['history']}  <b>/history</b> — Recent check log\n"
        f"  {E['ping']}  <b>/ping</b> — Bot status & uptime\n"
        f"  {E['bulb']}  <b>/help</b> — Full guide & rules\n\n"
        f"{THIN_DIVIDER}\n"
        f"{E['sparkle']} <i>Just type a username to quick-check it!</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['check']} Quick Check", switch_inline_query_current_chat=""),
         InlineKeyboardButton(f"{E['magic']} Generate", callback_data="qg")],
        [InlineKeyboardButton(f"🌐 Open Checker", web_app=WebAppInfo(url=WEBAPP_URL)),
         InlineKeyboardButton(f"{E['settings']} Settings", callback_data="s")],
        [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="st"),
         InlineKeyboardButton(f"{E['history']} History", callback_data="hi")],
        [InlineKeyboardButton(f"{E['bulb']} Help", callback_data="hp")],
    ])
    return text, kb


def render_help() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"{E['bulb']} <b>How to Use {BOT_USERNAME}</b>\n{THICK_DIVIDER}\n\n"
        f"<b>{E['check']} /check</b> <code>username</code> — Check one\n"
        f"<b>{E['pack']} /batch</b> <code>a,b,c</code> — Check multiple\n"
        f"<b>{E['magic']} /generate</b> <code>[N]</code> — Random names\n"
        f"<b>{E['crystal']} /pattern</b> <code>tmpl</code> — Pattern templates\n"
        f"<b>{E['settings']} /settings</b> — Configure\n"
        f"<b>{E['stats']} /stats</b> — View stats\n"
        f"<b>{E['history']} /history</b> — Recent checks\n"
        f"<b>{E['ping']} /ping</b> — Bot status\n"
        f"<b>{E['about']} /about</b> — Bot info\n"
        f"<b>{E['stop']} /stop</b> — Stop operation\n\n"
        f"{E['pin']} <b>Username Rules:</b>\n"
        f"  5–32 chars • a-z, 0-9, _ • starts with letter\n"
        f"  No double __ • Can't end with _\n\n"
        f"{E['crystal']} <b>Pattern Syntax:</b>\n"
        f"  <code>?</code>=letter <code>#</code>=digit <code>!</code>=alnum"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['back']} Back", callback_data="b")]])
    return text, kb


def render_settings(session: UserSession) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"{E['settings']} <b>Settings</b>\n{THICK_DIVIDER}\n\n"
        f"  📏 <b>Length:</b> {session.username_length}\n"
        f"  🔤 <b>Chars:</b> <code>{session.char_set_label}</code>\n"
        f"  {E['clock']} <b>Delay:</b> {session.delay}s\n"
        f"  🧵 <b>Workers:</b> {session.max_workers}\n"
        f"  {E['gear']} <b>Gen Mode:</b> {session.generation_mode}\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📏 {session.username_length} chars", callback_data="sl"),
         InlineKeyboardButton(f"🔤 {session.char_set_label}", callback_data="sc")],
        [InlineKeyboardButton(f"{E['clock']} {session.delay}s delay", callback_data="sd"),
         InlineKeyboardButton(f"🧵 {session.max_workers} workers", callback_data="sw")],
        [InlineKeyboardButton(f"{E['gear']} {session.generation_mode}", callback_data="sg"),
         InlineKeyboardButton(f"{E['crystal']} pattern", callback_data="pm")],
        [InlineKeyboardButton(f"{E['refresh']} Reset All", callback_data="crs"),
         InlineKeyboardButton(f"{E['back']} Back", callback_data="b")],
    ])
    return text, kb


def render_stats(session: UserSession) -> tuple[str, InlineKeyboardMarkup]:
    hit_bar = progress_bar(session.hits, max(session.checked, 1), 12)
    text = (
        f"{E['stats']} <b>Session Statistics</b>\n{THICK_DIVIDER}\n\n"
        f"  {E['magnifier']} Checked: <b>{session.checked}</b>\n"
        f"  {E['hit']} Available: <b>{session.hits}</b>\n"
        f"  {E['taken']} Taken: <b>{session.taken}</b>\n"
        f"  {E['invalid']} Invalid: <b>{session.invalid}</b>\n"
        f"  {E['rate']} Rate Limit: <b>{session.rate_limited}</b>\n"
        f"  {E['error']} Errors: <b>{session.errors}</b>\n\n"
        f"  {E['target']} <b>Hit Rate:</b>\n    <code>{hit_bar}</code> {session.hit_rate:.1f}%\n"
    )
    if session.available:
        recent = session.available[-5:]
        hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in recent)
        text += f"\n  {E['star']} <b>Recent Hits:</b>\n{hit_list}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['export']} Export", callback_data="ex"),
         InlineKeyboardButton(f"{E['history']} History", callback_data="hi")],
        [InlineKeyboardButton(f"{E['refresh']} Reset", callback_data="crst"),
         InlineKeyboardButton(f"{E['back']} Back", callback_data="b")],
    ])
    return text, kb


def render_history(session: UserSession) -> tuple[str, InlineKeyboardMarkup]:
    if not session.history:
        text = f"{E['history']} <b>History</b>\n{DIVIDER}\n\n  {E['no']} No checks yet.\n\n<i>Start with /check or /generate!</i>"
    else:
        lines = []
        for ts, username, status in reversed(session.history[-15:]):
            emoji = session.status_emoji(status)
            time_str = format_time_ago(ts)
            lines.append(f"  {emoji} <code>@{username}</code>  <i>{time_str}</i>")
        text = (
            f"{E['history']} <b>Recent Checks</b>\n{THICK_DIVIDER}\n\n"
            + "\n".join(lines)
            + f"\n\n{THIN_DIVIDER}\n  {E['chart']} Total: {session.checked} checked  {E['diamond']} {session.hits} hits"
        )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="st"),
         InlineKeyboardButton(f"{E['export']} Export", callback_data="ex")],
        [InlineKeyboardButton(f"{E['back']} Back", callback_data="b")],
    ])
    return text, kb


def render_export(session: UserSession) -> tuple[str, InlineKeyboardMarkup]:
    if session.available:
        hit_list = "\n".join(f"@{u}" for u in session.available)
        text = f"{E['export']} <b>Available Usernames ({len(session.available)})</b>\n{THICK_DIVIDER}\n\n<code>{hit_list}</code>\n\n<i>Copy above!</i>"
    else:
        text = f"{E['no']} No hits yet. Run /check or /generate first."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['back']} Back", callback_data="st")]])
    return text, kb


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text, kb = render_start(update.effective_user)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text, kb = render_help()
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/check username</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    username = ctx.args[0].strip().lower().lstrip("@")
    if not is_valid_username(username):
        await update.message.reply_text(
            f"{E['invalid']} <b>Invalid:</b> <code>@{username}</code>\n"
            f"5–32 chars, a-z/0-9/_, starts with letter, no double __",
            parse_mode=ParseMode.HTML,
        )
        return
    session = get_session(update.effective_user.id)
    msg = await update.message.reply_text(
        f"{E['clock']} <b>Checking</b> <code>@{username}</code>...",
        parse_mode=ParseMode.HTML,
    )
    status, _ = await asyncio.to_thread(client.check, username, session.delay)
    session.record(status, username)
    text, kb = _render_check_result(username, status, session)
    await safe_edit(msg, text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_batch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/batch user1,user2,user3</code>",
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
            f"{E['rate']} Max 200 per batch. You provided {len(usernames)}.",
            parse_mode=ParseMode.HTML,
        )
        return
    session = get_session(update.effective_user.id)
    session.running = True
    session.should_stop = False
    bar = progress_bar(0, len(usernames))
    msg = await update.message.reply_text(
        f"{E['start']} <b>Batch Check Started</b>\n{THICK_DIVIDER}\n\n"
        f"  {E['pack']} <b>Usernames:</b> {len(usernames)}\n"
        f"  {E['clock']} <b>Delay:</b> {session.delay}s\n\n"
        f"<code>{bar}</code> 0/{len(usernames)}\n\n<i>{E['rocket']} Launching...</i>",
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
        if (i + 1) % 3 == 0 or i == len(usernames) - 1:
            try:
                bar = progress_bar(i + 1, len(usernames))
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                await safe_edit(
                    msg,
                    f"{E['fire']} <b>Batch Running</b>\n{THICK_DIVIDER}\n\n"
                    f"<code>{bar}</code> {i+1}/{len(usernames)} ({pct(i+1, len(usernames))})\n\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n\n<i>{E['clock']} Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
    session.running = False
    elapsed = time.time() - start_time
    stopped = f"{E['stop']} <b>Stopped</b>\n\n" if session.should_stop else ""
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    bar = progress_bar(len(usernames), len(usernames))
    text = (
        f"{stopped}{E['trophy']} <b>Batch Complete</b>\n{THICK_DIVIDER}\n\n"
        f"<code>{bar}</code> {len(usernames)}/{len(usernames)} (100%)\n\n"
        f"  {E['chart']} <b>Results:</b>\n"
        f"    {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
        f"    {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"    {E['time']} Time: {format_uptime(elapsed)}\n\n"
        f"  {E['target']} <b>Available:</b>\n{hit_list}"
    )
    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(f"{E['export']} Export Hits ({len(results[AVAILABLE])})", callback_data="ex")])
    buttons.append([
        InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
        InlineKeyboardButton(f"{E['magic']} Generate", callback_data="qg"),
    ])
    await safe_edit(msg, text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    count = 20
    if ctx.args:
        try:
            count = max(1, min(int(ctx.args[0]), 100))
        except ValueError:
            if ctx.args[0] in ("random", "word_combo", "mixed"):
                session.generation_mode = ctx.args[0]
                if len(ctx.args) > 1:
                    try:
                        count = max(1, min(int(ctx.args[1]), 100))
                    except Exception:
                        pass
    await _run_generation(update.message, session, count)


async def cmd_pattern(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/pattern template</code>\n\n"
            f"<b>Syntax:</b>\n  <code>?</code>=letter <code>#</code>=digit <code>!</code>=alnum\n\n"
            f"<b>Example:</b> <code>/pattern user_????</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    pattern = ctx.args[0]
    valid, err = UsernameGenerator.validate_pattern(pattern)
    if not valid:
        await update.message.reply_text(
            f"{E['invalid']} <b>Invalid:</b> {err}",
            parse_mode=ParseMode.HTML,
        )
        return
    session = get_session(update.effective_user.id)
    session.pattern = pattern
    count = 20
    if len(ctx.args) > 1:
        try:
            count = max(1, min(int(ctx.args[1]), 100))
        except Exception:
            pass
    await _run_generation(update.message, session, count, pattern=pattern)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    text, kb = render_stats(session)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    text, kb = render_history(session)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uptime = time.time() - START_TIME
    session = get_session(update.effective_user.id)
    text = (
        f"{E['ping']} <b>Pong!</b>\n{DIVIDER}\n\n"
        f"  {E['zap']} <b>Uptime:</b> {format_uptime(uptime)}\n"
        f"  {E['telegram']} <b>Version:</b> v{VERSION}\n"
        f"  {E['chart']} <b>Your Stats:</b> {session.checked} checked, {session.hits} hits\n\n"
        f"{E['rocket']} <i>All systems operational!</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        f"{E['about']} <b>About {BOT_USERNAME}</b>\n{THICK_DIVIDER}\n\n"
        f"  {E['magnifier']} <b>What:</b> Username Availability Checker\n"
        f"  {E['globe']} <b>How:</b> Scrapes t.me pages (no API keys!)\n"
        f"  {E['gear']} <b>Version:</b> {VERSION}\n"
        f"  {E['brain']} <b>Author:</b> {BOT_AUTHOR}\n\n"
        f"{THIN_DIVIDER}\n{E['heart']} <i>Star the repo if useful!</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['link']} GitHub", url="https://github.com/Shineii86/TelegramUserCheckBot")],
        [InlineKeyboardButton(f"{E['back']} Back", callback_data="b")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    if session.running:
        session.should_stop = True
        await update.message.reply_text(
            f"{E['stop']} <b>Stopping...</b>\n{DIVIDER}\nWill finish current check shortly.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"{E['bulb']} Nothing running. Start with /check, /batch, or /generate.",
            parse_mode=ParseMode.HTML,
        )


async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    text, kb = render_settings(session)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ============================================================================
# SHARED RESULT RENDERER
# ============================================================================

def _render_check_result(username: str, status: str, session: UserSession) -> tuple[str, InlineKeyboardMarkup]:
    """Render the result of a single username check."""
    if status == AVAILABLE:
        text = (
            f"{E['party']} <b>AVAILABLE!</b> {E['sparkle']}\n{THICK_DIVIDER}\n"
            f"  {E['user']} <code>@{username}</code>\n"
            f"  {E['link']} <a href=\"https://t.me/{username}\">t.me/{username}</a>\n\n"
            f"  {E['chart']} Session: {session.checked} checked  {E['diamond']} {session.hits} hits"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['link']} Open in Telegram", url=f"https://t.me/{username}")],
            [
                InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
                InlineKeyboardButton(f"{E['copy']} Copy Name", callback_data=f"c:{username}"),
            ],
        ])
    elif status == TAKEN:
        text = (
            f"{E['taken']} <b>Taken</b>\n{DIVIDER}\n"
            f"<code>@{username}</code> is already registered.\n\n"
            f"{E['bulb']} <i>Try /generate to find available names!</i>"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
                InlineKeyboardButton(f"{E['magic']} Generate", callback_data="qg"),
            ],
        ])
    elif status == RATE_LIMITED:
        text = f"{E['rate']} <b>Rate Limited</b>\n{DIVIDER}\nToo many requests. Try again later."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['settings']} Settings", callback_data="s")]])
    else:
        text = f"{E['error']} <b>Error</b>\n{DIVIDER}\nFailed to check <code>@{username}</code>."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['refresh']} Retry", callback_data=f"r:{username}")]])
    return text, kb


# ============================================================================
# GENERATION ENGINE (unified for generate, pattern, and callbacks)
# ============================================================================

async def _run_generation(target, session: UserSession, count: int, *, pattern: str = "", is_callback: bool = False):
    """Unified generation engine for /generate, /pattern, and callback triggers."""
    session.running = True
    session.should_stop = False

    gen = UsernameGenerator(length=session.username_length, chars=session.char_set)

    # Determine stream
    if pattern:
        gen_stream = gen.pattern_stream(pattern)
        mode_icon = E["crystal"]
        mode_label = f"Pattern: <code>{pattern}</code>"
    elif session.generation_mode == "word_combo":
        gen_stream = gen.word_combo_stream()
        mode_icon = E["brain"]
        mode_label = "Word Combos"
    elif session.generation_mode == "mixed":
        gen_stream = gen.mixed_stream()
        mode_icon = E["rainbow"]
        mode_label = "Mixed"
    else:
        gen_stream = gen.random_stream()
        mode_icon = E["fire"]
        mode_label = "Random"

    bar = progress_bar(0, count)
    header = (
        f"{mode_icon} <b>Generating & Checking</b>\n{THICK_DIVIDER}\n\n"
        f"  {E['gear']} Mode: {mode_label}\n"
        f"  {E['settings']} Length: {session.username_length}\n\n"
    )

    if is_callback:
        await safe_edit(
            target,
            f"{header}<code>{bar}</code> 0/{count}\n\n<i>{E['crystal']} Conjuring...</i>",
            parse_mode=ParseMode.HTML,
        )
        msg = target
    else:
        msg = await target.reply_text(
            f"{header}<code>{bar}</code> 0/{count}\n\n<i>{E['crystal']} Conjuring...</i>",
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
                text = (
                    f"{header}<code>{bar}</code> {i+1}/{count} ({pct(i+1, count)})\n\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n\n<i>{E['clock']} Checking...</i>"
                )
                await safe_edit(msg, text, parse_mode=ParseMode.HTML)
            except Exception:
                pass

    session.running = False
    elapsed = time.time() - start_time
    stopped = f"{E['stop']} <b>Stopped</b>\n\n" if session.should_stop else ""
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    bar = progress_bar(count, count)
    text = (
        f"{stopped}{E['trophy']} <b>Complete</b>\n{THICK_DIVIDER}\n\n"
        f"  {E['gear']} Mode: {mode_label}\n\n"
        f"<code>{bar}</code> {count}/{count} (100%)\n\n"
        f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
        f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"  {E['time']} Time: {format_uptime(elapsed)}\n\n"
        f"  {E['target']} <b>Available:</b>\n{hit_list}"
    )
    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(f"{E['export']} Export Hits ({len(results[AVAILABLE])})", callback_data="ex")])
    buttons.append([
        InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="qg"),
        InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
    ])
    await safe_edit(msg, text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


# ============================================================================
# CALLBACK HANDLER — short callback_data with colon-separated payloads
# ============================================================================

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = get_session(user_id)
    data = query.data

    # ── Navigation ──
    if data == "b":  # Back to start
        text, kb = render_start(query.from_user)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "hp":  # Help
        text, kb = render_help()
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Quick Generate ──
    elif data == "qg":
        await _run_generation(query.message, session, 20, is_callback=True)

    # ── Copy Username ──
    elif data.startswith("c:"):
        username = data[2:]
        await safe_edit(
            query.message,
            f"{E['copy']} <b>Ready to copy!</b>\n{DIVIDER}\n\n<code>@{username}</code>\n\n<i>Select and copy above.</i>",
            parse_mode=ParseMode.HTML,
        )

    # ── Retry Check ──
    elif data.startswith("r:"):
        username = data[2:]
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        text, kb = _render_check_result(username, status, session)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── History ──
    elif data == "hi":
        text, kb = render_history(session)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Stats ──
    elif data == "st":
        text, kb = render_stats(session)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Export ──
    elif data == "ex":
        text, kb = render_export(session)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Settings ──
    elif data == "s":
        text, kb = render_settings(session)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Set Length ──
    elif data == "sl":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'▸ ' if i == session.username_length else ''}{i}", callback_data=f"l:{i}") for i in [5, 6, 7]],
            [InlineKeyboardButton(f"{'▸ ' if i == session.username_length else ''}{i}", callback_data=f"l:{i}") for i in [8, 10, 12]],
            [InlineKeyboardButton(f"{'▸ ' if i == session.username_length else ''}{i}", callback_data=f"l:{i}") for i in [15, 20, 25]],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="s")],
        ])
        await safe_edit(
            query.message,
            f"📏 <b>Username Length</b>\n{DIVIDER}\nCurrent: <b>{session.username_length}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("l:"):
        val = int(data[2:])
        session.username_length = val
        await query.answer(f"✅ Length set to {val}")

    # ── Set Chars ──
    elif data == "sc":
        current = session.char_set_label
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'▸ ' if current == 'a-z 0-9 _' else ''}a-z 0-9 _", callback_data="ch:d")],
            [InlineKeyboardButton(f"{'▸ ' if current == 'a-z only' else ''}a-z only", callback_data="ch:a")],
            [InlineKeyboardButton(f"{'▸ ' if current == 'a-z 0-9' else ''}a-z 0-9", callback_data="ch:n")],
            [InlineKeyboardButton(f"{'▸ ' if current == '0-9 only' else ''}0-9 only", callback_data="ch:0")],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="s")],
        ])
        await safe_edit(
            query.message,
            f"🔤 <b>Character Set</b>\n{DIVIDER}\nCurrent: <code>{current}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("ch:"):
        sets = {
            "d": "abcdefghijklmnopqrstuvwxyz0123456789_",
            "a": "abcdefghijklmnopqrstuvwxyz",
            "n": "abcdefghijklmnopqrstuvwxyz0123456789",
            "0": "0123456789",
        }
        key = data[3:]
        session.char_set = sets.get(key, sets["d"])
        labels = {"d": "a-z 0-9 _", "a": "a-z only", "n": "a-z 0-9", "0": "0-9 only"}
        await query.answer(f"✅ Chars: {labels.get(key, key)}")

    # ── Set Delay ──
    elif data == "sd":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'▸ ' if d == session.delay else ''}{d}s", callback_data=f"d:{d}") for d in [0.5, 1.0, 2.0]],
            [InlineKeyboardButton(f"{'▸ ' if d == session.delay else ''}{d}s", callback_data=f"d:{d}") for d in [3.0, 5.0]],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="s")],
        ])
        await safe_edit(
            query.message,
            f"{E['clock']} <b>Delay</b>\n{DIVIDER}\nCurrent: <b>{session.delay}s</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("d:"):
        val = float(data[2:])
        session.delay = val
        await query.answer(f"✅ Delay: {val}s")

    # ── Set Workers ──
    elif data == "sw":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'▸ ' if i == session.max_workers else ''}{i}", callback_data=f"w:{i}") for i in [1, 3, 5]],
            [InlineKeyboardButton(f"{'▸ ' if i == session.max_workers else ''}{i}", callback_data=f"w:{i}") for i in [10, 20, 50]],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="s")],
        ])
        await safe_edit(
            query.message,
            f"🧵 <b>Workers</b>\n{DIVIDER}\nCurrent: <b>{session.max_workers}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("w:"):
        val = int(data[2:])
        session.max_workers = val
        await query.answer(f"✅ Workers: {val}")

    # ── Set Gen Mode ──
    elif data == "sg":
        current = session.generation_mode
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'▸ ' if current == 'random' else ''}🎲 Random", callback_data="gm:random")],
            [InlineKeyboardButton(f"{'▸ ' if current == 'word_combo' else ''}🧠 Word Combos", callback_data="gm:word_combo")],
            [InlineKeyboardButton(f"{'▸ ' if current == 'mixed' else ''}🌈 Mixed", callback_data="gm:mixed")],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="s")],
        ])
        await safe_edit(
            query.message,
            f"{E['gear']} <b>Generation Mode</b>\n{DIVIDER}\nCurrent: <b>{current}</b>\n\n  🎲 Random • 🧠 Word Combos • 🌈 Mixed",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("gm:"):
        mode = data[3:]
        session.generation_mode = mode
        labels = {"random": "🎲 Random", "word_combo": "🧠 Word Combos", "mixed": "🌈 Mixed"}
        await query.answer(f"✅ Mode: {labels.get(mode, mode)}")

    # ── Pattern Menu ──
    elif data == "pm":
        text = (
            f"{E['crystal']} <b>Pattern Templates</b>\n{THICK_DIVIDER}\n\n"
            f"  <code>?</code>=letter <code>#</code>=digit <code>!</code>=alnum\n\n"
            f"<b>Quick Templates:</b>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("user_????", callback_data="pt:u4")],
            [InlineKeyboardButton("name_##_ab", callback_data="pt:n2a")],
            [InlineKeyboardButton("pro_####", callback_data="pt:p4")],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="s")],
        ])
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data.startswith("pt:"):
        tpl_map = {"u4": "user_????", "n2a": "name_##_ab", "p4": "pro_####"}
        key = data[3:]
        pattern = tpl_map.get(key, "user_????")
        await _run_generation(query.message, session, 20, pattern=pattern, is_callback=True)

    # ── Confirm Resets ──
    elif data == "crs":  # Confirm Reset Settings
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['yes']} Yes, reset", callback_data="rs"),
             InlineKeyboardButton(f"{E['no']} Cancel", callback_data="s")],
        ])
        await safe_edit(
            query.message,
            f"{E['stop']} <b>Reset all settings?</b>\n{DIVIDER}\nDefaults: length=5, chars=a-z 0-9 _, delay=1s, workers=5",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data == "rs":  # Reset Settings
        session.username_length = 5
        session.char_set = "abcdefghijklmnopqrstuvwxyz0123456789_"
        session.delay = 1.0
        session.max_workers = 5
        session.generation_mode = "random"
        session.pattern = ""
        await query.answer("✅ Settings reset!")
        text, kb = render_settings(session)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "crst":  # Confirm Reset Stats
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['yes']} Yes, reset", callback_data="rst"),
             InlineKeyboardButton(f"{E['no']} Cancel", callback_data="st")],
        ])
        await safe_edit(
            query.message,
            f"{E['stop']} <b>Reset statistics?</b>\n{DIVIDER}\n{session.checked} checked, {session.hits} hits will be cleared.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data == "rst":  # Reset Stats
        session.reset_stats()
        session.history.clear()
        await query.answer("✅ Stats reset!")
        text, kb = render_stats(session)
        await safe_edit(query.message, text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Stop Check (from notifier buttons) ──
    elif data == "x":  # Stop
        if session.running:
            session.should_stop = True
            await query.answer("🛑 Stopping...")
        else:
            await query.answer("Nothing running.")



# ============================================================================
# WEB APP DATA HANDLER
# ============================================================================

async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle data sent from the Telegram Web App."""
    try:
        import json
        data = json.loads(update.message.web_app_data.data)
    except (ValueError, TypeError):
        await update.message.reply_text(
            f"{E['error']} Invalid data from web app.",
            parse_mode=ParseMode.HTML,
        )
        return

    action = data.get("action")
    session = get_session(update.effective_user.id)

    if action == "check":
        username = data.get("username", "").strip().lower()
        status = data.get("status", "error")
        session.record(status, username)
        text, kb = _render_check_result(username, status, session)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif action == "batch_result":
        # Batch results summary from webapp
        total = data.get("total", 0)
        hits = data.get("hits", 0)
        taken = data.get("taken", 0)
        errors = data.get("errors", 0)
        elapsed = data.get("elapsed", "0")
        available_list = data.get("available", [])

        # Record stats
        for _ in range(hits):
            session.record("available", "")
        for _ in range(taken):
            session.record("taken", "")
        for _ in range(errors):
            session.record("error", "")

        text = (
            f"{E['pack']} <b>Batch Check Complete</b>\n{THICK_DIVIDER}\n\n"
            f"  {E['magnifier']} Checked: <b>{total}</b>\n"
            f"  {E['hit']} Available: <b>{hits}</b>\n"
            f"  {E['taken']} Taken: <b>{taken}</b>\n"
            f"  {E['error']} Errors: <b>{errors}</b>\n\n"
            f"  {E['clock']} Time: <b>{elapsed}s</b>\n"
        )
        if available_list:
            hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in available_list[:10])
            text += f"\n  {E['star']} <b>Available Names:</b>\n{hit_list}"
            if len(available_list) > 10:
                text += f"\n    {E['bulb']} ...and {len(available_list) - 10} more"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['check']} Check Again", switch_inline_query_current_chat=""),
             InlineKeyboardButton(f"{E['magic']} Generate", callback_data="qg")],
            [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="st"),
             InlineKeyboardButton(f"{E['back']} Home", callback_data="b")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif action == "generate_result":
        # Generate results from webapp
        mode = data.get("mode", "random")
        total = data.get("total", 0)
        hits = data.get("hits", 0)
        taken = data.get("taken", 0)
        errors = data.get("errors", 0)
        elapsed = data.get("elapsed", "0")
        available_list = data.get("available", [])

        for _ in range(hits):
            session.record("available", "")
        for _ in range(taken):
            session.record("taken", "")
        for _ in range(errors):
            session.record("error", "")

        mode_label = {"random": "🎲 Random", "word_combo": "🧠 Word Combos", "mixed": "🌈 Mixed"}.get(mode, mode)
        text = (
            f"{E['magic']} <b>Generation Complete</b>\n{THICK_DIVIDER}\n\n"
            f"  {E['gear']} Mode: <b>{mode_label}</b>\n"
            f"  {E['magnifier']} Checked: <b>{total}</b>\n"
            f"  {E['hit']} Available: <b>{hits}</b>\n"
            f"  {E['taken']} Taken: <b>{taken}</b>\n"
            f"  {E['error']} Errors: <b>{errors}</b>\n\n"
            f"  {E['clock']} Time: <b>{elapsed}s</b>\n"
        )
        if available_list:
            hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in available_list[:10])
            text += f"\n  {E['star']} <b>Available Names:</b>\n{hit_list}"
            if len(available_list) > 10:
                text += f"\n    {E['bulb']} ...and {len(available_list) - 10} more"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="qg"),
             InlineKeyboardButton(f"{E['crystal']} Pattern", callback_data="pm")],
            [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="st"),
             InlineKeyboardButton(f"{E['back']} Home", callback_data="b")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif action == "pattern_result":
        # Pattern results from webapp
        pattern = data.get("pattern", "")
        total = data.get("total", 0)
        hits = data.get("hits", 0)
        taken = data.get("taken", 0)
        errors = data.get("errors", 0)
        elapsed = data.get("elapsed", "0")
        available_list = data.get("available", [])

        for _ in range(hits):
            session.record("available", "")
        for _ in range(taken):
            session.record("taken", "")
        for _ in range(errors):
            session.record("error", "")

        text = (
            f"{E['crystal']} <b>Pattern Check Complete</b>\n{THICK_DIVIDER}\n\n"
            f"  {E['memo']} Pattern: <code>{pattern}</code>\n"
            f"  {E['magnifier']} Checked: <b>{total}</b>\n"
            f"  {E['hit']} Available: <b>{hits}</b>\n"
            f"  {E['taken']} Taken: <b>{taken}</b>\n"
            f"  {E['error']} Errors: <b>{errors}</b>\n\n"
            f"  {E['clock']} Time: <b>{elapsed}s</b>\n"
        )
        if available_list:
            hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in available_list[:10])
            text += f"\n  {E['star']} <b>Available Names:</b>\n{hit_list}"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['crystal']} New Pattern", callback_data="pm"),
             InlineKeyboardButton(f"{E['magic']} Generate", callback_data="qg")],
            [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="st"),
             InlineKeyboardButton(f"{E['back']} Home", callback_data="b")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif action == "export":
        # Export available names from webapp
        names = data.get("names", [])
        if names:
            text = (
                f"{E['export']} <b>Exported Available Names</b>\n{THICK_DIVIDER}\n\n"
                + "\n".join(f"  {E['hit']} <code>@{n}</code>" for n in names)
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{E['check']} Check More", switch_inline_query_current_chat=""),
                 InlineKeyboardButton(f"{E['back']} Home", callback_data="b")],
            ])
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    else:
        await update.message.reply_text(
            f"{E['bulb']} Web app data received.",
            parse_mode=ParseMode.HTML,
        )


# ============================================================================
# MESSAGE HANDLER — quick check by typing a username
# ============================================================================

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lstrip("@").lower()
    if len(text) < 5 or len(text) > 32:
        return
    if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in text):
        return
    if not text[0].isalpha():
        return
    if not is_valid_username(text):
        await update.message.reply_text(
            f"{E['invalid']} <code>@{text}</code> is not valid.",
            parse_mode=ParseMode.HTML,
        )
        return
    session = get_session(update.effective_user.id)
    msg = await update.message.reply_text(
        f"{E['clock']} <b>Checking</b> <code>@{text}</code>...",
        parse_mode=ParseMode.HTML,
    )
    status, _ = await asyncio.to_thread(client.check, text, session.delay)
    session.record(status, text)
    result_text, kb = _render_check_result(text, status, session)
    await safe_edit(msg, result_text, parse_mode=ParseMode.HTML, reply_markup=kb)



# ============================================================================
# INLINE QUERY HANDLER
# ============================================================================

async def handle_inline_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip().lower().lstrip("@")
    if not query:
        return
    if len(query) < 2 or len(query) > 32:
        return

    results = []

    # If it looks like a valid username, offer to check it
    if all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in query) and query[0].isalpha():
        session = get_session(update.effective_user.id)
        status, _ = await asyncio.to_thread(client.check, query, 0)
        session.record(status, query)

        if status == AVAILABLE:
            results.append(
                InlineQueryResultArticle(
                    id=f"av_{query}",
                    title=f"✅ @{query} is AVAILABLE!",
                    description=f"Tap to send • t.me/{query}",
                    input_message_content=InputTextMessageContent(
                        f"{E['party']} <b>AVAILABLE!</b> {E['sparkle']}\n{THICK_DIVIDER}\n"
                        f"  {E['user']} <code>@{query}</code>\n"
                        f"  {E['link']} <a href=\"https://t.me/{query}\">t.me/{query}</a>\n\n"
                        f"  {E['bulb']} <i>Claim it now!</i>",
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    ),
                    thumbnail_url="https://img.icons8.com/color/48/checkmark.png",
                )
            )
        elif status == TAKEN:
            results.append(
                InlineQueryResultArticle(
                    id=f"tk_{query}",
                    title=f"❌ @{query} is taken",
                    description="Already registered on Telegram",
                    input_message_content=InputTextMessageContent(
                        f"{E['taken']} <b>Taken</b>\n{DIVIDER}\n<code>@{query}</code> is already registered.\n\n"
                        f"{E['bulb']} <i>Try /generate to find available names!</i>",
                        parse_mode=ParseMode.HTML,
                    ),
                    thumbnail_url="https://img.icons8.com/color/48/cancel.png",
                )
            )
        elif status == INVALID:
            results.append(
                InlineQueryResultArticle(
                    id=f"in_{query}",
                    title=f"🚫 @{query} is invalid",
                    description="5–32 chars, a-z/0-9/_, starts with letter",
                    input_message_content=InputTextMessageContent(
                        f"{E['invalid']} <code>@{query}</code> is not a valid Telegram username.\n"
                        f"Rules: 5–32 chars, a-z/0-9/_, starts with letter, no double __",
                        parse_mode=ParseMode.HTML,
                    ),
                )
            )
        else:
            results.append(
                InlineQueryResultArticle(
                    id=f"er_{query}",
                    title=f"⚠️ Error checking @{query}",
                    description="Rate limited or network error — try again",
                    input_message_content=InputTextMessageContent(
                        f"{E['error']} Could not check <code>@{query}</code>. Try again later.",
                        parse_mode=ParseMode.HTML,
                    ),
                )
            )
    else:
        # Not a valid username format — suggest using /generate
        results.append(
            InlineQueryResultArticle(
                id=f"bad_{query}",
                title=f"💡 Type a valid username to check",
                description="5–32 chars: a-z, 0-9, _ — must start with a letter",
                input_message_content=InputTextMessageContent(
                    f"{E['bulb']} <b>Quick Check</b>\n{DIVIDER}\n"
                    f"Type a valid Telegram username to check availability.\n\n"
                    f"<b>Rules:</b> 5–32 chars, a-z/0-9/_, starts with letter, no __\n\n"
                    f"<b>Or try:</b> /generate — find random available names!",
                    parse_mode=ParseMode.HTML,
                ),
            )
        )

    await update.inline_query.answer(results, cache_time=0, is_personal=True)


async def handle_chosen_inline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Track chosen inline results for analytics."""
    result_id = update.chosen_inline_result.result_id
    user_id = update.chosen_inline_result.from_user.id
    session = get_session(user_id)
    # result_id format: "av_username" or "tk_username"
    if "_" in result_id:
        parts = result_id.split("_", 1)
        if len(parts) == 2 and parts[0] == "av":
            pass  # Could add extra tracking here


# ============================================================================
# BOT RUNNER
# ============================================================================

def run_bot(token: str):
    """Initialize and run the Telegram bot. Works in both CLI and Jupyter/Colab."""
    global client
    client = TelegramUsernameClient(
        user_agents=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
    )
    app = Application.builder().token(token).build()

    # Commands
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

    # Callbacks, inline queries & messages
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(InlineQueryHandler(handle_inline_query))
    app.add_handler(ChosenInlineResultHandler(handle_chosen_inline))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set menu button to open web app (if URL configured)
    async def post_init(app):
        if WEBAPP_URL and WEBAPP_URL != "https://your-domain.com":
            try:
                await app.bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(text="🔍 Checker", web_app=WebAppInfo(url=WEBAPP_URL))
                )
            except Exception:
                pass
    app.post_init = post_init

    print(f"🤖 {BOT_USERNAME} v{VERSION} is running...")
    print("Press Ctrl+C to stop.")

    # Detect Jupyter/Colab
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__name__
        is_notebook = shell in ("ZMQInteractiveShell", "Shell")
    except (ImportError, NameError, AttributeError):
        is_notebook = False

    if not is_notebook:
        app.run_polling(drop_pending_updates=True)
    else:
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass
        app.run_polling(drop_pending_updates=True)
