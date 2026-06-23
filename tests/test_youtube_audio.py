from pathlib import Path
from unittest.mock import patch

from app.wrapped.theme_lookup import ThemeSearchPlan, YoutubeQuery
from app.wrapped.youtube_audio import (
    api_audio_url,
    find_cached_by_key,
    is_valid_video_id,
    resolve_genre_theme_audio,
    resolve_media_theme_audio,
    search_best_video_id,
)


def test_is_valid_video_id():
    assert is_valid_video_id("dQw4w9WgXcQ")
    assert not is_valid_video_id("../etc/passwd")


def test_api_audio_url(tmp_path: Path):
    path = tmp_path / "abc123.m4a"
    path.write_bytes(b"x" * 9000)
    assert api_audio_url(path) == "/api/audio/abc123.m4a"


def test_find_cached_by_key(tmp_path: Path):
    path = tmp_path / "v3_movie_avengers_2012.m4a"
    path.write_bytes(b"x" * 9000)
    found = find_cached_by_key(tmp_path, "v3_movie_avengers_2012")
    assert found == path


@patch("app.wrapped.youtube_audio._try_plan_queries")
@patch("app.wrapped.youtube_audio.build_youtube_search_plan")
def test_resolve_media_theme_audio(mock_plan, mock_try, tmp_path: Path):
    mock_plan.return_value = ThemeSearchPlan(queries=[], track=None, media_title="The Avengers")
    mock_try.return_value = "/api/audio/v3_movie_the_avengers_2012.m4a"

    url = resolve_media_theme_audio(
        "The Avengers",
        tmp_path,
        year=2012,
        media_kind="movie",
        download=True,
    )
    assert url == "/api/audio/v3_movie_the_avengers_2012.m4a"


@patch("app.wrapped.youtube_audio._try_plan_queries", return_value=None)
def test_resolve_genre_theme_audio(_mock_try, tmp_path: Path):
    assert resolve_genre_theme_audio("drama", tmp_path, download=True) is None


@patch("app.wrapped.youtube_audio.subprocess.run")
def test_search_rejects_below_min_score(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "abc123XYZ\tRandom mix\t120\n"
    yt_query = YoutubeQuery(
        text="test",
        min_score=999,
        require_track_match=False,
        require_media_overlap=False,
    )
    assert search_best_video_id(yt_query, media_title="test", theme_track=None) is None
