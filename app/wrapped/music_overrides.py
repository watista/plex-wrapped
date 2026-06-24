from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.config import Settings
from app.utils.json_io import load_json_dict

logger = logging.getLogger(__name__)

MediaKind = Literal["movie", "show"]

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
_YT_URL_ID_RE = re.compile(
    r"(?:youtube\.com/watch\?(?:[^&\s]+&)*v=|youtu\.be/)([A-Za-z0-9_-]{6,32})"
)
_YEAR_SUFFIX_RE = re.compile(
    r"\s*[\(\[]\d{4}(?:\s*[-–—]\s*\d{4})?[\)\]]\s*$"
)


def is_valid_video_id(video_id: str) -> bool:
    return bool(_VIDEO_ID_RE.match(video_id))


def parse_youtube_video_id(value: str) -> str | None:
    raw = (value or "").strip()
    if is_valid_video_id(raw):
        return raw
    match = _YT_URL_ID_RE.search(raw)
    if match and is_valid_video_id(match.group(1)):
        return match.group(1)
    return None


def _normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    t = _YEAR_SUFFIX_RE.sub("", t).strip()
    return t


def _title_matches_override(title_key: str, override_key: str) -> bool:
    if title_key == override_key:
        return True
    for sep in (" (", " -", ": "):
        if title_key.startswith(override_key + sep):
            return True
    return False


def _parse_override_bucket(raw: dict | None) -> dict[str, str]:
    bucket: dict[str, str] = {}
    for title, value in (raw or {}).items():
        if not isinstance(title, str) or not isinstance(value, str):
            continue
        video_id = parse_youtube_video_id(value)
        if video_id:
            bucket[_normalize_title(title)] = video_id
    return bucket


def _overrides_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return -1.0


@lru_cache
def _load_overrides(path: str, mtime: float) -> tuple[dict[str, str], dict[str, str]]:
    """Return (movies, shows) maps of normalized title -> video id."""
    movies: dict[str, str] = {}
    shows: dict[str, str] = {}
    file_path = Path(path)
    if not file_path.is_file():
        return movies, shows

    try:
        data = load_json_dict(file_path)
    except Exception:
        logger.warning("Failed to load music overrides from %s", file_path, exc_info=True)
        return movies, shows

    movies = _parse_override_bucket(data.get("movies"))
    shows = _parse_override_bucket(data.get("shows"))
    return movies, shows


def match_music_override(
    settings: Settings,
    title: str,
    media_kind: MediaKind,
) -> tuple[str, str] | None:
    """Return (video_id, canonical_title_key) when an override applies."""
    path = settings.resolve_path(settings.music_overrides_path)
    movies, shows = _load_overrides(str(path), _overrides_mtime(path))
    key = _normalize_title(title)
    if not key:
        return None

    bucket = shows if media_kind == "show" else movies
    video_id = bucket.get(key)
    if video_id and is_valid_video_id(video_id):
        logger.info("Music override hit title=%r kind=%s video_id=%s", title, media_kind, video_id)
        return video_id, key

    for override_key, candidate_id in bucket.items():
        if not is_valid_video_id(candidate_id):
            continue
        if _title_matches_override(key, override_key):
            logger.info(
                "Music override fuzzy hit title=%r kind=%s override_key=%r video_id=%s",
                title,
                media_kind,
                override_key,
                candidate_id,
            )
            return candidate_id, override_key

    return None


def get_override_video_id(
    settings: Settings,
    title: str,
    media_kind: MediaKind,
) -> str | None:
    matched = match_music_override(settings, title, media_kind)
    return matched[0] if matched else None


def override_cache_key(canonical_title_key: str, media_kind: MediaKind) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", canonical_title_key).strip("_")[:72]
    return f"v3_override_{media_kind}_{slug}"
