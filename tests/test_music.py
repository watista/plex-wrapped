from unittest.mock import patch

from app.config import Settings
from app.models.schemas import ActorStat, GenreStat, MediaItem, ServerStats, WrappedPayload
from app.wrapped.music import (
    attach_wrapped_music,
    build_wrapped_music,
    genre_slug,
    slide_needs_special_music,
)


def _sample_payload(**overrides) -> WrappedPayload:
    base = WrappedPayload(
        year=2025,
        user_id=1,
        display_name="Test",
        username="test",
        movie_plays=10,
        tv_plays=20,
        top_movies=[MediaItem(title="Dune: Part Two", plays=4)],
        top_shows=[MediaItem(title="Breaking Bad", plays=62)],
        top_movie_genres=[GenreStat(name="Science Fiction", plays=48)],
        top_show_genres=[GenreStat(name="Drama", plays=210)],
        top_actors=[
            ActorStat(
                name="Bryan Cranston",
                plays=62,
                title_count=1,
                top_title="Breaking Bad",
                top_title_kind="show",
            )
        ],
        server=ServerStats(server_top_show="The Office", server_top_movie="Inception"),
    )
    data = base.model_dump()
    data.update(overrides)
    return WrappedPayload(**data)


def test_genre_slug_maps_science_fiction():
    assert genre_slug("Science Fiction") == "sci_fi"
    assert genre_slug("Unknown Genre") == "cinematic"


def test_slide_needs_special_music():
    assert slide_needs_special_music("top-movies")
    assert not slide_needs_special_music("welcome")


def test_default_pool_video_ids():
    from app.wrapped.theme_lookup import DEFAULT_POOL_VIDEO_IDS

    assert len(DEFAULT_POOL_VIDEO_IDS) == 11
    assert DEFAULT_POOL_VIDEO_IDS[0] == "dW9xbFLaatU"
    from app.wrapped.theme_lookup import genre_youtube_queries

    queries = genre_youtube_queries("drama")
    assert queries
    assert all("instrumental only" in q for q in queries)


@patch("app.wrapped.music.resolve_default_pool_audio", return_value=["/api/audio/pool1.mp3"])
@patch("app.wrapped.music._resolve_genre_url")
@patch("app.wrapped.music._resolve_theme_url")
def test_build_wrapped_music_assigns_slides(mock_theme, mock_genre, _mock_pool):
    mock_theme.side_effect = lambda settings, title, **kwargs: f"/api/audio/{title.replace(' ', '_')}.mp3"
    mock_genre.side_effect = lambda settings, name, **kwargs: f"/api/audio/genre_{genre_slug(name)}.mp3"

    payload = _sample_payload()
    music = build_wrapped_music(payload, Settings(music_download_enabled=False))

    assert music.default_pool == ["/api/audio/pool1.mp3"]
    assert music.slides["top-movies"] == "/api/audio/Dune:_Part_Two.mp3"
    assert music.slides["movie-genres"] == "/api/audio/genre_sci_fi.mp3"
    assert music.slides["show-genres"] == "/api/audio/genre_drama.mp3"


def test_attach_wrapped_music_disabled():
    payload = _sample_payload()
    attach_wrapped_music(payload, Settings(music_enabled=False))
    assert payload.music.default_pool == []
    assert payload.music.slides == {}
