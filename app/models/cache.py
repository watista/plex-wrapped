from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings


class WrappedCache:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.path = self.settings.resolve_path(self.settings.database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wrapped_cache (
                    user_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, year)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS share_links (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    view_count INTEGER DEFAULT 0,
                    max_views INTEGER
                )
                """
            )
            conn.commit()

    def get(self, user_id: int, year: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM wrapped_cache WHERE user_id = ? AND year = ?",
                (user_id, year),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def set(self, user_id: int, year: int, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO wrapped_cache (user_id, year, payload_json, computed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, year) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    computed_at = excluded.computed_at
                """,
                (user_id, year, json.dumps(payload), now),
            )
            conn.commit()

    def record_share_link(
        self,
        token_hash: str,
        user_id: int,
        year: int,
        expires_at: datetime,
        max_views: int | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO share_links
                (token_hash, user_id, year, created_at, expires_at, view_count, max_views)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (token_hash, user_id, year, now, expires_at.isoformat(), max_views),
            )
            conn.commit()

    def get_share_link(self, token_hash: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM share_links WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()

    def increment_share_views(self, token_hash: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE share_links SET view_count = view_count + 1 WHERE token_hash = ?",
                (token_hash,),
            )
            conn.commit()
