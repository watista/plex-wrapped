from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from app.config import Settings
from app.models.schemas import WrappedMusic, WrappedPayload
from app.wrapped.youtube_audio import (
    ffmpeg_available,
    resolve_default_pool_audio,
    resolve_genre_theme_audio,
    resolve_media_theme_audio,
    yt_dlp_available,
)

logger = logging.getLogger(__name__)

MediaKind = Literal["movie", "show"]

_GENRE_SLUGS: dict[str, str] = {
    "action": "action",
    "adventure": "adventure",
    "animation": "animation",
    "comedy": "comedy",
    "crime": "crime",
    "documentary": "documentary",
    "drama": "drama",
    "family": "family",
    "fantasy": "fantasy",
    "history": "history",
    "horror": "horror",
    "music": "music",
    "mystery": "mystery",
    "romance": "romance",
    "science fiction": "sci_fi",
    "sci-fi": "sci_fi",
    "scifi": "sci_fi",
    "thriller": "thriller",
    "war": "war",
    "western": "western",
}

_DEFAULT_GENRE_SLUG = "cinematic"

_SPECIAL_SLIDE_IDS = frozenset(
    {
        "top-movies",
        "top-shows",
        "favorite-actor",
        "movie-genres",
        "show-genres",
        "server-vs-you",
        "summary",
    }
)


def genre_slug(name: str) -> str:
    key = (name or "").strip().lower()
    return _GENRE_SLUGS.get(key, _DEFAULT_GENRE_SLUG)


def _ffmpeg_loc(settings: Settings) -> str | None:
    return (settings.ffmpeg_location or "").strip() or None


def _resolve_genre_url(settings: Settings, genre_name: str, *, download: bool) -> str | None:
    slug = genre_slug(genre_name)
    cache_dir = settings.resolve_path(settings.audio_cache_path)
    url = resolve_genre_theme_audio(
        slug,
        cache_dir,
        download=download,
        ffmpeg_location=_ffmpeg_loc(settings),
    )
    if url:
        logger.info("Genre music resolved genre=%r slug=%s -> %s", genre_name, slug, url)
    return url


def _resolve_theme_url(
    settings: Settings,
    title: str,
    *,
    year: int | None = None,
    media_kind: MediaKind = "movie",
    download: bool,
) -> str | None:
    if not title.strip():
        return None
    cache_dir = settings.resolve_path(settings.audio_cache_path)
    url = resolve_media_theme_audio(
        title,
        cache_dir,
        year=year,
        media_kind=media_kind,
        download=download,
        ffmpeg_location=_ffmpeg_loc(settings),
        settings=settings,
    )
    if url:
        logger.info("Music theme resolved title=%r kind=%s -> %s", title, media_kind, url)
    else:
        logger.info("Music theme missing title=%r kind=%s year=%s", title, media_kind, year)
    return url


def _build_default_pool(settings: Settings, *, download: bool) -> list[str]:
    cache_dir = settings.resolve_path(settings.audio_cache_path)
    return resolve_default_pool_audio(
        cache_dir,
        download=download,
        ffmpeg_location=_ffmpeg_loc(settings),
    )


def _pick_summary_title(payload: WrappedPayload) -> tuple[str | None, MediaKind | None]:
    if payload.tv_plays > 0 and payload.top_shows:
        return payload.top_shows[0].title, "show"
    if payload.top_movies:
        return payload.top_movies[0].title, "movie"
    return None, None


def _pick_server_top(payload: WrappedPayload) -> tuple[str | None, MediaKind | None]:
    server = payload.server
    if server.server_top_show:
        return server.server_top_show, "show"
    if server.server_top_movie:
        return server.server_top_movie, "movie"
    return None, None


def build_wrapped_music(payload: WrappedPayload, settings: Settings) -> WrappedMusic:
    if not settings.music_enabled:
        return WrappedMusic()

    download = settings.music_download_enabled
    if download and not yt_dlp_available():
        logger.warning(
            "yt-dlp not found on PATH; theme downloads skipped (install yt-dlp for slide music)"
        )
        download = False
    elif download and not ffmpeg_available(_ffmpeg_loc(settings)):
        logger.info(
            "ffmpeg not found; theme downloads will use m4a only (no webm). "
            "Install ffmpeg for mp3 conversion, or set FFMPEG_LOCATION in .env"
        )

    default_pool = _build_default_pool(settings, download=download)
    if not default_pool:
        cinematic = _resolve_genre_url(settings, "cinematic", download=download)
        if cinematic:
            default_pool = [cinematic]

    slides: dict[str, str] = {}

    def assign(slide_id: str, url: str | None) -> None:
        if url:
            slides[slide_id] = url

    if payload.top_movies:
        assign(
            "top-movies",
            _resolve_theme_url(
                settings,
                payload.top_movies[0].title,
                year=payload.year,
                media_kind="movie",
                download=download,
            ),
        )

    if payload.top_shows:
        assign(
            "top-shows",
            _resolve_theme_url(
                settings,
                payload.top_shows[0].title,
                year=payload.year,
                media_kind="show",
                download=download,
            ),
        )

    if payload.top_actors:
        hero = payload.top_actors[0]
        if hero.top_title:
            assign(
                "favorite-actor",
                _resolve_theme_url(
                    settings,
                    hero.top_title,
                    year=payload.year,
                    media_kind=hero.top_title_kind or "movie",
                    download=download,
                ),
            )

    if payload.top_movie_genres:
        assign(
            "movie-genres",
            _resolve_genre_url(settings, payload.top_movie_genres[0].name, download=download),
        )

    if payload.top_show_genres:
        assign(
            "show-genres",
            _resolve_genre_url(settings, payload.top_show_genres[0].name, download=download),
        )

    server_title, server_kind = _pick_server_top(payload)
    if server_title and server_kind:
        assign(
            "server-vs-you",
            _resolve_theme_url(
                settings,
                server_title,
                year=payload.year,
                media_kind=server_kind,
                download=download,
            ),
        )

    summary_title, summary_kind = _pick_summary_title(payload)
    if summary_title and summary_kind:
        assign(
            "summary",
            _resolve_theme_url(
                settings,
                summary_title,
                year=payload.year,
                media_kind=summary_kind,
                download=download,
            ),
        )

    return WrappedMusic(default_pool=default_pool, slides=slides)


def _purge_invalid_cache_files(cache_dir: Path) -> None:
    if not cache_dir.is_dir():
        return
    for path in cache_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in {".webm", ".opus", ".ogg", ".part", ".ytdl"}:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        if path.name.startswith("v2_"):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def attach_wrapped_music(payload: WrappedPayload, settings: Settings) -> None:
    cache_dir = settings.resolve_path(settings.audio_cache_path)
    _purge_invalid_cache_files(cache_dir)
    payload.music = build_wrapped_music(payload, settings)


def slide_needs_special_music(slide_id: str) -> bool:
    return slide_id in _SPECIAL_SLIDE_IDS
