"""
Telegram Bot — interactive Telegram username checker.
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
# ALL COMMAND HANDLERS (same as before, abbreviated for clarity)
# ============================================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    hour = datetime.now(timezone.utc).hour
    if 5 <= hour < 12: greeting = "Good morning"
    elif 12 <= hour < 17: greeting = "Good afternoon"
    elif 17 <= hour < 21: greeting = "Good evening"
    else: greeting = "Hey"
    text = (
        f"{E['wave']} <b>{greeting}, {user.first_name}!</b>\n\n"
        f"{E['telegram']} <b>{BOT_USERNAME}</b> <i>v{VERSION}</i>\n"
        f"{THICK_DIVIDER}\n\n"
        f"{E['magnifier']} <b>Telegram Username Availability Checker</b>\n"
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
         InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate")],
        [InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings"),
         InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats")],
        [InlineKeyboardButton(f"{E['history']} History", callback_data="history"),
         InlineKeyboardButton(f"{E['bulb']} Help", callback_data="help")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")]])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(f"{E['bulb']} <b>Usage:</b> <code>/check username</code>", parse_mode=ParseMode.HTML)
        return
    username = ctx.args[0].strip().lower().lstrip("@")
    if not is_valid_username(username):
        await update.message.reply_text(f"{E['invalid']} <b>Invalid:</b> <code>@{username}</code>\n5–32 chars, a-z/0-9/_, starts with letter, no double __", parse_mode=ParseMode.HTML)
        return
    session = get_session(update.effective_user.id)
    msg = await update.message.reply_text(f"{E['clock']} <b>Checking</b> <code>@{username}</code>...", parse_mode=ParseMode.HTML)
    status, _ = await asyncio.to_thread(client.check, username, session.delay)
    session.record(status, username)
    if status == AVAILABLE:
        text = f"{E['party']} <b>AVAILABLE!</b> {E['sparkle']}\n{THICK_DIVIDER}\n  {E['user']} <code>@{username}</code>\n  {E['link']} <a href=\"https://t.me/{username}\">t.me/{username}</a>\n\n  {E['chart']} Session: {session.checked} checked  {E['diamond']} {session.hits} hits"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['link']} Open", url=f"https://t.me/{username}")],
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
             InlineKeyboardButton(f"{E['copy']} Copy", callback_data=f"copy_{username}")],
        ])
    elif status == TAKEN:
        text = f"{E['taken']} <b>Taken</b>\n{DIVIDER}\n<code>@{username}</code> is already registered.\n\n{E['bulb']} <i>Try /generate to find available names!</i>"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
             InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate")],
        ])
    elif status == RATE_LIMITED:
        text = f"{E['rate']} <b>Rate Limited</b>\n{DIVIDER}\nToo many requests. Try again later."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings")]])
    else:
        text = f"{E['error']} <b>Error</b>\n{DIVIDER}\nFailed to check <code>@{username}</code>."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['refresh']} Retry", callback_data=f"retry_{username}")]])
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_batch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(f"{E['bulb']} <b>Usage:</b> <code>/batch user1,user2,user3</code>", parse_mode=ParseMode.HTML)
        return
    raw = " ".join(ctx.args)
    usernames = [u.strip().lower().lstrip("@") for u in raw.replace("\n", ",").replace(" ", ",").split(",") if u.strip()]
    if not usernames:
        await update.message.reply_text(f"{E['error']} No usernames provided.")
        return
    if len(usernames) > 200:
        await update.message.reply_text(f"{E['rate']} Max 200 per batch. You provided {len(usernames)}.", parse_mode=ParseMode.HTML)
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
        parse_mode=ParseMode.HTML)
    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    start_time = time.time()
    for i, username in enumerate(usernames):
        if session.should_stop: break
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        results[status].append(username)
        if (i + 1) % 3 == 0 or i == len(usernames) - 1:
            try:
                bar = progress_bar(i + 1, len(usernames))
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                await msg.edit_text(
                    f"{E['fire']} <b>Batch Running</b>\n{THICK_DIVIDER}\n\n"
                    f"<code>{bar}</code> {i+1}/{len(usernames)} ({pct(i+1, len(usernames))})\n\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n\n<i>{E['clock']} Checking...</i>",
                    parse_mode=ParseMode.HTML)
            except: pass
    session.running = False
    elapsed = time.time() - start_time
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    stopped = f"{E['stop']} <b>Stopped</b>\n\n" if session.should_stop else ""
    bar = progress_bar(len(usernames), len(usernames))
    text = (
        f"{stopped}{E['trophy']} <b>Batch Complete</b>\n{THICK_DIVIDER}\n\n"
        f"<code>{bar}</code> {len(usernames)}/{len(usernames)} (100%)\n\n"
        f"  {E['chart']} <b>Results:</b>\n"
        f"    {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
        f"    {E['taken']} Taken: {len(results[TAKEN])}\n"
        f"    {E['time']} Time: {format_uptime(elapsed)}\n\n"
        f"  {E['target']} <b>Available:</b>\n{hit_list}")
    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(f"{E['export']} Export Hits ({len(results[AVAILABLE])})", callback_data="export_hits")])
    buttons.append([InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat=""),
                    InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate")])
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def _run_generation(query_or_msg, session, count, is_callback=False):
    session.running = True
    session.should_stop = False
    gen = UsernameGenerator(length=session.username_length, chars=session.char_set)
    if session.generation_mode == "word_combo":
        gen_stream = gen.word_combo_stream(); mode_icon = E['brain']; mode_label = "Word Combos"
    elif session.generation_mode == "mixed":
        gen_stream = gen.mixed_stream(); mode_icon = E['rainbow']; mode_label = "Mixed"
    else:
        gen_stream = gen.random_stream(); mode_icon = E['fire']; mode_label = "Random"
    bar = progress_bar(0, count)
    header = f"{mode_icon} <b>Generating & Checking</b>\n{THICK_DIVIDER}\n\n  {E['gear']} Mode: {mode_label}\n  {E['settings']} Length: {session.username_length}\n\n"
    if is_callback:
        await query_or_msg.edit_message_text(f"{header}<code>{bar}</code> 0/{count}\n\n<i>{E['crystal']} Conjuring...</i>", parse_mode=ParseMode.HTML)
    else:
        msg = await query_or_msg.reply_text(f"{header}<code>{bar}</code> 0/{count}\n\n<i>{E['crystal']} Conjuring...</i>", parse_mode=ParseMode.HTML)
    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    start_time = time.time()
    for i in range(count):
        if session.should_stop: break
        username = next(gen_stream)
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        results[status].append(username)
        if (i + 1) % 3 == 0 or i == count - 1:
            try:
                bar = progress_bar(i + 1, count)
                elapsed = time.time() - start_time
                speed = (i + 1) / elapsed if elapsed > 0 else 0
                text = (f"{header}<code>{bar}</code> {i+1}/{count} ({pct(i+1, count)})\n\n"
                        f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                        f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                        f"  {E['zap']} Speed: {speed:.1f}/sec\n\n<i>{E['clock']} Checking...</i>")
                target = query_or_msg if is_callback else msg
                await target.edit_message_text(text, parse_mode=ParseMode.HTML)
            except: pass
    session.running = False
    elapsed = time.time() - start_time
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    stopped = f"{E['stop']} <b>Stopped</b>\n\n" if session.should_stop else ""
    bar = progress_bar(count, count)
    text = (f"{stopped}{E['trophy']} <b>Complete</b>\n{THICK_DIVIDER}\n\n"
            f"  {E['gear']} Mode: {mode_label}\n\n"
            f"<code>{bar}</code> {count}/{count} (100%)\n\n"
            f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
            f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
            f"  {E['time']} Time: {format_uptime(elapsed)}\n\n"
            f"  {E['target']} <b>Available:</b>\n{hit_list}")
    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(f"{E['export']} Export Hits ({len(results[AVAILABLE])})", callback_data="export_hits")])
    buttons.append([InlineKeyboardButton(f"{E['magic']} Generate More", callback_data="quick_generate"),
                    InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")])
    target = query_or_msg if is_callback else msg
    await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    count = 20
    if ctx.args:
        try: count = max(1, min(int(ctx.args[0]), 100))
        except ValueError:
            if ctx.args[0] in ("random", "word_combo", "mixed"):
                session.generation_mode = ctx.args[0]
                if len(ctx.args) > 1:
                    try: count = max(1, min(int(ctx.args[1]), 100))
                    except: pass
    await _run_generation(update.message, session, count)


async def cmd_pattern(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            f"{E['bulb']} <b>Usage:</b> <code>/pattern template</code>\n\n"
            f"<b>Syntax:</b>\n  <code>?</code>=letter <code>#</code>=digit <code>!</code>=alnum\n\n"
            f"<b>Example:</b> <code>/pattern user_????</code>",
            parse_mode=ParseMode.HTML)
        return
    pattern = ctx.args[0]
    valid, err = UsernameGenerator.validate_pattern(pattern)
    if not valid:
        await update.message.reply_text(f"{E['invalid']} <b>Invalid:</b> {err}", parse_mode=ParseMode.HTML)
        return
    session = get_session(update.effective_user.id)
    session.pattern = pattern
    count = 20
    if len(ctx.args) > 1:
        try: count = max(1, min(int(ctx.args[1]), 100))
        except: pass
    session.running = True
    session.should_stop = False
    gen = UsernameGenerator(length=session.username_length, chars=session.char_set)
    gen_stream = gen.pattern_stream(pattern)
    bar = progress_bar(0, count)
    msg = await update.message.reply_text(
        f"{E['crystal']} <b>Pattern Generation</b>\n{THICK_DIVIDER}\n\n"
        f"  {E['pin']} Pattern: <code>{pattern}</code>\n\n"
        f"<code>{bar}</code> 0/{count}\n\n<i>Generating...</i>",
        parse_mode=ParseMode.HTML)
    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    start_time = time.time()
    for i in range(count):
        if session.should_stop: break
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
                    f"{E['crystal']} <b>Pattern</b>\n{THICK_DIVIDER}\n\n  {E['pin']} <code>{pattern}</code>\n\n"
                    f"<code>{bar}</code> {i+1}/{count} ({pct(i+1, count)})\n\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n"
                    f"  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n\n<i>Checking...</i>",
                    parse_mode=ParseMode.HTML)
            except: pass
    session.running = False
    elapsed = time.time() - start_time
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    bar = progress_bar(count, count)
    text = (f"{E['trophy']} <b>Pattern Complete</b>\n{THICK_DIVIDER}\n\n  {E['pin']} <code>{pattern}</code>\n\n"
            f"<code>{bar}</code> {count}/{count} (100%)\n\n"
            f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n  {E['taken']} Taken: {len(results[TAKEN])}\n"
            f"  {E['time']} Time: {format_uptime(elapsed)}\n\n  {E['target']} <b>Available:</b>\n{hit_list}")
    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(f"{E['export']} Export Hits", callback_data="export_hits")])
    buttons.append([InlineKeyboardButton(f"{E['crystal']} Generate More", callback_data=f"pattern_more_{pattern}"),
                    InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")])
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    hit_bar = progress_bar(session.hits, max(session.checked, 1), 12)
    text = (
        f"{E['stats']} <b>Session Statistics</b>\n{THICK_DIVIDER}\n\n"
        f"  {E['magnifier']} Checked: <b>{session.checked}</b>\n"
        f"  {E['hit']} Available: <b>{session.hits}</b>\n"
        f"  {E['taken']} Taken: <b>{session.taken}</b>\n"
        f"  {E['invalid']} Invalid: <b>{session.invalid}</b>\n"
        f"  {E['rate']} Rate Limit: <b>{session.rate_limited}</b>\n"
        f"  {E['error']} Errors: <b>{session.errors}</b>\n\n"
        f"  {E['target']} <b>Hit Rate:</b>\n    <code>{hit_bar}</code> {session.hit_rate:.1f}%\n")
    if session.available:
        recent = session.available[-5:]
        hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in recent)
        text += f"\n  {E['star']} <b>Recent Hits:</b>\n{hit_list}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['export']} Export", callback_data="export_hits"),
         InlineKeyboardButton(f"{E['history']} History", callback_data="history")],
        [InlineKeyboardButton(f"{E['refresh']} Reset", callback_data="confirm_reset_stats"),
         InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    if not session.history:
        await update.message.reply_text(f"{E['history']} <b>History</b>\n{DIVIDER}\n\n  {E['no']} No checks yet.\n\n<i>Start with /check or /generate!</i>", parse_mode=ParseMode.HTML)
        return
    lines = []
    for ts, username, status in reversed(session.history[-15:]):
        emoji = session.status_emoji(status)
        time_str = format_time_ago(ts)
        lines.append(f"  {emoji} <code>@{username}</code>  <i>{time_str}</i>")
    text = f"{E['history']} <b>Recent Checks</b>\n{THICK_DIVIDER}\n\n" + "\n".join(lines) + f"\n\n{THIN_DIVIDER}\n  {E['chart']} Total: {session.checked} checked  {E['diamond']} {session.hits} hits"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats"),
         InlineKeyboardButton(f"{E['export']} Export", callback_data="export_hits")],
        [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uptime = time.time() - START_TIME
    session = get_session(update.effective_user.id)
    text = (f"{E['ping']} <b>Pong!</b>\n{DIVIDER}\n\n"
            f"  {E['zap']} <b>Uptime:</b> {format_uptime(uptime)}\n"
            f"  {E['telegram']} <b>Version:</b> v{VERSION}\n"
            f"  {E['chart']} <b>Your Stats:</b> {session.checked} checked, {session.hits} hits\n\n"
            f"{E['rocket']} <i>All systems operational!</i>")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (f"{E['about']} <b>About {BOT_USERNAME}</b>\n{THICK_DIVIDER}\n\n"
            f"  {E['magnifier']} <b>What:</b> Username Availability Checker\n"
            f"  {E['globe']} <b>How:</b> Scrapes t.me pages (no API keys!)\n"
            f"  {E['gear']} <b>Version:</b> {VERSION}\n"
            f"  {E['brain']} <b>Author:</b> {BOT_AUTHOR}\n\n"
            f"{THIN_DIVIDER}\n{E['heart']} <i>Star the repo if useful!</i>")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{E['link']} GitHub", url="https://github.com/Shineii86/TelegramUserCheckBot")],
        [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    if session.running:
        session.should_stop = True
        await update.message.reply_text(f"{E['stop']} <b>Stopping...</b>\n{DIVIDER}\nWill finish current check shortly.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"{E['bulb']} Nothing running. Start with /check, /batch, or /generate.", parse_mode=ParseMode.HTML)


async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    text = (f"{E['settings']} <b>Settings</b>\n{THICK_DIVIDER}\n\n"
            f"  📏 <b>Length:</b> {session.username_length}\n"
            f"  🔤 <b>Chars:</b> <code>{session.char_set_label}</code>\n"
            f"  {E['clock']} <b>Delay:</b> {session.delay}s\n"
            f"  🧵 <b>Workers:</b> {session.max_workers}\n"
            f"  {E['gear']} <b>Gen Mode:</b> {session.generation_mode}\n")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📏 Length ({session.username_length})", callback_data="set_length"),
         InlineKeyboardButton(f"🔤 Chars", callback_data="set_chars")],
        [InlineKeyboardButton(f"{E['clock']} Delay ({session.delay}s)", callback_data="set_delay"),
         InlineKeyboardButton(f"🧵 Workers ({session.max_workers})", callback_data="set_workers")],
        [InlineKeyboardButton(f"{E['gear']} Gen Mode ({session.generation_mode})", callback_data="set_gen_mode"),
         InlineKeyboardButton(f"{E['crystal']} Pattern", callback_data="pattern_menu")],
        [InlineKeyboardButton(f"{E['refresh']} Reset All", callback_data="confirm_reset_settings"),
         InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ============================================================================
# CALLBACK HANDLER
# ============================================================================

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = get_session(user_id)
    data = query.data

    if data == "back_start":
        user = query.from_user
        text = (f"{E['wave']} <b>Hey {user.first_name}!</b>\n\n{E['telegram']} <b>{BOT_USERNAME}</b> <i>v{VERSION}</i>\n{THICK_DIVIDER}\n\n"
                f"  {E['check']}  <b>/check</b> — Check one\n  {E['pack']}  <b>/batch</b> — Check multiple\n"
                f"  {E['magic']}  <b>/generate</b> — Random names\n  {E['crystal']}  <b>/pattern</b> — Pattern templates\n"
                f"  {E['settings']}  <b>/settings</b> — Configure\n  {E['stats']}  <b>/stats</b> — View stats\n"
                f"  {E['history']}  <b>/history</b> — Recent checks\n  {E['ping']}  <b>/ping</b> — Bot status\n"
                f"  {E['bulb']}  <b>/help</b> — Full guide\n\n{THIN_DIVIDER}\n{E['sparkle']} <i>Just type a username!</i>")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['check']} Quick Check", switch_inline_query_current_chat=""),
             InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate")],
            [InlineKeyboardButton(f"{E['crystal']} Pattern", callback_data="pattern_menu"),
             InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings")],
            [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats"),
             InlineKeyboardButton(f"{E['history']} History", callback_data="history")],
            [InlineKeyboardButton(f"{E['bulb']} Help", callback_data="help")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "quick_generate":
        await _run_generation(query, session, 20, is_callback=True)

    elif data.startswith("copy_"):
        username = data[5:]
        await query.edit_message_text(f"{E['copy']} <b>Ready to copy!</b>\n{DIVIDER}\n\n<code>@{username}</code>\n\n<i>Select and copy above.</i>", parse_mode=ParseMode.HTML)

    elif data.startswith("retry_"):
        username = data[6:]
        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        if status == AVAILABLE:
            text = f"{E['party']} <b>AVAILABLE!</b>\n{THICK_DIVIDER}\n  {E['user']} <code>@{username}</code>\n  {E['link']} <a href=\"https://t.me/{username}\">t.me/{username}</a>"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['link']} Open", url=f"https://t.me/{username}")],
                                        [InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")]])
        elif status == TAKEN:
            text = f"{E['taken']} <code>@{username}</code> is still taken."
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")]])
        else:
            text = f"{E['error']} Still having trouble with <code>@{username}</code>."
            kb = None
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "history":
        if not session.history:
            text = f"{E['history']} <b>History</b>\n{DIVIDER}\n\n  {E['no']} No checks yet."
        else:
            lines = []
            for ts, username, status in reversed(session.history[-15:]):
                lines.append(f"  {session.status_emoji(status)} <code>@{username}</code>  <i>{format_time_ago(ts)}</i>")
            text = f"{E['history']} <b>Recent Checks</b>\n{THICK_DIVIDER}\n\n" + "\n".join(lines)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['stats']} Stats", callback_data="stats"),
             InlineKeyboardButton(f"{E['export']} Export", callback_data="export_hits")],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "settings":
        text = (f"{E['settings']} <b>Settings</b>\n{THICK_DIVIDER}\n\n"
                f"  📏 <b>Length:</b> {session.username_length}\n  🔤 <b>Chars:</b> <code>{session.char_set_label}</code>\n"
                f"  {E['clock']} <b>Delay:</b> {session.delay}s\n  🧵 <b>Workers:</b> {session.max_workers}\n"
                f"  {E['gear']} <b>Gen Mode:</b> {session.generation_mode}\n")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📏 Length ({session.username_length})", callback_data="set_length"),
             InlineKeyboardButton(f"🔤 Chars", callback_data="set_chars")],
            [InlineKeyboardButton(f"{E['clock']} Delay ({session.delay}s)", callback_data="set_delay"),
             InlineKeyboardButton(f"🧵 Workers ({session.max_workers})", callback_data="set_workers")],
            [InlineKeyboardButton(f"{E['gear']} Gen Mode ({session.generation_mode})", callback_data="set_gen_mode"),
             InlineKeyboardButton(f"{E['crystal']} Pattern", callback_data="pattern_menu")],
            [InlineKeyboardButton(f"{E['refresh']} Reset All", callback_data="confirm_reset_settings"),
             InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "set_length":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{'👉 ' if i == session.username_length else ''}{i}", callback_data=f"len_{i}") for i in [5,6,7]],
                                    [InlineKeyboardButton(f"{'👉 ' if i == session.username_length else ''}{i}", callback_data=f"len_{i}") for i in [8,10,12]],
                                    [InlineKeyboardButton(f"{'👉 ' if i == session.username_length else ''}{i}", callback_data=f"len_{i}") for i in [15,20,25]],
                                    [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")]])
        await query.edit_message_text(f"📏 <b>Username Length</b>\n{DIVIDER}\nCurrent: <b>{session.username_length}</b>", parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data.startswith("len_"):
        session.username_length = int(data.split("_")[1])
        await query.edit_message_text(f"{E['yes']} Length set to <b>{session.username_length}</b>", parse_mode=ParseMode.HTML)

    elif data == "set_chars":
        current = session.char_set_label
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{'👉 ' if current=='a-z 0-9 _' else ''}a-z 0-9 _", callback_data="chars_default")],
                                    [InlineKeyboardButton(f"{'👉 ' if current=='a-z only' else ''}a-z only", callback_data="chars_alpha")],
                                    [InlineKeyboardButton(f"{'👉 ' if current=='a-z 0-9' else ''}a-z 0-9", callback_data="chars_alnum")],
                                    [InlineKeyboardButton(f"{'👉 ' if current=='0-9 only' else ''}0-9 only", callback_data="chars_digits")],
                                    [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")]])
        await query.edit_message_text(f"🔤 <b>Character Set</b>\n{DIVIDER}\nCurrent: <code>{current}</code>", parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data.startswith("chars_"):
        sets = {"chars_default":"abcdefghijklmnopqrstuvwxyz0123456789_","chars_alpha":"abcdefghijklmnopqrstuvwxyz","chars_alnum":"abcdefghijklmnopqrstuvwxyz0123456789","chars_digits":"0123456789"}
        session.char_set = sets.get(data, sets["chars_default"])
        await query.edit_message_text(f"{E['yes']} Chars: <code>{session.char_set}</code>", parse_mode=ParseMode.HTML)

    elif data == "set_delay":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{'👉 ' if d==session.delay else ''}{d}s", callback_data=f"delay_{d}") for d in [0.5,1.0,2.0]],
                                    [InlineKeyboardButton(f"{'👉 ' if d==session.delay else ''}{d}s", callback_data=f"delay_{d}") for d in [3.0,5.0]],
                                    [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")]])
        await query.edit_message_text(f"{E['clock']} <b>Delay</b>\n{DIVIDER}\nCurrent: <b>{session.delay}s</b>", parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data.startswith("delay_"):
        session.delay = float(data.split("_")[1])
        await query.edit_message_text(f"{E['yes']} Delay: <b>{session.delay}s</b>", parse_mode=ParseMode.HTML)

    elif data == "set_workers":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{'👉 ' if i==session.max_workers else ''}{i}", callback_data=f"workers_{i}") for i in [1,3,5]],
                                    [InlineKeyboardButton(f"{'👉 ' if i==session.max_workers else ''}{i}", callback_data=f"workers_{i}") for i in [10,20,50]],
                                    [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")]])
        await query.edit_message_text(f"🧵 <b>Workers</b>\n{DIVIDER}\nCurrent: <b>{session.max_workers}</b>", parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data.startswith("workers_"):
        session.max_workers = int(data.split("_")[1])
        await query.edit_message_text(f"{E['yes']} Workers: <b>{session.max_workers}</b>", parse_mode=ParseMode.HTML)

    elif data == "set_gen_mode":
        current = session.generation_mode
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{'👉 ' if current=='random' else ''}🎲 Random", callback_data="gen_random")],
                                    [InlineKeyboardButton(f"{'👉 ' if current=='word_combo' else ''}🧠 Word Combos", callback_data="gen_word_combo")],
                                    [InlineKeyboardButton(f"{'👉 ' if current=='mixed' else ''}🌈 Mixed", callback_data="gen_mixed")],
                                    [InlineKeyboardButton(f"{E['back']} Back", callback_data="settings")]])
        await query.edit_message_text(f"{E['gear']} <b>Generation Mode</b>\n{DIVIDER}\nCurrent: <b>{current}</b>\n\n  🎲 Random • 🧠 Word Combos • 🌈 Mixed", parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data.startswith("gen_"):
        session.generation_mode = data[4:]
        labels = {"random":"🎲 Random","word_combo":"🧠 Word Combos","mixed":"🌈 Mixed"}
        await query.edit_message_text(f"{E['yes']} Mode: <b>{labels.get(data[4:], data[4:])}</b>", parse_mode=ParseMode.HTML)

    elif data == "pattern_menu":
        text = f"{E['crystal']} <b>Pattern Templates</b>\n{THICK_DIVIDER}\n\n  <code>?</code>=letter <code>#</code>=digit <code>!</code>=alnum\n\n<b>Quick Templates:</b>"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("user_????", callback_data="pattern_tpl_user_????")],
            [InlineKeyboardButton("name_##_ab", callback_data="pattern_tpl_name_##_ab")],
            [InlineKeyboardButton("pro_####", callback_data="pattern_tpl_pro_####")],
            [InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data.startswith("pattern_tpl_"):
        pattern = data[len("pattern_tpl_"):]
        session.pattern = pattern
        await _run_pattern_cb(query, session, 20, pattern)

    elif data.startswith("pattern_more_"):
        pattern = data[len("pattern_more_"):]
        session.pattern = pattern
        await _run_pattern_cb(query, session, 20, pattern)

    elif data == "confirm_reset_settings":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['yes']} Yes", callback_data="reset_settings"),
                                     InlineKeyboardButton(f"{E['no']} Cancel", callback_data="settings")]])
        await query.edit_message_text(f"{E['stop']} <b>Reset all settings?</b>\n{DIVIDER}\nDefaults: length=5, chars=a-z 0-9 _, delay=1s, workers=5", parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "reset_settings":
        session.username_length = 5; session.char_set = "abcdefghijklmnopqrstuvwxyz0123456789_"
        session.delay = 1.0; session.max_workers = 5; session.generation_mode = "random"; session.pattern = ""
        await query.edit_message_text(f"{E['yes']} <b>Settings reset!</b>", parse_mode=ParseMode.HTML)

    elif data == "confirm_reset_stats":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['yes']} Yes", callback_data="reset_stats"),
                                     InlineKeyboardButton(f"{E['no']} Cancel", callback_data="stats")]])
        await query.edit_message_text(f"{E['stop']} <b>Reset statistics?</b>\n{DIVIDER}\n{session.checked} checked, {session.hits} hits will be cleared.", parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "reset_stats":
        session.reset_stats(); session.history.clear()
        await query.edit_message_text(f"{E['yes']} <b>Stats reset!</b>", parse_mode=ParseMode.HTML)

    elif data == "export_hits":
        if session.available:
            hit_list = "\n".join(f"@{u}" for u in session.available)
            await query.edit_message_text(f"{E['export']} <b>Available Usernames ({len(session.available)})</b>\n{THICK_DIVIDER}\n\n<code>{hit_list}</code>\n\n<i>Copy above!</i>", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(f"{E['no']} No hits yet. Run /check or /generate first.", parse_mode=ParseMode.HTML)

    elif data == "stats":
        hit_bar = progress_bar(session.hits, max(session.checked, 1), 12)
        text = (f"{E['stats']} <b>Statistics</b>\n{THICK_DIVIDER}\n\n"
                f"  {E['magnifier']} Checked: <b>{session.checked}</b>\n  {E['hit']} Available: <b>{session.hits}</b>\n"
                f"  {E['taken']} Taken: <b>{session.taken}</b>\n  {E['invalid']} Invalid: <b>{session.invalid}</b>\n"
                f"  {E['rate']} Rate Limit: <b>{session.rate_limited}</b>\n  {E['error']} Errors: <b>{session.errors}</b>\n\n"
                f"  {E['target']} <b>Hit Rate:</b>\n    <code>{hit_bar}</code> {session.hit_rate:.1f}%\n")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{E['export']} Export", callback_data="export_hits"),
             InlineKeyboardButton(f"{E['history']} History", callback_data="history")],
            [InlineKeyboardButton(f"{E['refresh']} Reset", callback_data="confirm_reset_stats"),
             InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "help":
        text = (f"{E['bulb']} <b>Quick Help</b>\n{THICK_DIVIDER}\n\n"
                f"  {E['check']} <b>/check username</b> — Check one\n  {E['pack']} <b>/batch a,b,c</b> — Check multiple\n"
                f"  {E['magic']} <b>/generate [N]</b> — Random\n  {E['crystal']} <b>/pattern tmpl</b> — Patterns\n"
                f"  {E['settings']} <b>/settings</b> — Configure\n  {E['stats']} <b>/stats</b> — Stats\n"
                f"  {E['history']} <b>/history</b> — History\n  {E['ping']} <b>/ping</b> — Status\n"
                f"  {E['stop']} <b>/stop</b> — Stop\n\n  {E['sparkle']} Just type a username!\n\n"
                f"{E['pin']} Rules: 5–32 chars, a-z/0-9/_, starts with letter")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['back']} Back", callback_data="back_start")]])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _run_pattern_cb(query, session, count, pattern):
    session.running = True; session.should_stop = False
    gen = UsernameGenerator(length=session.username_length, chars=session.char_set)
    gen_stream = gen.pattern_stream(pattern)
    bar = progress_bar(0, count)
    await query.edit_message_text(f"{E['crystal']} <b>Pattern</b>\n{THICK_DIVIDER}\n\n  {E['pin']} <code>{pattern}</code>\n\n<code>{bar}</code> 0/{count}\n\n<i>Generating...</i>", parse_mode=ParseMode.HTML)
    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}
    start_time = time.time()
    for i in range(count):
        if session.should_stop: break
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
                    f"{E['crystal']} <b>Pattern</b>\n{THICK_DIVIDER}\n\n  {E['pin']} <code>{pattern}</code>\n\n"
                    f"<code>{bar}</code> {i+1}/{count} ({pct(i+1, count)})\n\n"
                    f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n  {E['taken']} Taken: {len(results[TAKEN])}\n"
                    f"  {E['zap']} Speed: {speed:.1f}/sec\n\n<i>Checking...</i>",
                    parse_mode=ParseMode.HTML)
            except: pass
    session.running = False; elapsed = time.time() - start_time
    hit_list = "\n".join(f"    {E['hit']} <code>@{u}</code>" for u in results[AVAILABLE]) or f"    {E['no']} <i>None found</i>"
    bar = progress_bar(count, count)
    text = (f"{E['trophy']} <b>Pattern Complete</b>\n{THICK_DIVIDER}\n\n  {E['pin']} <code>{pattern}</code>\n\n"
            f"<code>{bar}</code> {count}/{count} (100%)\n\n"
            f"  {E['hit']} Available: <b>{len(results[AVAILABLE])}</b>\n  {E['taken']} Taken: {len(results[TAKEN])}\n"
            f"  {E['time']} Time: {format_uptime(elapsed)}\n\n  {E['target']} <b>Available:</b>\n{hit_list}")
    buttons = []
    if results[AVAILABLE]:
        buttons.append([InlineKeyboardButton(f"{E['export']} Export Hits", callback_data="export_hits")])
    buttons.append([InlineKeyboardButton(f"{E['crystal']} More", callback_data=f"pattern_more_{pattern}"),
                    InlineKeyboardButton(f"{E['check']} Check Another", switch_inline_query_current_chat="")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


# ============================================================================
# MESSAGE HANDLER
# ============================================================================

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lstrip("@").lower()
    if len(text) < 5 or len(text) > 32: return
    if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in text): return
    if not text[0].isalpha(): return
    if not is_valid_username(text):
        await update.message.reply_text(f"{E['invalid']} <code>@{text}</code> is not valid.", parse_mode=ParseMode.HTML)
        return
    session = get_session(update.effective_user.id)
    msg = await update.message.reply_text(f"{E['clock']} <b>Checking</b> <code>@{text}</code>...", parse_mode=ParseMode.HTML)
    status, _ = await asyncio.to_thread(client.check, text, session.delay)
    session.record(status, text)
    if status == AVAILABLE:
        result = f"{E['party']} <b>AVAILABLE!</b>\n{DIVIDER}\n  {E['user']} <code>@{text}</code>\n  {E['link']} <a href=\"https://t.me/{text}\">t.me/{text}</a>\n\n  {E['chart']} {session.checked} checked  {E['diamond']} {session.hits} hits"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['link']} Open", url=f"https://t.me/{text}")],
                                    [InlineKeyboardButton(f"{E['check']} Another", switch_inline_query_current_chat=""),
                                     InlineKeyboardButton(f"{E['copy']} Copy", callback_data=f"copy_{text}")]])
    elif status == TAKEN:
        result = f"{E['taken']} <code>@{text}</code> is taken.\n\n{E['bulb']} Try /generate!"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['check']} Another", switch_inline_query_current_chat=""),
                                     InlineKeyboardButton(f"{E['magic']} Generate", callback_data="quick_generate")]])
    elif status == RATE_LIMITED:
        result = f"{E['rate']} Rate limited. Try later."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['settings']} Settings", callback_data="settings")]])
    else:
        result = f"{E['error']} Error checking <code>@{text}</code>."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"{E['refresh']} Retry", callback_data=f"retry_{text}")]])
    await msg.edit_text(result, parse_mode=ParseMode.HTML, reply_markup=kb)


# ============================================================================
# BOT RUNNER
# ============================================================================

def run_bot(token: str):
    """Initialize and run the Telegram bot. Works in both CLI and Jupyter/Colab."""
    global client
    client = TelegramUsernameClient(user_agents=[
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ])
    app = Application.builder().token(token).build()
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
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"🤖 {BOT_USERNAME} v{VERSION} is running...")
    print("Press Ctrl+C to stop.")

    # Detect Jupyter/Colab and use async approach
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__name__
        is_notebook = shell in ("ZMQInteractiveShell", "Shell")
    except (ImportError, NameError, AttributeError):
        is_notebook = False

    if not is_notebook:
        # Normal CLI — use run_polling (blocking, works fine)
        app.run_polling(drop_pending_updates=True)
    else:
        # Jupyter/Colab — use nest_asyncio + run_polling
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass
        app.run_polling(drop_pending_updates=True)
