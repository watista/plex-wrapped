#!/usr/bin/env python3
"""Load bundled test stats into the dedicated test SQLite database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.fixtures.test_wrapped import find_test_user, load_test_payload, load_test_user_entries
from app.models.cache import WrappedCache


def _resolve_entries(settings, user_id: int | None, all_test_users: bool):
    if all_test_users:
        entries = load_test_user_entries(settings)
        if not entries:
            print("No users in data/fixtures/test_users.json")
            sys.exit(1)
        return entries

    if user_id is not None:
        entry = find_test_user(user_id, settings)
        fixture = entry.fixture if entry else None
        display_name = entry.display_name if entry else f"User {user_id} (test)"
        from app.fixtures.test_wrapped import TestUserEntry

        return [
            TestUserEntry(
                plex_user_id=user_id,
                display_name=display_name,
                fixture=fixture or settings.resolve_path(settings.wrapped_test_fixture_path),
            )
        ]

    print("Loading test data for user_id=1 (use --user-id or --all-test-users)")
    entry = find_test_user(1, settings)
    if entry:
        return [entry]
    from app.fixtures.test_wrapped import TestUserEntry

    return [
        TestUserEntry(
            plex_user_id=1,
            display_name="Alex (test)",
            fixture=settings.resolve_path(settings.wrapped_test_fixture_path),
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load test wrapped stats into data/wrapped_test.db (separate from production)"
    )
    parser.add_argument("--year", type=int, default=None, help="Wrapped year (default: WRAPPED_YEAR)")
    parser.add_argument("--user-id", type=int, default=None, help="Plex/Tautulli user id to store under")
    parser.add_argument(
        "--all-test-users",
        action="store_true",
        help="Load every user listed in data/fixtures/test_users.json",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Override fixture JSON for a single --user-id load",
    )
    args = parser.parse_args()

    settings = get_settings()
    year = args.year or settings.wrapped_year
    db = WrappedCache(settings, database_path=settings.test_database_path)

    entries = _resolve_entries(settings, args.user_id, args.all_test_users)

    for entry in entries:
        payload = load_test_payload(
            user_id=entry.plex_user_id,
            year=year,
            fixture_path=args.fixture or entry.fixture,
            settings=settings,
        )
        db.set(entry.plex_user_id, year, payload.model_dump())
        print(
            f"Wrote user_id={entry.plex_user_id} year={year} "
            f"({payload.display_name}, {payload.total_plays} plays)"
        )

    user_ids = sorted(e.plex_user_id for e in entries)
    print(f"Database: {db.path}")
    print("Enable test mode in .env: USE_TEST_DATABASE=true")
    print(f"Then open /wrapped as one of: {user_ids}")


if __name__ == "__main__":
    main()
