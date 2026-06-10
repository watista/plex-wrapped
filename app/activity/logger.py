from __future__ import annotations

import logging
from typing import Any


class ActivityLogger:
    """Structured activity logs tagged by Plex username."""

    def __init__(self, name: str = "plex.wrapped.activity") -> None:
        self._logger = logging.getLogger(name)

    def log(self, username: str, event: str, **fields: Any) -> None:
        user = (username or "unknown").strip() or "unknown"
        parts = [f"event={event}"]
        for key, value in fields.items():
            if value is None:
                continue
            parts.append(f"{key}={value}")
        self._logger.info("user=%s | %s", user, " ".join(parts))
