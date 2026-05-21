from pathlib import Path

from app.fixtures.test_wrapped import load_test_payload


def test_load_test_payload():
    payload = load_test_payload(user_id=99, year=2025)
    assert payload.user_id == 99
    assert payload.year == 2025
    assert payload.has_watch_history
    assert payload.top_movies
    assert payload.persona_id == "night_owl"


def test_fixture_file_exists():
    from app.fixtures.test_wrapped import DEFAULT_FIXTURE

    assert DEFAULT_FIXTURE.is_file()
