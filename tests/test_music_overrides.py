from pathlib import Path
from unittest.mock import patch

from app.config import Settings
from app.wrapped.music_overrides import (
    get_override_video_id,
    match_music_override,
    override_cache_key,
)
from app.wrapped.theme_lookup import cache_key
from app.wrapped.youtube_audio import (
    api_audio_url,
    find_cached_by_key,
    parse_youtube_video_id,
    resolve_media_theme_audio,
)


def test_parse_youtube_video_id():
    assert parse_youtube_video_id("AdQ3JDLlmPI") == "AdQ3JDLlmPI"
    assert (
        parse_youtube_video_id("https://www.youtube.com/watch?v=AdQ3JDLlmPI")
        == "AdQ3JDLlmPI"
    )
    assert parse_youtube_video_id("not-a-url") is None


def test_override_missing_file():
    settings = Settings(music_overrides_path="config/does_not_exist.json")
    assert get_override_video_id(settings, "Game of Thrones", "show") is None


def test_override_game_of_thrones_file(tmp_path: Path):
    overrides = tmp_path / "music_overrides.json"
    overrides.write_text(
        '{"shows": {"Game of Thrones": "https://www.youtube.com/watch?v=AdQ3JDLlmPI"}}',
        encoding="utf-8",
    )
    settings = Settings(music_overrides_path=str(overrides))
    assert get_override_video_id(settings, "Game of Thrones", "show") == "AdQ3JDLlmPI"
    assert get_override_video_id(settings, "game of thrones", "show") == "AdQ3JDLlmPI"
    assert get_override_video_id(settings, "Game of Thrones (2011)", "show") == "AdQ3JDLlmPI"
    assert get_override_video_id(settings, "Game of Thrones - Season 1", "show") == "AdQ3JDLlmPI"
    assert get_override_video_id(settings, "Game of Thrones", "movie") is None
    assert override_cache_key("game of thrones", "show").startswith("v3_override_show_")
    matched = match_music_override(settings, "Game of Thrones (2011)", "show")
    assert matched == ("AdQ3JDLlmPI", "game of thrones")


def test_resolve_media_theme_audio_uses_override_not_stale_cache(tmp_path: Path):
    overrides = tmp_path / "music_overrides.json"
    overrides.write_text(
        '{"shows": {"Game of Thrones": "https://www.youtube.com/watch?v=AdQ3JDLlmPI"}}',
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    stale_key = cache_key("Game of Thrones (2011)", year=2025, media_kind="show")
    wrong = cache_dir / f"{stale_key}.m4a"
    wrong.write_bytes(b"x" * 9000)
    override = cache_dir / "v3_override_show_game_of_thrones.m4a"
    override.write_bytes(b"y" * 9000)

    settings = Settings(music_overrides_path=str(overrides))
    url = resolve_media_theme_audio(
        "Game of Thrones (2011)",
        cache_dir,
        year=2025,
        media_kind="show",
        download=True,
        settings=settings,
    )
    assert url == api_audio_url(override)
    assert url != api_audio_url(wrong)


@patch("app.wrapped.youtube_audio.download_audio")
def test_resolve_media_theme_audio_override_blocks_search_when_download_fails(
    mock_download, tmp_path: Path
):
    overrides = tmp_path / "music_overrides.json"
    overrides.write_text(
        '{"shows": {"Game of Thrones": "https://www.youtube.com/watch?v=AdQ3JDLlmPI"}}',
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    stale_key = cache_key("Game of Thrones", year=2025, media_kind="show")
    wrong = cache_dir / f"{stale_key}.m4a"
    wrong.write_bytes(b"x" * 9000)
    mock_download.return_value = None

    settings = Settings(music_overrides_path=str(overrides))
    url = resolve_media_theme_audio(
        "Game of Thrones",
        cache_dir,
        year=2025,
        media_kind="show",
        download=True,
        settings=settings,
    )
    assert url is None
    assert find_cached_by_key(cache_dir, stale_key) == wrong
