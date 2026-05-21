from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings

DATE_FMT = "%d-%m-%Y %H:%M:%S"


@dataclass
class TelegramUserStats:
    telegram_id: str
    login_count: int = 0
    film_requests: list[str] = field(default_factory=list)
    serie_requests: list[str] = field(default_factory=list)
    total_requests: int = 0
    top_requested: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TelegramData:
    raw: dict[str, Any]
    by_plex_user_id: dict[int, TelegramUserStats] = field(default_factory=dict)


def parse_telegram_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), DATE_FMT)
    except ValueError:
        return None


def _entries_in_year(section: dict[str, str], year: int) -> list[tuple[datetime, str]]:
    results: list[tuple[datetime, str]] = []
    for date_str, title in section.items():
        dt = parse_telegram_date(date_str)
        if dt and dt.year == year:
            results.append((dt, title))
    return results


def load_user_mapping(settings: Settings | None = None) -> dict[str, dict[str, Any]]:
    settings = settings or get_settings()
    path = settings.resolve_path(settings.user_mapping_path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_telegram_data(settings: Settings | None = None, year: int | None = None) -> TelegramData:
    settings = settings or get_settings()
    year = year or settings.wrapped_year
    path = settings.resolve_path(settings.telegram_requests_path)
    mapping = load_user_mapping(settings)

    raw: dict[str, Any] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)

    # Build reverse map: plex_user_id -> telegram_id
    plex_to_telegram: dict[int, str] = {}
    for telegram_id, entry in mapping.items():
        plex_id = entry.get("plex_user_id")
        if plex_id is not None:
            plex_to_telegram[int(plex_id)] = str(telegram_id)

    by_plex: dict[int, TelegramUserStats] = {}

    for telegram_id, user_data in raw.items():
        if not isinstance(user_data, dict):
            continue

        logins = _entries_in_year(user_data.get("logins", {}), year)
        films = _entries_in_year(user_data.get("film_requests", {}), year)
        series = _entries_in_year(user_data.get("serie_requests", {}), year)

        film_titles = [t for _, t in films]
        serie_titles = [t for _, t in series]
        all_titles = film_titles + serie_titles

        title_counts: dict[str, int] = {}
        for title in all_titles:
            title_counts[title] = title_counts.get(title, 0) + 1

        top_requested = sorted(
            [{"title": t, "count": c} for t, c in title_counts.items()],
            key=lambda x: (-x["count"], x["title"]),
        )[:5]

        stats = TelegramUserStats(
            telegram_id=str(telegram_id),
            login_count=len(logins),
            film_requests=film_titles,
            serie_requests=serie_titles,
            total_requests=len(film_titles) + len(serie_titles),
            top_requested=top_requested,
        )

        # Attach to plex_user_id via mapping
        entry = mapping.get(str(telegram_id), {})
        plex_id = entry.get("plex_user_id")
        if plex_id is not None:
            by_plex[int(plex_id)] = stats

    return TelegramData(raw=raw, by_plex_user_id=by_plex)


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def _title_matched(title: str, normalized_history: list[str]) -> bool:
    norm = normalize_title(title)
    if not norm:
        return False
    return any(norm in h or h in norm for h in normalized_history if h)


def match_requests_to_history(
    film_requests: list[str],
    serie_requests: list[str],
    history_titles: list[str],
) -> list[str]:
    normalized_history = [normalize_title(t) for t in history_titles if t]
    matched: list[str] = []
    for title in film_requests + serie_requests:
        if _title_matched(title, normalized_history):
            matched.append(title)
    return list(dict.fromkeys(matched))


def count_unique_matched(
    titles: list[str],
    history_titles: list[str],
) -> int:
    normalized_history = [normalize_title(t) for t in history_titles if t]
    seen: set[str] = set()
    for title in titles:
        norm = normalize_title(title)
        if not norm or norm in seen:
            continue
        if _title_matched(title, normalized_history):
            seen.add(norm)
    return len(seen)
