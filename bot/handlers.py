"""
Telegram Bot — interactive Telegram username checker.

Commands:
    /start          — Welcome message
    /help           — Show help
    /check <name>   — Check a single username
    /batch <names>  — Check multiple usernames (comma-separated)
    /generate       — Generate & check random usernames
    /settings       — View/change settings
    /stats          — Show session statistics
    /stop           — Stop current batch/generation
"""

import asyncio
import random
import string
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

from checker.telegram_client import TelegramUsernameClient, AVAILABLE, TAKEN, INVALID, RATE_LIMITED, ERROR, is_valid_username
from checker.proxy import ProxyManager
from checker.generator import UsernameGenerator


# ── Emoji Map ──
EMOJI = {
    "check": "🔍",
    "hit": "✅",
    "taken": "❌",
    "invalid": "🚫",
    "rate": "⚠️",
    "error": "💥",
    "stats": "📊",
    "settings": "⚙️",
    "stop": "🛑",
    "start": "🚀",
    "user": "👤",
    "id": "🆔",
    "pack": "📦",
    "clock": "🕐",
    "fire": "🔥",
    "star": "⭐",
    "back": "🔙",
    "yes": "✅",
    "no": "❌",
    "telegram": "📱",
}


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
        self.mode = "single"  # single, batch, generate

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
    """Handle /start."""
    user = update.effective_user
    text = (
        f"{EMOJI['telegram']} <b>TelegramUserCheckBot v1.0</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['user']} <b>User:</b> <code>{user.first_name}</code>\n"
        f"{EMOJI['id']} <b>UID:</b> <code>{user.id}</code>\n\n"
        f"{EMOJI['check']} <b>Check Telegram username availability instantly!</b>\n\n"
        f"<b>Commands:</b>\n"
        f"  /check username — Check one username\n"
        f"  /batch user1,user2,user3 — Check multiple\n"
        f"  /generate — Generate & check random names\n"
        f"  /settings — Configure checker\n"
        f"  /stats — Session statistics\n"
        f"  /stop — Stop current operation\n\n"
        f"<i>💡 Just type a username to quick-check!</i>"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{EMOJI['check']} Quick Check", switch_inline_query_current_chat=""),
            InlineKeyboardButton(f"{EMOJI['settings']} Settings", callback_data="settings"),
        ],
        [
            InlineKeyboardButton(f"{EMOJI['stats']} Stats", callback_data="stats"),
            InlineKeyboardButton("📖 Help", callback_data="help"),
        ],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /help."""
    text = (
        f"📖 <b>TelegramUserCheckBot Help</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>🔹 /check username</b>\n"
        f"Check if a single Telegram username is available.\n"
        f"<i>Example:</i> <code>/check coolname123</code>\n\n"
        f"<b>🔹 /batch user1,user2,user3</b>\n"
        f"Check multiple usernames at once (comma-separated).\n"
        f"<i>Example:</i> <code>/batch abc,xyz,test123</code>\n\n"
        f"<b>🔹 /generate</b>\n"
        f"Generate random usernames and check availability.\n"
        f"Uses your configured length and character set.\n\n"
        f"<b>🔹 /settings</b>\n"
        f"View and change: username length, char set, delay.\n\n"
        f"<b>🔹 /stats</b>\n"
        f"Show checked count, hits, taken, errors.\n\n"
        f"<b>🔹 /stop</b>\n"
        f"Stop any running batch or generation.\n\n"
        f"<b>📌 Telegram Username Rules:</b>\n"
        f"  • 5-32 characters\n"
        f"  • a-z, 0-9, underscores only\n"
        f"  • Must start with a letter\n"
        f"  • No double underscores\n"
        f"  • Can't end with underscore\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Made with ❤️ by @Shineii86</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /check <username>."""
    if not ctx.args:
        await update.message.reply_text(
            f"{EMOJI['error']} Usage: <code>/check username</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    username = ctx.args[0].strip().lower().lstrip("@")
    if not username:
        await update.message.reply_text(f"{EMOJI['error']} Provide a username.")
        return

    # Validate format
    if not is_valid_username(username):
        await update.message.reply_text(
            f"{EMOJI['invalid']} <b>Invalid Username</b>\n\n"
            f"<code>@{username}</code> doesn't follow Telegram's rules:\n"
            f"• 5-32 characters\n"
            f"• Must start with a letter\n"
            f"• Only a-z, 0-9, underscores\n"
            f"• No double underscores\n"
            f"• Can't end with underscore",
            parse_mode=ParseMode.HTML,
        )
        return

    session = get_session(update.effective_user.id)
    msg = await update.message.reply_text(
        f"{EMOJI['clock']} Checking <code>@{username}</code>...",
        parse_mode=ParseMode.HTML,
    )

    status, _ = await asyncio.to_thread(client.check, username, session.delay)
    session.record(status, username)

    if status == AVAILABLE:
        text = (
            f"{EMOJI['hit']} <b>AVAILABLE!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{EMOJI['user']} <b>Username:</b> <code>@{username}</code>\n"
            f"{EMOJI['telegram']} <b>Link:</b> https://t.me/{username}\n"
            f"{EMOJI['hit']} <b>Status:</b> Available ✨\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{EMOJI['stats']} <b>Total checked:</b> {session.checked}\n"
            f"{EMOJI['hit']} <b>Total hits:</b> {session.hits}"
        )
    elif status == TAKEN:
        text = (
            f"{EMOJI['taken']} <b>Taken</b>\n"
            f"{EMOJI['user']} <code>@{username}</code> is already registered."
        )
    elif status == INVALID:
        text = (
            f"{EMOJI['invalid']} <b>Invalid</b>\n"
            f"<code>@{username}</code> is not a valid Telegram username."
        )
    elif status == RATE_LIMITED:
        text = (
            f"{EMOJI['rate']} <b>Rate Limited</b>\n"
            f"Too many requests. Try again later or use a proxy."
        )
    else:
        text = f"{EMOJI['error']} <b>Error</b> checking <code>@{username}</code>."

    await msg.edit_text(text, parse_mode=ParseMode.HTML)


async def cmd_batch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /batch user1,user2,user3."""
    if not ctx.args:
        await update.message.reply_text(
            f"{EMOJI['error']} Usage: <code>/batch user1,user2,user3</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = " ".join(ctx.args)
    usernames = [u.strip().lower().lstrip("@") for u in raw.split(",") if u.strip()]
    if not usernames:
        await update.message.reply_text(f"{EMOJI['error']} No usernames provided.")
        return

    session = get_session(update.effective_user.id)
    session.running = True
    session.should_stop = False

    msg = await update.message.reply_text(
        f"{EMOJI['start']} <b>Batch Check Started</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['pack']} <b>Usernames:</b> {len(usernames)}\n"
        f"{EMOJI['clock']} <b>Delay:</b> {session.delay}s\n\n"
        f"<i>Checking...</i>",
        parse_mode=ParseMode.HTML,
    )

    results = {AVAILABLE: [], TAKEN: [], INVALID: [], RATE_LIMITED: [], ERROR: []}

    for i, username in enumerate(usernames):
        if session.should_stop:
            break

        status, _ = await asyncio.to_thread(client.check, username, session.delay)
        session.record(status, username)
        results[status].append(username)

        # Update progress every 5 checks or on last
        if (i + 1) % 5 == 0 or i == len(usernames) - 1:
            try:
                await msg.edit_text(
                    f"{EMOJI['start']} <b>Batch Check Running</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{EMOJI['pack']} Progress: {i + 1}/{len(usernames)}\n"
                    f"{EMOJI['hit']} Hits: {len(results[AVAILABLE])}\n"
                    f"{EMOJI['taken']} Taken: {len(results[TAKEN])}\n"
                    f"{EMOJI['invalid']} Invalid: {len(results[INVALID])}\n"
                    f"{EMOJI['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n\n"
                    f"<i>Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False

    # Final report
    hit_list = "\n".join(f"  <code>@{u}</code>" for u in results[AVAILABLE]) or "  <i>None</i>"
    text = (
        f"{EMOJI['stats']} <b>Batch Check Complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['pack']} <b>Total:</b> {len(usernames)}\n"
        f"{EMOJI['hit']} <b>Available:</b> {len(results[AVAILABLE])}\n"
        f"{EMOJI['taken']} <b>Taken:</b> {len(results[TAKEN])}\n"
        f"{EMOJI['invalid']} <b>Invalid:</b> {len(results[INVALID])}\n"
        f"{EMOJI['rate']} <b>Rate Limited:</b> {len(results[RATE_LIMITED])}\n\n"
        f"{EMOJI['hit']} <b>Available Usernames:</b>\n{hit_list}"
    )

    if session.should_stop:
        text = f"{EMOJI['stop']} <b>Stopped!</b>\n\n" + text

    await msg.edit_text(text, parse_mode=ParseMode.HTML)


async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /generate — generate and check random usernames."""
    session = get_session(update.effective_user.id)
    count = 20  # default batch size for generation

    if ctx.args:
        try:
            count = int(ctx.args[0])
            count = min(count, 100)  # cap at 100
        except ValueError:
            pass

    session.running = True
    session.should_stop = False

    gen = UsernameGenerator(
        length=session.username_length,
        chars=session.char_set,
    )

    msg = await update.message.reply_text(
        f"{EMOJI['fire']} <b>Generating & Checking</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['pack']} <b>Count:</b> {count}\n"
        f"{EMOJI['settings']} <b>Length:</b> {session.username_length}\n"
        f"{EMOJI['clock']} <b>Delay:</b> {session.delay}s\n\n"
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

        if (i + 1) % 5 == 0 or i == count - 1:
            try:
                await msg.edit_text(
                    f"{EMOJI['fire']} <b>Generating & Checking</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{EMOJI['pack']} Progress: {i + 1}/{count}\n"
                    f"{EMOJI['hit']} Hits: {len(results[AVAILABLE])}\n"
                    f"{EMOJI['taken']} Taken: {len(results[TAKEN])}\n"
                    f"{EMOJI['invalid']} Invalid: {len(results[INVALID])}\n"
                    f"{EMOJI['rate']} Rate Limit: {len(results[RATE_LIMITED])}\n\n"
                    f"<i>Checking...</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    session.running = False

    hit_list = "\n".join(f"  <code>@{u}</code>" for u in results[AVAILABLE]) or "  <i>None</i>"
    text = (
        f"{EMOJI['stats']} <b>Generation Complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['pack']} <b>Checked:</b> {count}\n"
        f"{EMOJI['hit']} <b>Available:</b> {len(results[AVAILABLE])}\n"
        f"{EMOJI['taken']} <b>Taken:</b> {len(results[TAKEN])}\n"
        f"{EMOJI['invalid']} <b>Invalid:</b> {len(results[INVALID])}\n"
        f"{EMOJI['rate']} <b>Rate Limited:</b> {len(results[RATE_LIMITED])}\n\n"
        f"{EMOJI['hit']} <b>Available Usernames:</b>\n{hit_list}"
    )

    if session.should_stop:
        text = f"{EMOJI['stop']} <b>Stopped!</b>\n\n" + text

    await msg.edit_text(text, parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /stats."""
    session = get_session(update.effective_user.id)
    text = (
        f"{EMOJI['stats']} <b>Session Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['check']} <b>Checked:</b> {session.checked}\n"
        f"{EMOJI['hit']} <b>Available:</b> {session.hits}\n"
        f"{EMOJI['taken']} <b>Taken:</b> {session.taken}\n"
        f"{EMOJI['invalid']} <b>Invalid:</b> {session.invalid}\n"
        f"{EMOJI['rate']} <b>Rate Limited:</b> {session.rate_limited}\n"
        f"{EMOJI['error']} <b>Errors:</b> {session.errors}\n"
    )
    if session.available:
        hit_list = "\n".join(f"  <code>@{u}</code>" for u in session.available[-10:])
        text += f"\n{EMOJI['hit']} <b>Recent Hits:</b>\n{hit_list}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJI['stop']} Reset Stats", callback_data="reset_stats")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /stop."""
    session = get_session(update.effective_user.id)
    if session.running:
        session.should_stop = True
        await update.message.reply_text(
            f"{EMOJI['stop']} <b>Stopping...</b> Will finish current check shortly.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"{EMOJI['no']} Nothing is running.",
            parse_mode=ParseMode.HTML,
        )


async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /settings."""
    session = get_session(update.effective_user.id)
    await show_settings(update.message, session)


async def show_settings(message, session: UserSession):
    """Show settings menu with inline buttons."""
    text = (
        f"{EMOJI['settings']} <b>Settings</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📏 <b>Username Length:</b> {session.username_length}\n"
        f"🔤 <b>Character Set:</b> <code>{session.char_set}</code>\n"
        f"{EMOJI['clock']} <b>Delay:</b> {session.delay}s\n"
        f"🧵 <b>Workers:</b> {session.max_workers}\n"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📏 Length", callback_data="set_length"),
            InlineKeyboardButton("🔤 Chars", callback_data="set_chars"),
        ],
        [
            InlineKeyboardButton(f"{EMOJI['clock']} Delay", callback_data="set_delay"),
            InlineKeyboardButton("🧵 Workers", callback_data="set_workers"),
        ],
        [
            InlineKeyboardButton(f"{EMOJI['back']} Reset All", callback_data="reset_settings"),
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

    if data == "settings":
        text = (
            f"{EMOJI['settings']} <b>Settings</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📏 <b>Username Length:</b> {session.username_length}\n"
            f"🔤 <b>Character Set:</b> <code>{session.char_set}</code>\n"
            f"{EMOJI['clock']} <b>Delay:</b> {session.delay}s\n"
            f"🧵 <b>Workers:</b> {session.max_workers}\n"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📏 Length", callback_data="set_length"),
                InlineKeyboardButton("🔤 Chars", callback_data="set_chars"),
            ],
            [
                InlineKeyboardButton(f"{EMOJI['clock']} Delay", callback_data="set_delay"),
                InlineKeyboardButton("🧵 Workers", callback_data="set_workers"),
            ],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "set_length":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(str(i), callback_data=f"len_{i}") for i in range(5, 13)],
            [InlineKeyboardButton(f"{EMOJI['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"📏 <b>Choose Username Length</b>\n"
            f"<i>Telegram allows 5-32 characters</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("len_"):
        session.username_length = int(data.split("_")[1])
        await query.edit_message_text(
            f"{EMOJI['yes']} Length set to <b>{session.username_length}</b>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "set_chars":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("a-z 0-9 _", callback_data="chars_default")],
            [InlineKeyboardButton("a-z only", callback_data="chars_alpha")],
            [InlineKeyboardButton("a-z 0-9", callback_data="chars_alnum")],
            [InlineKeyboardButton("0-9 only", callback_data="chars_digits")],
            [InlineKeyboardButton(f"{EMOJI['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"🔤 <b>Choose Character Set:</b>",
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
            f"{EMOJI['yes']} Character set updated:\n<code>{session.char_set}</code>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "set_delay":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{d}s", callback_data=f"delay_{d}") for d in [0.5, 1.0, 2.0, 3.0]],
            [InlineKeyboardButton(f"{EMOJI['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"{EMOJI['clock']} <b>Choose Delay:</b>\n"
            f"<i>Higher delay = safer from rate limits</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("delay_"):
        session.delay = float(data.split("_")[1])
        await query.edit_message_text(
            f"{EMOJI['yes']} Delay set to <b>{session.delay}s</b>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "set_workers":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(str(i), callback_data=f"workers_{i}") for i in [1, 3, 5, 10]],
            [InlineKeyboardButton(f"{EMOJI['back']} Back", callback_data="settings")],
        ])
        await query.edit_message_text(
            f"🧵 <b>Choose Worker Count:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    elif data.startswith("workers_"):
        session.max_workers = int(data.split("_")[1])
        await query.edit_message_text(
            f"{EMOJI['yes']} Workers set to <b>{session.max_workers}</b>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "reset_settings":
        session.username_length = 5
        session.char_set = "abcdefghijklmnopqrstuvwxyz0123456789_"
        session.delay = 1.0
        session.max_workers = 5
        await query.edit_message_text(
            f"{EMOJI['yes']} <b>All settings reset to defaults.</b>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "stats":
        text = (
            f"{EMOJI['stats']} <b>Session Statistics</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{EMOJI['check']} <b>Checked:</b> {session.checked}\n"
            f"{EMOJI['hit']} <b>Available:</b> {session.hits}\n"
            f"{EMOJI['taken']} <b>Taken:</b> {session.taken}\n"
            f"{EMOJI['invalid']} <b>Invalid:</b> {session.invalid}\n"
            f"{EMOJI['rate']} <b>Rate Limited:</b> {session.rate_limited}\n"
            f"{EMOJI['error']} <b>Errors:</b> {session.errors}\n"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{EMOJI['stop']} Reset Stats", callback_data="reset_stats")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "reset_stats":
        session.reset_stats()
        await query.edit_message_text(
            f"{EMOJI['yes']} <b>Stats reset.</b>",
            parse_mode=ParseMode.HTML,
        )

    elif data == "help":
        text = (
            f"📖 <b>Quick Help</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"/check username — Check one\n"
            f"/batch a,b,c — Check multiple\n"
            f"/generate — Random check\n"
            f"/settings — Configure\n"
            f"/stats — View stats\n"
            f"/stop — Stop operation\n\n"
            f"<i>💡 Just type a username to quick-check!</i>"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)


# ============================================================================
# MESSAGE HANDLER (Quick check by just typing a username)
# ============================================================================

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages as quick username checks."""
    text = update.message.text.strip().lstrip("@").lower()

    # Only check if it looks like a username (alphanumeric + underscore, 5+ chars)
    if len(text) < 5 or len(text) > 32:
        return
    if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in text):
        return
    if not text[0].isalpha():
        return

    session = get_session(update.effective_user.id)

    if not is_valid_username(text):
        await update.message.reply_text(
            f"{EMOJI['invalid']} <code>@{text}</code> is not a valid Telegram username.",
            parse_mode=ParseMode.HTML,
        )
        return

    msg = await update.message.reply_text(
        f"{EMOJI['clock']} Checking <code>@{text}</code>...",
        parse_mode=ParseMode.HTML,
    )

    status, _ = await asyncio.to_thread(client.check, text, session.delay)
    session.record(status, text)

    if status == AVAILABLE:
        result = (
            f"{EMOJI['hit']} <b>AVAILABLE!</b>\n"
            f"{EMOJI['user']} <code>@{text}</code>\n"
            f"{EMOJI['telegram']} https://t.me/{text}\n"
            f"{EMOJI['stats']} Checked: {session.checked} | Hits: {session.hits}"
        )
    elif status == TAKEN:
        result = f"{EMOJI['taken']} <code>@{text}</code> is taken."
    elif status == INVALID:
        result = f"{EMOJI['invalid']} <code>@{text}</code> is invalid."
    elif status == RATE_LIMITED:
        result = f"{EMOJI['rate']} Rate limited. Try again later."
    else:
        result = f"{EMOJI['error']} Error checking <code>@{text}</code>."

    await msg.edit_text(result, parse_mode=ParseMode.HTML)


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

    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Message handler for quick checks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 TelegramUserCheckBot is running...")
    print("Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)
