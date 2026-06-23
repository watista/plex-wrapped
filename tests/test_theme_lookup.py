from unittest.mock import patch

from app.wrapped.theme_lookup import (
    ThemeTrack,
    build_youtube_search_plan,
    score_youtube_candidate,
)


def test_score_youtube_penalizes_bhojpuri():
    score = score_youtube_candidate(
        video_title="Avengers bhojpuri song remix",
        duration=180,
        media_title="The Avengers",
        theme_track=None,
    )
    assert score < 0


def test_score_youtube_strict_requires_track_or_artist():
    track = ThemeTrack(
        track_name="The Avengers",
        artist_name="Alan Silvestri",
        album_name="The Avengers OST",
        source="spotify",
    )
    good = score_youtube_candidate(
        video_title="The Avengers - Alan Silvestri | Official Soundtrack",
        duration=120,
        media_title="The Avengers",
        theme_track=track,
        require_track_match=True,
    )
    bad = score_youtube_candidate(
        video_title="Random Indian music mix",
        duration=120,
        media_title="The Avengers",
        theme_track=track,
        require_track_match=True,
    )
    assert good > bad
    assert bad < 0


@patch("app.wrapped.theme_lookup.lookup_theme_track")
def test_build_youtube_search_plan_uses_track_queries(mock_lookup):
    mock_lookup.return_value = ThemeTrack(
        track_name="Cornfield Chase",
        artist_name="Hans Zimmer",
        album_name="Interstellar OST",
        source="spotify",
    )
    plan = build_youtube_search_plan("Interstellar", year=2014, media_kind="movie", settings=None)
    assert plan.track is not None
    assert plan.queries[0].require_track_match is True
    assert "Hans Zimmer" in plan.queries[0].text
