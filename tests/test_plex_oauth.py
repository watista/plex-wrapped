import pytest

from app.auth.plex_oauth import PlexOAuth
from app.config import Settings


@pytest.fixture
def oauth():
    return PlexOAuth(
        Settings(
            plex_client_id="test-client-uuid-1234",
            public_url="http://localhost:8000",
            plex_product="PlexWrappedTest",
        )
    )


def test_callback_url_includes_pin_id(oauth: PlexOAuth):
    url = oauth._callback_url("999")
    assert url == "http://localhost:8000/auth/callback?pin_id=999"


def test_public_origin(oauth: PlexOAuth):
    assert oauth._public_origin() == "http://localhost:8000"


def test_create_pin_auth_url_contains_forward_url(oauth: PlexOAuth, monkeypatch):
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"id": 42, "code": "abcd1234"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, data=None):
            assert headers.get("Origin") == "http://localhost:8000"
            assert data["strong"] == "true"
            return FakeResponse()

    monkeypatch.setattr("app.auth.plex_oauth.httpx.Client", FakeClient)
    pin = oauth.create_pin()
    assert "pin_id=42" in pin["forward_url"]
    assert "forwardUrl=http" in pin["auth_url"] or "forwardUrl=http" in pin["auth_url"].replace("%3A", ":")
