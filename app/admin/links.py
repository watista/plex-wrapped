from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import Settings, get_settings
from app.models.cache import WrappedCache


class ShareLinkManager:
    def __init__(self, settings: Settings | None = None, cache: WrappedCache | None = None):
        self.settings = settings or get_settings()
        self.cache = cache or WrappedCache(self.settings)
        self._serializer = URLSafeTimedSerializer(
            self.settings.share_link_secret or self.settings.secret_key,
            salt="plex-wrapped-share",
        )

    def create_link(self, user_id: int, year: int | None = None, max_views: int | None = None) -> str:
        year = year or self.settings.wrapped_year
        token = self._serializer.dumps({"user_id": user_id, "year": year})
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(days=self.settings.share_link_expiry_days)
        self.cache.record_share_link(token_hash, user_id, year, expires, max_views)
        return f"{self.settings.public_url.rstrip('/')}/w/{token}"

    def validate_token(self, token: str) -> tuple[int, int] | None:
        max_age = self.settings.share_link_expiry_days * 86400
        try:
            data = self._serializer.loads(token, max_age=max_age)
            user_id = int(data["user_id"])
            year = int(data["year"])
        except (BadSignature, KeyError, TypeError, ValueError):
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        row = self.cache.get_share_link(token_hash)
        if row:
            expires = datetime.fromisoformat(row["expires_at"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                return None
            max_views = row["max_views"]
            if max_views is not None and row["view_count"] >= max_views:
                return None
            self.cache.increment_share_views(token_hash)

        return user_id, year
