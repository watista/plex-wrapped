from unittest.mock import MagicMock

import httpx

from app.config import Settings
from app.wrapped.posters import (
    plex_poster_paths,
    rating_key_from_poster_path,
    resolve_poster,
    thumb_from_metadata,
)


def test_rating_key_from_poster_path():
    assert rating_key_from_poster_path("/library/metadata/1219/thumb/1462175063") == "1219"


def test_plex_poster_paths_strips_stale_timestamp():
    assert plex_poster_paths("/library/metadata/1219/thumb/1462175063") == [
        "/library/metadata/1219/thumb/1462175063",
        "/library/metadata/1219/thumb",
    ]


def test_thumb_from_metadata_prefers_grandparent_for_shows():
    meta = {
        "thumb": "/library/metadata/999/thumb/1",
        "grandparent_thumb": "/library/metadata/1219/thumb/2",
    }
    assert thumb_from_metadata(meta, media_kind="show") == "/library/metadata/1219/thumb/2"
    assert thumb_from_metadata(meta, media_kind="movie") == "/library/metadata/999/thumb/1"


def test_resolve_poster_uses_metadata_thumb_without_tmdb():
    settings = Settings()
    meta = {"thumb": "/library/metadata/42/thumb/99"}

    def get_metadata(_key):
        return meta

    url = resolve_poster(
        settings=settings,
        thumb="/library/metadata/42/thumb/1",
        rating_key=42,
        title="Inception",
        media_kind="movie",
        get_metadata=get_metadata,
    )
    assert url == "/library/metadata/42/thumb/99"


def test_resolve_poster_prefers_tmdb_over_plex_path(monkeypatch):
    settings = Settings(tmdb_api_key="test-key")
    meta = {
        "thumb": "/library/metadata/42/thumb/99",
        "guids": ["tmdb://27205"],
    }

    def get_metadata(_key):
        return meta

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"poster_path": "/inception.jpg"},
            request=request,
        )

    monkeypatch.setattr("app.wrapped.posters.httpx.Client", lambda **_: MagicMock(
        __enter__=lambda s: MagicMock(get=fake_get),
        __exit__=lambda *a: None,
    ))

    url = resolve_poster(
        settings=settings,
        thumb="/library/metadata/42/thumb/1",
        rating_key=42,
        title="Inception",
        media_kind="movie",
        get_metadata=get_metadata,
    )
    assert url == "https://image.tmdb.org/t/p/w500/inception.jpg"


def test_resolve_poster_tmdb_fallback(monkeypatch):
    settings = Settings(tmdb_api_key="test-key")

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"results": [{"poster_path": "/abc.jpg"}]},
            request=request,
        )

    monkeypatch.setattr("app.wrapped.posters.httpx.Client", lambda **_: MagicMock(
        __enter__=lambda s: MagicMock(get=fake_get),
        __exit__=lambda *a: None,
    ))

    url = resolve_poster(
        settings=settings,
        thumb=None,
        rating_key=None,
        title="Inception",
        media_kind="movie",
    )
    assert url == "https://image.tmdb.org/t/p/w500/abc.jpg"
