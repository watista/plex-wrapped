from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from app.wrapped.theme_lookup import (
    ThemeSearchPlan,
    ThemeTrack,
    YoutubeQuery,
    build_youtube_search_plan,
    cache_key,
    genre_cache_key,
    genre_youtube_queries,
    score_youtube_candidate,
)

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

MediaKind = Literal["movie", "show"]

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
_PLAYBACK_EXTENSIONS = frozenset({".mp3", ".m4a", ".aac"})
_MIN_AUDIO_BYTES = 8192


def is_valid_video_id(video_id: str) -> bool:
    return bool(_VIDEO_ID_RE.match(video_id))


_YT_URL_ID_RE = re.compile(
    r"(?:youtube\.com/watch\?(?:[^&\s]+&)*v=|youtu\.be/)([A-Za-z0-9_-]{6,32})"
)


def parse_youtube_video_id(value: str) -> str | None:
    raw = (value or "").strip()
    if is_valid_video_id(raw):
        return raw
    match = _YT_URL_ID_RE.search(raw)
    if match and is_valid_video_id(match.group(1)):
        return match.group(1)
    return None


def yt_dlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def ffmpeg_available(ffmpeg_location: str | None = None) -> bool:
    if ffmpeg_location and Path(ffmpeg_location).is_file():
        return True
    return shutil.which("ffmpeg") is not None


def api_audio_url(path: Path) -> str:
    return f"/api/audio/{path.name}"


def find_cached_by_key(cache_dir: Path, key: str) -> Path | None:
    for ext in (".mp3", ".m4a", ".aac"):
        path = cache_dir / f"{key}{ext}"
        try:
            if path.is_file() and path.stat().st_size >= _MIN_AUDIO_BYTES:
                return path
        except OSError:
            continue
    return None


def _yt_dlp_base_cmd(*, ffmpeg_location: str | None = None) -> list[str]:
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-overwrites",
        "--no-warnings",
        "--extractor-args",
        "youtube:player_client=android",
    ]
    if ffmpeg_location:
        loc = Path(ffmpeg_location)
        if loc.is_file():
            cmd.extend(["--ffmpeg-location", str(loc.parent)])
        elif loc.is_dir():
            cmd.extend(["--ffmpeg-location", str(loc)])
    return cmd


