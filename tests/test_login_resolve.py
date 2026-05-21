from app.auth.login_resolve import resolve_login_user_id
from app.auth.plex_oauth import PlexOAuth
from app.config import Settings
from app.models.cache import WrappedCache


class _FakeTautulli:
    def get_users(self):
        raise OSError("should not be called in test mode")


def test_resolve_login_test_mode_by_plex_id(tmp_path):
    settings = Settings(
        use_test_database=True,
        test_database_path=str(tmp_path / "test.db"),
        wrapped_year=2025,
        plex_client_id="test-uuid",
    )
    cache = WrappedCache(settings, database_path=settings.test_database_path)
    cache.set(
        14983182,
        2025,
        {
            "year": 2025,
            "user_id": 14983182,
            "display_name": "Wouter",
            "username": "wouter",
        },
    )
    oauth = PlexOAuth(settings)
    plex_user = {"id": 14983182, "username": "Watista", "email": "test@example.com"}

    user_id = resolve_login_user_id(settings, cache, oauth, plex_user, _FakeTautulli())
    assert user_id == 14983182
