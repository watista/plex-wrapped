from pathlib import Path

import pytest

from app.fixtures.test_wrapped import FIXTURES_DIR, DEFAULT_FIXTURE, load_test_payload, load_test_user_entries
from app.models.schemas import WrappedPayload
from app.utils.json_io import load_json_dict


def test_load_test_payload():
    payload = load_test_payload(user_id=99, year=2025)
    assert payload.user_id == 99
    assert payload.year == 2025
    assert payload.has_watch_history
    assert payload.top_movies
    assert payload.persona_id == "night_owl"


def test_fixture_file_exists():
    assert DEFAULT_FIXTURE.is_file()


@pytest.mark.parametrize(
    "fixture_name,expected",
    [
        ("wrapped_test.json", {"has_watch_history": True, "movie_plays_gt": 0, "tv_plays_gt": 0}),
        ("wrapped_test_films_only.json", {"has_watch_history": True, "movie_plays_gt": 0, "tv_plays_eq": 0}),
        ("wrapped_test_series_only.json", {"has_watch_history": True, "movie_plays_eq": 0, "tv_plays_gt": 0}),
        ("wrapped_test_telegram_only.json", {"has_watch_history": False, "has_telegram_activity": True}),
        ("wrapped_test_no_activity.json", {"has_watch_history": False, "has_telegram_activity": False}),
        ("wrapped_test_light_viewer.json", {"has_watch_history": True, "movie_plays_gt": 0, "tv_plays_gt": 0}),
        ("wrapped_test_mixed_low_completion.json", {"has_watch_history": True, "has_telegram_activity": True}),
        (
            "wrapped_test_no_telegram.json",
            {"has_watch_history": True, "has_telegram_activity": False, "movie_plays_gt": 0, "tv_plays_gt": 0},
        ),
    ],
)
def test_fixture_profiles_validate(fixture_name: str, expected: dict):
    path = FIXTURES_DIR / fixture_name
    assert path.is_file(), f"Missing fixture: {fixture_name}"
    payload = WrappedPayload(**load_json_dict(path))

    if "has_watch_history" in expected:
        assert payload.has_watch_history is expected["has_watch_history"]
    if "has_telegram_activity" in expected:
        assert payload.has_telegram_activity is expected["has_telegram_activity"]
    if expected.get("movie_plays_eq") is not None:
        assert payload.movie_plays == expected["movie_plays_eq"]
    if expected.get("movie_plays_gt") is not None:
        assert payload.movie_plays > 0
    if expected.get("tv_plays_eq") is not None:
        assert payload.tv_plays == expected["tv_plays_eq"]
    if expected.get("tv_plays_gt") is not None:
        assert payload.tv_plays > 0


def test_all_manifest_fixtures_exist_and_load():
    entries = load_test_user_entries()
    assert len(entries) >= 9
    for entry in entries:
        assert entry.fixture.is_file(), f"Fixture missing for user {entry.plex_user_id}: {entry.fixture}"
        payload = load_test_payload(user_id=entry.plex_user_id)
        assert payload.user_id == entry.plex_user_id
        assert payload.display_name == entry.display_name
