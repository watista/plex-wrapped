from __future__ import annotations

import logging
from typing import Any, Callable, Literal

import httpx

from app.models.schemas import ActorStat
from app.wrapped.posters import _tmdb_guids_from_metadata

logger = logging.getLogger(__name__)

MediaKind = Literal["movie", "show"]
_TMDB_PROFILE_BASE = "https://image.tmdb.org/t/p/h632"
_CAST_BILLING_LIMIT = 15


def profile_url(profile_path: str | None) -> str | None:
    if not profile_path or not str(profile_path).strip():
        return None
    path = str(profile_path).strip()
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{_TMDB_PROFILE_BASE}{path}"


def _search_tmdb_id(title: str, media_kind: MediaKind, *, api_key: str) -> int | None:
    search_type = "movie" if media_kind == "movie" else "tv"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"https://api.themoviedb.org/3/search/{search_type}",
                params={"api_key": api_key, "query": title},
            )
            response.raise_for_status()
            results = response.json().get("results") or []
            if results and results[0].get("id") is not None:
                return int(results[0]["id"])
    except Exception:
        logger.debug("TMDB search failed for %r", title, exc_info=True)
    return None


def _resolve_tmdb_id(
    *,
    title: str,
    media_kind: MediaKind,
    meta: dict[str, Any],
    api_key: str,
    search_cache: dict[tuple[str, str], int | None] | None = None,
) -> int | None:
    tmdb_ids = _tmdb_guids_from_metadata(meta, media_kind=media_kind)
    if tmdb_ids:
        return tmdb_ids[0]

    cache_key = (media_kind, title.strip().lower())
    if search_cache is not None and cache_key in search_cache:
        return search_cache[cache_key]

    tmdb_id = _search_tmdb_id(title, media_kind, api_key=api_key)
    if search_cache is not None:
        search_cache[cache_key] = tmdb_id
    return tmdb_id


def fetch_cast(
    tmdb_id: int,
    media_kind: MediaKind,
    *,
    api_key: str,
    cache: dict[tuple[str, int], list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    cache_key = (media_kind, tmdb_id)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    endpoint = "movie" if media_kind == "movie" else "tv"
    cast: list[dict[str, Any]] = []
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}/credits",
                params={"api_key": api_key},
            )
            response.raise_for_status()
            raw = response.json().get("cast") or []
            for member in raw[:_CAST_BILLING_LIMIT]:
                if not isinstance(member, dict):
                    continue
                person_id = member.get("id")
                name = (member.get("name") or "").strip()
                if person_id is None or not name:
                    continue
                cast.append(
                    {
                        "id": int(person_id),
                        "name": name,
                        "profile_path": member.get("profile_path"),
                    }
                )
    except Exception:
        logger.debug(
            "TMDB credits lookup failed kind=%s id=%s",
            media_kind,
            tmdb_id,
            exc_info=True,
        )
        cast = []

    if cache is not None:
        cache[cache_key] = cast
    return cast


def _accumulate_title_cast(
    actor_stats: dict[int, dict[str, Any]],
    *,
    title: str,
    plays: int,
    rating_key: str | int | None,
    media_kind: MediaKind,
    get_metadata: Callable[[str | int], dict[str, Any]],
    api_key: str,
    credits_cache: dict[tuple[str, int], list[dict[str, Any]]] | None,
    search_cache: dict[tuple[str, str], int | None] | None,
) -> None:
    if not plays or not rating_key:
        return

    meta = get_metadata(rating_key)
    tmdb_id = _resolve_tmdb_id(
        title=title,
        media_kind=media_kind,
        meta=meta,
        api_key=api_key,
        search_cache=search_cache,
    )
    if tmdb_id is None:
        return

    cast = fetch_cast(tmdb_id, media_kind, api_key=api_key, cache=credits_cache)
    if not cast:
        return

    for member in cast:
        pid = member["id"]
        if pid not in actor_stats:
            actor_stats[pid] = {
                "name": member["name"],
                "plays": 0,
                "titles": set(),
                "title_plays": {},
                "thumb": profile_url(member.get("profile_path")),
            }
        actor_stats[pid]["plays"] += plays
        actor_stats[pid]["titles"].add(title)
        title_plays = actor_stats[pid]["title_plays"]
        title_plays[title] = int(title_plays.get(title) or 0) + plays
        if not actor_stats[pid]["thumb"]:
            actor_stats[pid]["thumb"] = profile_url(member.get("profile_path"))


def compute_top_actors(
    *,
    movie_stats: dict[str, dict[str, Any]],
    show_stats: dict[str, dict[str, Any]],
    get_metadata: Callable[[str | int], dict[str, Any]],
    api_key: str,
    credits_cache: dict[tuple[str, int], list[dict[str, Any]]] | None = None,
    search_cache: dict[tuple[str, str], int | None] | None = None,
    limit: int = 3,
) -> list[ActorStat]:
    """Rank actors by total plays across watched titles using TMDB cast credits."""
    key = (api_key or "").strip()
    if not key:
        return []

    actor_stats: dict[int, dict[str, Any]] = {}

    for title, data in movie_stats.items():
        _accumulate_title_cast(
            actor_stats,
            title=title,
            plays=int(data.get("plays") or 0),
            rating_key=data.get("rating_key"),
            media_kind="movie",
            get_metadata=get_metadata,
            api_key=key,
            credits_cache=credits_cache,
            search_cache=search_cache,
        )

    for title, data in show_stats.items():
        _accumulate_title_cast(
            actor_stats,
            title=title,
            plays=int(data.get("plays") or 0),
            rating_key=data.get("rating_key"),
            media_kind="show",
            get_metadata=get_metadata,
            api_key=key,
            credits_cache=credits_cache,
            search_cache=search_cache,
        )

    entries: list[ActorStat] = []
    for data in actor_stats.values():
        if data["plays"] <= 0:
            continue
        title_plays: dict[str, int] = data.get("title_plays") or {}
        top_title: str | None = None
        if title_plays:
            top_title = max(title_plays.items(), key=lambda item: (item[1], item[0]))[0]
        top_title_kind: MediaKind | None = None
        if top_title:
            if top_title in show_stats:
                top_title_kind = "show"
            elif top_title in movie_stats:
                top_title_kind = "movie"
        entries.append(
            ActorStat(
                name=data["name"],
                plays=data["plays"],
                title_count=len(data["titles"]),
                thumb=data.get("thumb"),
                top_title=top_title,
                top_title_kind=top_title_kind,
            )
        )
    entries.sort(key=lambda actor: (-actor.plays, -actor.title_count, actor.name))
    return entries[:limit]
