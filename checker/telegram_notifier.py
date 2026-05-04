"""
Telegram Notifications — send alerts for hits and status updates.
"""

import requests


class TelegramNotifier:
    """Send messages to a Telegram chat via Bot API."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    def send(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message. Returns True on success."""
        if not self.enabled:
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}
        try:
            resp = requests.post(url, json=data, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def send_hit(self, hit_num: int, username: str, checked: int) -> bool:
        """Send an 'available username found' notification."""
        msg = (
            f"✅ <b>Telegram Username Available</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔥 Hit #{hit_num}\n"
            f"👤 Username: @{username}\n"
            f"✅ Status: Available 👍\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Checked so far: {checked}"
        )
        return self.send(msg)

    def send_start(self) -> bool:
        """Send a 'bot started' notification."""
        return self.send("🤖 TelegramUserCheckBot started. Checking usernames...")

    def send_finish(self, checked: int, hits: int) -> bool:
        """Send a 'bot finished' notification."""
        return self.send(
            f"✅ TelegramUserCheckBot finished.\n"
            f"Checked: {checked}\n"
            f"Available: {hits}"
        )

    def send_error(self, error: str) -> bool:
        """Send an error notification."""
        return self.send(f"⚠️ <b>Error:</b> {error}")
