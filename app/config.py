from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Plex Wrapped"
    public_url: str = "http://localhost:8000"
    secret_key: str = "dev-secret-change-in-production"
    wrapped_year: int = 2025
    session_max_age: int = 604800

    tautulli_url: str = "http://localhost:8181"
    tautulli_api_key: str = ""

    plex_client_id: str = ""
    plex_product: str = "PlexWrapped"

    admin_secret: str = ""
    share_link_secret: str = ""
    share_link_expiry_days: int = 90

    user_mapping_path: str = "config/user_mapping.json"
    telegram_requests_path: str = "data/telegram_requests.json"
    database_path: str = "data/wrapped.db"
    test_database_path: str = "data/wrapped_test.db"
    use_test_database: bool = False
    wrapped_test_fixture_path: str = "data/fixtures/wrapped_test.json"
    wrapped_test_users_path: str = "data/fixtures/test_users.json"

    log_level: str = "INFO"

    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    google_analytics_id: str = ""

    plex_server_url: str = ""
    plex_server_token: str = ""

    tmdb_api_key: str = ""

    # Background music (downloaded at compute time via yt-dlp + ffmpeg).
    music_enabled: bool = True
    music_download_enabled: bool = True
    audio_cache_path: str = "data/audio/cache"
    # Optional path to ffmpeg binary or its directory (for yt-dlp mp3 conversion).
    music_overrides_path: str = "config/music_overrides.json"
    ffmpeg_location: str = ""

    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # Cursor AI (used to generate dynamic copy when computing wrapped data).
    # Uses the Cursor Python SDK with the local runtime, so the `cursor-agent`
    # runtime must be installed on the machine that runs the compute step.
    cursor_ai_enabled: bool = False
    cursor_api_key: str = ""
    cursor_model: str = "auto"
    cursor_timeout_seconds: int = 120
    # Working directory the local agent runs against. Empty -> project root.
    cursor_agent_cwd: str = ""

    def resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p

    def active_database_path(self) -> str:
        if self.use_test_database:
            return self.test_database_path
        return self.database_path


@lru_cache
def get_settings() -> Settings:
    return Settings()
