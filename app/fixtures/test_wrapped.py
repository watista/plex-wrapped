from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, Settings, get_settings
from app.models.schemas import WrappedPayload
from app.utils.json_io import load_json_dict

DEFAULT_FIXTURE = PROJECT_ROOT / "data" / "fixtures" / "wrapped_test.json"
FIXTURES_DIR = PROJECT_ROOT / "data" / "fixtures"


@dataclass(frozen=True)
class TestUserEntry:
    plex_user_id: int
    display_name: str
    fixture: Path


def default_fixture_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.resolve_path(settings.wrapped_test_fixture_path)


def test_users_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.resolve_path(settings.wrapped_test_users_path)


def load_test_user_entries(settings: Settings | None = None) -> list[TestUserEntry]:
    """Load the manifest of bundled test users (independent of user_mapping.json)."""
    settings = settings or get_settings()
    path = test_users_path(settings)
    data = load_json_dict(path)
    entries: list[TestUserEntry] = []
    for row in data.get("users", []):
        if not isinstance(row, dict):
            continue
        plex_user_id = row.get("plex_user_id")
        if plex_user_id is None:
            continue
        fixture_name = row.get("fixture", "wrapped_test.json")
        fixture = FIXTURES_DIR / fixture_name
        if not fixture.is_file():
            fixture = settings.resolve_path(str(fixture_name))
        entries.append(
            TestUserEntry(
                plex_user_id=int(plex_user_id),
                display_name=str(row.get("display_name") or f"User {plex_user_id} (test)"),
                fixture=fixture,
            )
        )
    return entries


def find_test_user(
    user_id: int,
    settings: Settings | None = None,
) -> TestUserEntry | None:
    for entry in load_test_user_entries(settings):
        if entry.plex_user_id == user_id:
            return entry
    return None


def load_test_payload(
    *,
    user_id: int,
    year: int | None = None,
    fixture_path: Path | None = None,
    settings: Settings | None = None,
    overrides: dict[str, Any] | None = None,
) -> WrappedPayload:
    """Load and validate a test wrapped payload for one user."""
    settings = settings or get_settings()
    entry = find_test_user(user_id, settings)
    path = fixture_path
    if path is None and entry is not None:
        path = entry.fixture
    if path is None:
        path = default_fixture_path(settings)
    if not path.is_file():
        raise FileNotFoundError(f"Test fixture not found: {path}")

    data = load_json_dict(path)
    data["user_id"] = user_id
    data["year"] = year if year is not None else settings.wrapped_year
    if entry is not None:
        data["display_name"] = entry.display_name
    if overrides:
        data.update(overrides)

    return WrappedPayload(**data)
