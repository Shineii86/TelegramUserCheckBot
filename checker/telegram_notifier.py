"""
Telegram Notifications — send rich alerts for hits and status updates.
Supports inline buttons for interactive notifications.
"""

import requests
from typing import Optional, List, Dict


class TelegramNotifier:
    """Send messages to a Telegram chat via Bot API."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)
        self._api_base = f"https://api.telegram.org/bot{token}"

    def _post(self, method: str, data: dict, timeout: int = 10) -> Optional[dict]:
        """Make a Bot API call. Returns response JSON or None on failure."""
        if not self.enabled:
            return None
        url = f"{self._api_base}/{method}"
        try:
            resp = requests.post(url, json=data, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def send(
        self,
        text: str,
        parse_mode: str = "HTML",
        buttons: Optional[List[List[Dict[str, str]]]] = None,
        disable_preview: bool = True,
    ) -> bool:
        """Send a message with optional inline buttons."""
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }
        if buttons:
            data["reply_markup"] = {"inline_keyboard": buttons}
        result = self._post("sendMessage", data)
        return result is not None

    def send_hit(self, hit_num: int, username: str, checked: int) -> bool:
        """Send a rich 'available username found' notification with action buttons."""
        msg = (
            f"🎉 <b>Username Available!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"  🔥 <b>Hit #{hit_num}</b>\n"
            f"  👤 <b>Username:</b> <code>@{username}</code>\n"
            f"  🔗 <b>Link:</b> <a href=\"https://t.me/{username}\">t.me/{username}</a>\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  📊 Checked so far: <b>{checked}</b>\n"
            f"\n"
            f"🚀 <i>Claim it before someone else does!</i>"
        )
        buttons = [
            [
                {"text": "📱 Open in Telegram", "url": f"https://t.me/{username}"},
                {"text": "📋 Copy Name", "callback_data": f"c:{username}"},
            ],
            [
                {"text": "📊 Stats", "callback_data": "st"},
                {"text": "🛑 Stop", "callback_data": "x"},
            ],
        ]
        return self.send(msg, buttons=buttons)

    def send_start(self) -> bool:
        """Send a 'bot started' notification."""
        msg = (
            f"🤖 <b>TelegramUserCheckBot Started</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"  ⚡ Ready to check usernames\n"
            f"  📊 Use /stats to view progress\n"
            f"  🛑 Use /stop to halt anytime\n"
            f"\n"
            f"<i>Checking usernames...</i>"
        )
        return self.send(msg)

    def send_finish(self, checked: int, hits: int) -> bool:
        """Send a 'bot finished' notification with summary."""
        hit_rate = (hits / checked * 100) if checked > 0 else 0
        msg = (
            f"✅ <b>Check Complete!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"  📊 <b>Checked:</b> {checked}\n"
            f"  ✅ <b>Available:</b> {hits}\n"
            f"  🎯 <b>Hit Rate:</b> {hit_rate:.1f}%\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Use /stats for detailed breakdown.</i>"
        )
        buttons = [
            [
                {"text": "📊 Stats", "callback_data": "st"},
                {"text": "📤 Export Hits", "callback_data": "export_hits"},
            ],
        ]
        return self.send(msg, buttons=buttons)

    def send_error(self, error: str) -> bool:
        """Send an error notification."""
        msg = (
            f"⚠️ <b>Error</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"  {error}\n"
            f"\n"
            f"<i>Check your config and try again.</i>"
        )
        return self.send(msg)

    def send_progress(self, checked: int, hits: int, total: Optional[int] = None) -> bool:
        """Send a progress update notification."""
        if total:
            pct = int(100 * checked / total) if total > 0 else 0
            bar_len = 10
            filled = int(bar_len * checked / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            msg = (
                f"📊 <b>Progress Update</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"\n"
                f"  <code>{bar}</code> {pct}%\n"
                f"  📊 Checked: {checked}/{total}\n"
                f"  ✅ Hits: {hits}\n"
            )
        else:
            msg = (
                f"📊 <b>Progress Update</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"\n"
                f"  📊 Checked: {checked}\n"
                f"  ✅ Hits: {hits}\n"
            )
        return self.send(msg)

    def send_rate_limit(self, wait_seconds: float) -> bool:
        """Send a rate limit warning."""
        msg = (
            f"⚠️ <b>Rate Limited</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"  Too many requests.\n"
            f"  ⏳ Waiting {wait_seconds:.0f}s before retry...\n"
            f"\n"
            f"<i>Consider using proxies for faster checking.</i>"
        )
        return self.send(msg)
