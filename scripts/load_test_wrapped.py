#!/usr/bin/env python3
"""Load bundled test stats into the wrapped cache (no Tautulli required)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.fixtures.test_wrapped import load_test_payload
from app.models.cache import WrappedCache
from app.telegram.loader import load_user_mapping


def _resolve_user_ids(settings, explicit: int | None, all_mapped: bool) -> set[int]:
    if explicit is not None:
        return {explicit}

    if all_mapped:
        mapping = load_user_mapping(settings)
        return {
            int(entry["plex_user_id"])
            for entry in mapping.values()
            if entry.get("plex_user_id") is not None
        }

    print("Loading test data for user_id=1 (use --user-id or --all-mapped to override)")
    return {1}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load test wrapped stats into the SQLite cache for local UI testing"
    )
    parser.add_argument("--year", type=int, default=None, help="Wrapped year (default: WRAPPED_YEAR)")
    parser.add_argument("--user-id", type=int, default=None, help="Plex/Tautulli user id to store under")
    parser.add_argument(
        "--all-mapped",
        action="store_true",
        help="Load test data for every plex_user_id in user_mapping.json",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Path to fixture JSON (default: data/fixtures/wrapped_test.json)",
    )
    args = parser.parse_args()

    settings = get_settings()
    year = args.year or settings.wrapped_year
    cache = WrappedCache(settings)

    user_ids = _resolve_user_ids(settings, args.user_id, args.all_mapped)
    if args.all_mapped and not user_ids:
        print("No plex_user_id entries found in user_mapping.json")
        sys.exit(1)

    for uid in sorted(user_ids):
        payload = load_test_payload(
            user_id=uid,
            year=year,
            fixture_path=args.fixture,
            settings=settings,
        )
        cache.set(uid, year, payload.model_dump())
        print(
            f"Loaded test wrapped for user_id={uid} year={year} "
            f"({payload.display_name}, {payload.total_plays} plays)"
        )

    print(f"Done. Open /wrapped after signing in as one of: {sorted(user_ids)}")


if __name__ == "__main__":
    main()
