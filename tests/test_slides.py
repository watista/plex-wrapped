from app.models.schemas import GenreStat, MediaItem, TelegramStats, WrappedPayload
from app.wrapped.slides import compute_persona


def _base_payload(**kwargs) -> WrappedPayload:
    defaults = {
        "year": 2025,
        "user_id": 1,
        "display_name": "Test",
        "username": "test",
    }
    defaults.update(kwargs)
    return WrappedPayload(**defaults)


def test_persona_series_devourer():
    p = _base_payload(tv_plays=100, movie_plays=10)
    r = compute_persona(p)
    assert r.persona_id == "series_devourer"
    assert r.persona == "Series Devourer"


def test_persona_curator():
    p = _base_payload(
        total_plays=20,
        telegram=TelegramStats(movies_requested=6, series_requested=6),
    )
    r = compute_persona(p)
    assert r.persona_id == "curator"


def test_persona_dedicated_fallback():
    p = _base_payload(total_plays=5, movie_plays=2, tv_plays=3)
    r = compute_persona(p)
    assert r.persona_id == "dedicated_viewer"


def test_persona_weekend_warrior():
    p = _base_payload(
        plays_by_weekday=[1, 2, 3, 4, 5, 20, 1],
        total_plays=50,
        movie_plays=25,
        tv_plays=25,
    )
    r = compute_persona(p)
    assert r.persona_id == "weekend_warrior"


def test_persona_genre_explorer():
    genres = [GenreStat(name=f"G{i}", plays=1) for i in range(6)]
    p = _base_payload(
        top_movie_genres=genres[:3],
        top_show_genres=genres[3:],
        total_plays=50,
        movie_plays=25,
        tv_plays=25,
    )
    r = compute_persona(p)
    assert r.persona_id == "genre_explorer"
