#!/usr/bin/env python3
"""Pre-compute wrapped stats for all mapped users."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai import CursorAIClient, CursorAIError
from app.config import get_settings
from app.logging_setup import configure_logging
from app.models.cache import WrappedCache
from app.tautulli.client import TautulliClient
from app.telegram.loader import load_telegram_data, load_user_mapping
from app.wrapped.aggregator import WrappedAggregator

logger = logging.getLogger(__name__)


def _check_ai(ai: CursorAIClient) -> int:
    """Verify the Cursor AI connection and print the result."""
    print("Checking Cursor AI connection...")
    try:
        reply = ai.health_check()
    except CursorAIError as exc:
        print(f"  Cursor AI not ready: {exc}")
        return 1
    print(f"  OK: Cursor AI responded with: {reply!r}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-compute Plex Wrapped cache")
    parser.add_argument("--year", type=int, default=None, help="Wrapped year (default: WRAPPED_YEAR)")
    parser.add_argument("--force", action="store_true", help="Recompute even if cached")
    parser.add_argument("--user-id", type=int, default=None, help="Single user id only")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging")
    parser.add_argument(
        "--check-ai",
        action="store_true",
        help="Verify the Cursor AI connection and exit (no compute)",
    )
    args = parser.parse_args()

    settings = get_settings()
    log_level = "DEBUG" if args.verbose else settings.log_level
    configure_logging(log_level)
    year = args.year or settings.wrapped_year

    if args.check_ai:
        sys.exit(_check_ai(CursorAIClient(settings)))

    tautulli = TautulliClient(settings)
    cache = WrappedCache(settings, database_path=settings.database_path)
    telegram = load_telegram_data(settings, year)
    mapping = load_user_mapping(settings)
    ai = CursorAIClient(settings)
    logger.info("Cursor AI enabled=%s model=%s", ai.enabled, settings.cursor_model)

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

    aggregator = WrappedAggregator(tautulli, settings, telegram, cache, year=year, ai=ai)

    logger.info(
        "Starting compute year=%s users=%s force=%s tautulli=%s db=%s",
        year,
        len(user_ids),
        args.force,
        settings.tautulli_url,
        cache.path,
    )

    for uid in sorted(user_ids):
        print(f"Computing wrapped for user_id={uid} year={year}...")
        try:
            from_cache = not args.force and aggregator.get_cached(uid) is not None
            payload = aggregator.get_or_compute(uid, force=args.force)
            source = "cache" if from_cache else "computed"
            print(
                f"  OK: {payload.display_name} — {payload.total_plays} plays, "
                f"{payload.watch_hours}h ({source})"
            )
            logger.info(
                "Done user_id=%s name=%s plays=%s movies=%s tv=%s watch_hours=%s",
                uid,
                payload.display_name,
                payload.total_plays,
                payload.movie_plays,
                payload.tv_plays,
                payload.watch_hours,
            )
        except Exception as exc:
            print(f"  ERROR: {exc}")
            logger.exception("Failed user_id=%s year=%s", uid, year)

    tautulli.close()
    print("Done.")


if __name__ == "__main__":
    main()