def _parse_duration(value: str) -> int | None:
    value = (value or "").strip()
    if not value or value.lower() in {"na", "none"}:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def search_best_video_id(
    yt_query: YoutubeQuery,
    *,
    media_title: str,
    theme_track: ThemeTrack | None,
    timeout: float = 60.0,
    ffmpeg_location: str | None = None,
    max_results: int = 10,
) -> str | None:
    """Search YouTube and pick the best-scoring candidate above the query threshold."""
    if not yt_dlp_available():
        return None
    cleaned = " ".join(yt_query.text.split()).strip()
    if not cleaned:
        return None

    cmd = [
        *_yt_dlp_base_cmd(ffmpeg_location=ffmpeg_location),
        "--flat-playlist",
        "--print",
        "%(id)s\t%(title)s\t%(duration)s",
        f"ytsearch{max_results}:{cleaned}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("yt-dlp search failed for %r: %s", cleaned, exc)
        return None
    if result.returncode != 0:
        logger.debug(
            "yt-dlp search exit=%s query=%r stderr=%s",
            result.returncode,
            cleaned,
            (result.stderr or "").strip()[:400],
        )
        return None

    best_id: str | None = None
    best_score = -999.0
    for line in result.stdout.splitlines():
        parts = line.split("\t", 2)
        if not parts:
            continue
        vid = parts[0].strip()
        if not is_valid_video_id(vid):
            continue
        title = parts[1].strip() if len(parts) > 1 else ""
        duration = _parse_duration(parts[2]) if len(parts) > 2 else None
        score = score_youtube_candidate(
            video_title=title,
            duration=duration,
            media_title=media_title,
            theme_track=theme_track,
            require_track_match=yt_query.require_track_match,
            require_media_overlap=yt_query.require_media_overlap,
            require_instrumental=yt_query.require_instrumental,
        )
        if score > best_score:
            best_score = score
            best_id = vid

    if best_id and best_score >= yt_query.min_score:
        logger.info(
            "YouTube pick query=%r id=%s score=%.1f min=%.1f",
            cleaned,
            best_id,
            best_score,
            yt_query.min_score,
        )
        return best_id

    if best_id:
        logger.info(
            "YouTube reject query=%r best_id=%s score=%.1f below min=%.1f",
            cleaned,
            best_id,
            best_score,
            yt_query.min_score,
        )
    return None


def _cleanup_bad_files(cache_dir: Path, stem: str) -> None:
    for path in cache_dir.glob(f"{stem}.*"):
        try:
            if not path.is_file():
                continue
            if path.suffix.lower() not in _PLAYBACK_EXTENSIONS or path.stat().st_size < _MIN_AUDIO_BYTES:
                path.unlink(missing_ok=True)
        except OSError:
            pass


def download_audio(
    video_id: str,
    cache_dir: Path,
    *,
    cache_file_stem: str,
    timeout: float = 300.0,
    ffmpeg_location: str | None = None,
) -> Path | None:
    if not is_valid_video_id(video_id):
        return None
    if not yt_dlp_available():
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    existing = find_cached_by_key(cache_dir, cache_file_stem)
    if existing:
        return existing

    _cleanup_bad_files(cache_dir, cache_file_stem)

    url = f"https://www.youtube.com/watch?v={video_id}"
    has_ffmpeg = ffmpeg_available(ffmpeg_location)
    target_mp3 = cache_dir / f"{cache_file_stem}.mp3"
    target_m4a = cache_dir / f"{cache_file_stem}.m4a"

    if has_ffmpeg:
        cmd = [
            *_yt_dlp_base_cmd(ffmpeg_location=ffmpeg_location),
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "5",
            "-o",
            str(target_mp3),
            url,
        ]
    else:
        cmd = [
            *_yt_dlp_base_cmd(ffmpeg_location=ffmpeg_location),
            "-f",
            "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio",
            "--reject-formats",
            "webm,opus",
            "-o",
            str(target_m4a),
            url,
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("yt-dlp download failed id=%s: %s", video_id, exc)
        _cleanup_bad_files(cache_dir, cache_file_stem)
        return None

    if result.returncode != 0:
        logger.warning(
            "yt-dlp download exit=%s id=%s stderr=%s",
            result.returncode,
            video_id,
            (result.stderr or "").strip()[:500],
        )

    cached = find_cached_by_key(cache_dir, cache_file_stem)
    if cached:
        return cached

    for path in cache_dir.glob(f"_tmp_{video_id}.*"):
        if path.suffix.lower() not in _PLAYBACK_EXTENSIONS:
            path.unlink(missing_ok=True)
            continue
        if path.stat().st_size < _MIN_AUDIO_BYTES:
            path.unlink(missing_ok=True)
            continue
        dest = cache_dir / f"{cache_file_stem}{path.suffix.lower()}"
        path.replace(dest)
        return dest

    _cleanup_bad_files(cache_dir, cache_file_stem)
    return None


def _try_plan_queries(
    plan: ThemeSearchPlan,
    cache_dir: Path,
    cache_file_stem: str,
    *,
    ffmpeg_location: str | None,
    label: str,
) -> str | None:
    for yt_query in plan.queries:
        video_id = search_best_video_id(
            yt_query,
            media_title=plan.media_title,
            theme_track=plan.track,
            ffmpeg_location=ffmpeg_location,
        )
        if not video_id:
            continue
        path = download_audio(
            video_id,
            cache_dir,
            cache_file_stem=cache_file_stem,
            ffmpeg_location=ffmpeg_location,
        )
        if path:
            logger.info("Theme audio saved %s query=%r file=%s", label, yt_query.text, path.name)
            return api_audio_url(path)
    return None


def resolve_video_id_audio(
    video_id: str,
    cache_dir: Path,
    *,
    cache_file_stem: str,
    download: bool = True,
    ffmpeg_location: str | None = None,
) -> str | None:
    if not is_valid_video_id(video_id):
        return None
    if not download:
        cached = find_cached_by_key(cache_dir, cache_file_stem)
        return api_audio_url(cached) if cached else None

    cached = find_cached_by_key(cache_dir, cache_file_stem)
    if cached:
        return api_audio_url(cached)

    path = download_audio(
        video_id,
        cache_dir,
        cache_file_stem=cache_file_stem,
        ffmpeg_location=ffmpeg_location,
    )
    return api_audio_url(path) if path else None


def resolve_media_theme_audio(
    title: str,
    cache_dir: Path,
    *,
    year: int | None,
    media_kind: MediaKind,
    download: bool = True,
    ffmpeg_location: str | None = None,
    settings: Settings | None = None,
) -> str | None:
    if settings:
        from app.wrapped.music_overrides import match_music_override, override_cache_key

        matched = match_music_override(settings, title, media_kind)
        if matched:
            override_id, canonical_key = matched
            override_key = override_cache_key(canonical_key, media_kind)
            url = resolve_video_id_audio(
                override_id,
                cache_dir,
                cache_file_stem=override_key,
                download=download,
                ffmpeg_location=ffmpeg_location,
            )
            if url:
                return url
            logger.warning(
                "Music override configured for %r (%s) video_id=%s but audio unavailable",
                title,
                media_kind,
                override_id,
            )
            return None

    key = cache_key(title, year=year, media_kind=media_kind)
    if not download:
        cached = find_cached_by_key(cache_dir, key)
        return api_audio_url(cached) if cached else None

    cached = find_cached_by_key(cache_dir, key)
    if cached:
        return api_audio_url(cached)

    plan = build_youtube_search_plan(title, year=year, media_kind=media_kind, settings=settings)
    return _try_plan_queries(
        plan,
        cache_dir,
        key,
        ffmpeg_location=ffmpeg_location,
        label=f"media={title!r}",
    )


def resolve_genre_theme_audio(
    genre_slug: str,
    cache_dir: Path,
    *,
    download: bool = True,
    ffmpeg_location: str | None = None,
) -> str | None:
    """Download a genre-appropriate instrumental loop from YouTube (shared cache)."""
    key = genre_cache_key(genre_slug)
    if not download:
        cached = find_cached_by_key(cache_dir, key)
        return api_audio_url(cached) if cached else None

    cached = find_cached_by_key(cache_dir, key)
    if cached:
        return api_audio_url(cached)

    from app.wrapped.theme_lookup import YoutubeQuery, _MIN_SCORE_RELAXED

    queries = [
        YoutubeQuery(
            text=q,
            min_score=_MIN_SCORE_RELAXED,
            require_track_match=False,
            require_media_overlap=False,
            require_instrumental=True,
        )
        for q in genre_youtube_queries(genre_slug)
    ]
    plan = ThemeSearchPlan(
        queries=queries,
        track=None,
        media_title=genre_slug.replace("_", " "),
    )
    return _try_plan_queries(
        plan,
        cache_dir,
        key,
        ffmpeg_location=ffmpeg_location,
        label=f"genre={genre_slug}",
    )


def resolve_theme_audio(
    query: str,
    cache_dir: Path,
    *,
    download: bool = True,
    ffmpeg_location: str | None = None,
) -> str | None:
    if not download:
        return None

    from app.wrapped.theme_lookup import YoutubeQuery, _MIN_SCORE_RELAXED

    yt_query = YoutubeQuery(
        text=query,
        min_score=_MIN_SCORE_RELAXED,
        require_track_match=False,
        require_media_overlap=False,
    )
    video_id = search_best_video_id(
        yt_query,
        media_title=query,
        theme_track=None,
        ffmpeg_location=ffmpeg_location,
    )
    if not video_id:
        return None
    stem = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")[:72] or "generic"
    path = download_audio(
        video_id,
        cache_dir,
        cache_file_stem=f"generic_{stem}",
        ffmpeg_location=ffmpeg_location,
    )
    return api_audio_url(path) if path else None


def resolve_fixed_slide_audio(
    cache_dir: Path,
    *,
    download: bool = True,
    ffmpeg_location: str | None = None,
) -> dict[str, str]:
    """Download fixed background tracks per slide id."""
    from app.wrapped.theme_lookup import FIXED_SLIDE_VIDEO_IDS, fixed_slide_cache_key

    slides: dict[str, str] = {}
    for slide_id, video_id in FIXED_SLIDE_VIDEO_IDS.items():
        key = fixed_slide_cache_key(slide_id)
        if not download:
            cached = find_cached_by_key(cache_dir, key)
            if cached:
                slides[slide_id] = api_audio_url(cached)
            continue

        cached = find_cached_by_key(cache_dir, key)
        if cached:
            slides[slide_id] = api_audio_url(cached)
            continue

        path = download_audio(
            video_id,
            cache_dir,
            cache_file_stem=key,
            ffmpeg_location=ffmpeg_location,
        )
        if path:
            logger.info("Fixed slide track slide=%s id=%s -> %s", slide_id, video_id, path.name)
            slides[slide_id] = api_audio_url(path)
        else:
            logger.warning("Fixed slide track slide=%s id=%s download failed", slide_id, video_id)

    return slides
