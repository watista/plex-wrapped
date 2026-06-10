from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActivityEventBody(BaseModel):
    event: str
    slide_id: str | None = None
    slide_index: int | None = None
    slide_count: int | None = None
    button: str | None = None
    duration_ms: int | None = None
    login_method: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
