from __future__ import annotations

import logging
import re
from typing import Any, Callable, Literal

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

MediaKind = Literal["movie", "show"]

_PLEX_THUMB_WITH_TS = re.compile(
    r"^(?P<base>/library/metadata/\d+/(?:thumb|art|banner))/\d+$"
)
_RATING_KEY_FROM_PATH = re.compile(r"^/library/metadata/(?P<rating_key>\d+)/")
_TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"


def rating_key_from_poster_path(path: str) -> str | None:
    match = _RATING_KEY_FROM_PATH.match(path)
    return match.group("rating_key") if match else None


def plex_poster_paths(path: str) -> list[str]:
    """Plex thumb URLs from Tautulli often include a stale timestamp segment."""
    paths = [path]
    match = _PLEX_THUMB_WITH_TS.match(path)
    if match:
        paths.append(match.group("base"))
    return paths


def thumb_from_metadata(meta: dict[str, Any], *, media_kind: MediaKind) -> str | None:
    if media_kind == "show":
        thumb = meta.get("grandparent_thumb") or meta.get("thumb")
    else:
        thumb = meta.get("thumb") or meta.get("grandparent_thumb")
    if isinstance(thumb, str) and thumb.strip():
        return thumb.strip()
    return None


def _parse_tmdb_guid(guid: str) -> int | None:
    if not guid.startswith("tmdb://"):
        return None
    raw = guid.split("://", 1)[1].split("?")[0].strip()
    try:
        return int(raw)
    except ValueError:
        return None


def _tmdb_guids_from_metadata(meta: dict[str, Any], *, media_kind: MediaKind) -> list[int]:
    if media_kind == "show":
        raw_guids = meta.get("grandparent_guids") or meta.get("guids") or []
    else:
        raw_guids = meta.get("guids") or meta.get("grandparent_guids") or []
    ids: list[int] = []
    for guid in raw_guids:
        if not isinstance(guid, str):
            continue
        tmdb_id = _parse_tmdb_guid(guid)
        if tmdb_id is not None:
            ids.append(tmdb_id)
    return ids


def _tmdb_poster_by_id(tmdb_id: int, *, api_key: str, media_kind: MediaKind) -> str | None:
    endpoint = "movie" if media_kind == "movie" else "tv"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}",
                params={"api_key": api_key},
            )
            response.raise_for_status()
            poster_path = response.json().get("poster_path")
    except Exception:
        logger.debug("TMDB details lookup failed id=%s", tmdb_id, exc_info=True)
        return None
    if poster_path:
        return f"{_TMDB_POSTER_BASE}{poster_path}"
    return None


def _tmdb_poster_from_metadata(meta: dict[str, Any], *, api_key: str, media_kind: MediaKind) -> str | None:
    for tmdb_id in _tmdb_guids_from_metadata(meta, media_kind=media_kind):
        url = _tmdb_poster_by_id(tmdb_id, api_key=api_key, media_kind=media_kind)
        if url:
            return url
    return None


def _tmdb_poster_by_title(title: str, *, api_key: str, media_kind: MediaKind) -> str | None:
    search_type = "movie" if media_kind == "movie" else "tv"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"https://api.themoviedb.org/3/search/{search_type}",
                params={"api_key": api_key, "query": title},
            )
            response.raise_for_status()
            results = response.json().get("results") or []
    except Exception:
        logger.debug("TMDB search failed for %r", title, exc_info=True)
        return None

    for item in results:
        poster_path = item.get("poster_path")
        if poster_path:
            return f"{_TMDB_POSTER_BASE}{poster_path}"
    return None


def _tmdb_poster_url(
    title: str,
    *,
    api_key: str,
    media_kind: MediaKind,
    meta: dict[str, Any] | None = None,
) -> str | None:
    if meta:
        url = _tmdb_poster_from_metadata(meta, api_key=api_key, media_kind=media_kind)
        if url:
            return url
    if title.strip():
        return _tmdb_poster_by_title(title, api_key=api_key, media_kind=media_kind)
    return None


def resolve_poster(
    *,
    settings: Settings,
    thumb: str | None,
    rating_key: str | int | None,
    title: str,
    media_kind: MediaKind,
    get_metadata: Callable[[str | int], dict[str, Any]] | None = None,
    tmdb_cache: dict[tuple[str, str], str | None] | None = None,
) -> str | None:
    """Pick the best poster URL/path for display (Plex proxy path or external HTTPS)."""
    meta: dict[str, Any] = {}
    if rating_key and get_metadata is not None:
        meta = get_metadata(rating_key)

    resolved = thumb_from_metadata(meta, media_kind=media_kind) if meta else None
    if not resolved and thumb and str(thumb).strip():
        resolved = str(thumb).strip()

    if resolved and resolved.startswith(("http://", "https://")):
        return resolved

    api_key = settings.tmdb_api_key.strip()
    if api_key:
        cache_key = (media_kind, title.strip().lower())
        if tmdb_cache is not None and cache_key in tmdb_cache:
            tmdb_url = tmdb_cache[cache_key]
        else:
            tmdb_url = _tmdb_poster_url(
                title,
                api_key=api_key,
                media_kind=media_kind,
                meta=meta or None,
            )
            if tmdb_cache is not None:
                tmdb_cache[cache_key] = tmdb_url
        if tmdb_url:
            return tmdb_url

    if resolved and resolved.startswith("/library/"):
        return resolved

    return resolved
