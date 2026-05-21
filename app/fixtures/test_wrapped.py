from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, Settings, get_settings
from app.models.schemas import WrappedPayload

DEFAULT_FIXTURE = PROJECT_ROOT / "data" / "fixtures" / "wrapped_test.json"


def default_fixture_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.resolve_path(settings.wrapped_test_fixture_path)


def load_test_payload(
    *,
    user_id: int,
    year: int | None = None,
    fixture_path: Path | None = None,
    settings: Settings | None = None,
    overrides: dict[str, Any] | None = None,
) -> WrappedPayload:
    """Load and validate the bundled test wrapped payload."""
    settings = settings or get_settings()
    path = fixture_path or default_fixture_path(settings)
    if not path.is_file():
        raise FileNotFoundError(f"Test fixture not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    data["user_id"] = user_id
    data["year"] = year if year is not None else settings.wrapped_year
    if overrides:
        data.update(overrides)

    return WrappedPayload(**data)
