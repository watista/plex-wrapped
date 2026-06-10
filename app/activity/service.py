from __future__ import annotations

from typing import Any

from fastapi import Request

from app.activity.logger import ActivityLogger
from app.activity.schemas import ActivityEventBody
from app.activity.telegram import TelegramNotifier
from app.auth.plex_oauth import get_session_user_id, get_session_username
from app.config import Settings
from app.models.cache import WrappedCache


class ActivityService:
    def __init__(
        self,
        settings: Settings,
        cache: WrappedCache,
        *,
        logger: ActivityLogger | None = None,
        telegram: TelegramNotifier | None = None,
    ) -> None:
        self.settings = settings
        self.cache = cache
        self.logger = logger or ActivityLogger()
        self.telegram = telegram or TelegramNotifier(settings)

    def resolve_username(self, request: Request, user_id: int, year: int | None = None) -> str:
        username = get_session_username(request, self.settings)
        if username:
            return username

        lookup_year = year if year is not None else self.settings.wrapped_year
        cached = self.cache.get(user_id, lookup_year)
        if cached:
            return cached.get("username") or cached.get("display_name") or f"user_{user_id}"
        return f"user_{user_id}"

    def resolve_display_name(self, user_id: int, year: int | None = None) -> str | None:
        lookup_year = year if year is not None else self.settings.wrapped_year
        cached = self.cache.get(user_id, lookup_year)
        if not cached:
            return None
        return cached.get("display_name") or cached.get("username")

    def log_login(
        self,
        request: Request,
        *,
        user_id: int,
        username: str,
        login_method: str,
        year: int | None = None,
        notify_telegram: bool = True,
    ) -> None:
        lookup_year = year if year is not None else self.settings.wrapped_year
        display_name = self.resolve_display_name(user_id, lookup_year)
        client_host = request.client.host if request.client else None
        user_agent = (request.headers.get("user-agent") or "")[:200]

        self.logger.log(
            username,
            "login",
            method=login_method,
            user_id=user_id,
            year=lookup_year,
            client_host=client_host,
            user_agent=user_agent,
        )

        if notify_telegram:
            self.telegram.send_login_notification(
                username=username,
                display_name=display_name,
                login_method=login_method,
                year=lookup_year,
                user_id=user_id,
            )

    def record_client_event(
        self,
        request: Request,
        user_id: int,
        body: ActivityEventBody,
        *,
        year: int | None = None,
    ) -> None:
        username = self.resolve_username(request, user_id, year)
        lookup_year = year if year is not None else self.settings.wrapped_year
        fields: dict[str, Any] = {
            "user_id": user_id,
            "year": lookup_year,
            "slide_id": body.slide_id,
            "slide_index": body.slide_index,
            "slide_count": body.slide_count,
            "button": body.button,
            "duration_ms": body.duration_ms,
            "login_method": body.login_method,
        }
        if body.metadata:
            for key, value in body.metadata.items():
                if key not in fields and value is not None:
                    fields[key] = value

        self.logger.log(username, body.event, **fields)
