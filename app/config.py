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
    wrapped_test_fixture_path: str = "data/fixtures/wrapped_test.json"

    plex_server_url: str = ""
    plex_server_token: str = ""

    def resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
