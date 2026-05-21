#!/usr/bin/env python3
"""Pre-compute wrapped stats for all mapped users."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.models.cache import WrappedCache
from app.tautulli.client import TautulliClient
from app.telegram.loader import load_telegram_data, load_user_mapping
from app.wrapped.aggregator import WrappedAggregator


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-compute Plex Wrapped cache")
    parser.add_argument("--year", type=int, default=None, help="Wrapped year (default: WRAPPED_YEAR)")
    parser.add_argument("--force", action="store_true", help="Recompute even if cached")
    parser.add_argument("--user-id", type=int, default=None, help="Single user id only")
    args = parser.parse_args()

    settings = get_settings()
    year = args.year or settings.wrapped_year

    tautulli = TautulliClient(settings)
    cache = WrappedCache(settings, database_path=settings.database_path)
    telegram = load_telegram_data(settings, year)
    mapping = load_user_mapping(settings)

    user_ids: set[int] = set()
    for entry in mapping.values():
        if entry.get("plex_user_id") is not None:
            user_ids.add(int(entry["plex_user_id"]))

    if args.user_id:
        user_ids = {args.user_id}

    if not user_ids:
        print("No users in mapping. Add plex_user_id entries to user_mapping.json")
        for user in tautulli.get_users():
            uid = user.get("user_id")
            if uid:
                user_ids.add(int(uid))
        print(f"Falling back to all Tautulli users: {len(user_ids)}")

    aggregator = WrappedAggregator(tautulli, settings, telegram, cache, year=year)

    for uid in sorted(user_ids):
        print(f"Computing wrapped for user_id={uid} year={year}...")
        try:
            payload = aggregator.get_or_compute(uid, force=args.force)
            print(f"  OK: {payload.display_name} — {payload.total_plays} plays")
        except Exception as exc:
            print(f"  ERROR: {exc}")

    tautulli.close()
    print("Done.")


if __name__ == "__main__":
    main()
