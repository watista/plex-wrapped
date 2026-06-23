from unittest.mock import MagicMock

import httpx

from app.wrapped.tmdb_actors import compute_top_actors, fetch_cast, profile_url


def test_profile_url():
    assert profile_url("/abc.jpg") == "https://image.tmdb.org/t/p/h632/abc.jpg"
    assert profile_url(None) is None


def test_fetch_cast_movie(monkeypatch):
    def fake_get(url, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={
                "cast": [
                    {"id": 1, "name": "Lead Actor", "profile_path": "/lead.jpg", "order": 0},
                    {"id": 2, "name": "Co-star", "profile_path": "/co.jpg", "order": 1},
                ]
            },
            request=request,
        )

    monkeypatch.setattr(
        "app.wrapped.tmdb_actors.httpx.Client",
        lambda **_: MagicMock(
            __enter__=lambda s: MagicMock(get=fake_get),
            __exit__=lambda *a: None,
        ),
    )

    cast = fetch_cast(27205, "movie", api_key="test-key")
    assert len(cast) == 2
    assert cast[0]["name"] == "Lead Actor"


def test_compute_top_actors_weights_show_plays(monkeypatch):
    meta = {"grandparent_guids": ["tmdb://1396"]}

    def get_metadata(_key):
        return meta

    def fake_get(url, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={
                "cast": [
                    {"id": 10, "name": "Bryan Cranston", "profile_path": "/bryan.jpg", "order": 0},
                    {"id": 11, "name": "Aaron Paul", "profile_path": "/aaron.jpg", "order": 1},
                ]
            },
            request=request,
        )

    monkeypatch.setattr(
        "app.wrapped.tmdb_actors.httpx.Client",
        lambda **_: MagicMock(
            __enter__=lambda s: MagicMock(get=fake_get),
            __exit__=lambda *a: None,
        ),
    )

    show_stats = {
        "Breaking Bad": {"plays": 62, "rating_key": "999"},
    }
    actors = compute_top_actors(
        movie_stats={},
        show_stats=show_stats,
        get_metadata=get_metadata,
        api_key="test-key",
    )

    assert len(actors) == 2
    assert actors[0].name == "Bryan Cranston"
    assert actors[0].plays == 62
    assert actors[0].title_count == 1
    assert actors[0].top_title == "Breaking Bad"
    assert actors[0].top_title_kind == "show"
    assert actors[0].thumb == "https://image.tmdb.org/t/p/h632/bryan.jpg"


def test_compute_top_actors_without_api_key():
    actors = compute_top_actors(
        movie_stats={"Inception": {"plays": 3, "rating_key": "1"}},
        show_stats={},
        get_metadata=lambda _k: {},
        api_key="",
    )
    assert actors == []
