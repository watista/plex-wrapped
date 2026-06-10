from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._token = (settings.telegram_bot_token or "").strip()
        self._chat_id = (settings.telegram_channel_id or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._chat_id)

    def send_login_notification(
        self,
        *,
        username: str,
        display_name: str | None = None,
        login_method: str,
        year: int | None = None,
        user_id: int | None = None,
    ) -> None:
        if not self.enabled:
            logger.debug("Telegram notifier disabled (missing bot token or channel id)")
            return

        name = display_name or username
        method_label = "Share link" if login_method == "share_link" else "Login portal"
        lines = [
            "ℹ️ <b>Plex Wrapped login</b> ℹ️",
            f"User: <code>{_escape_html(username)}</code>",
            f"Name: {_escape_html(name)}",
            f"Method: {method_label}",
        ]

        self._send_message("\n".join(lines))

    def _send_message(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                if response.status_code >= 400:
                    logger.warning(
                        "Telegram notification failed: status=%s body=%s",
                        response.status_code,
                        response.text[:300],
                    )
        except Exception as exc:
            logger.warning("Telegram notification error: %s", exc)


def _escape_html(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
