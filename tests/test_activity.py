import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.activity.logger import ActivityLogger
from app.activity.schemas import ActivityEventBody
from app.activity.service import ActivityService
from app.activity.telegram import TelegramNotifier
from app.auth.plex_oauth import set_session_user_id
from app.config import Settings
from app.main import app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        secret_key="test-secret",
        database_path=str(tmp_path / "wrapped.db"),
        telegram_bot_token="bot123",
        telegram_channel_id="-100999",
    )


def test_activity_logger_tags_username(caplog):
    logger = ActivityLogger()
    with caplog.at_level("INFO", logger="plex.wrapped.activity"):
        logger.log("plexuser", "slide_view", slide_id="welcome", slide_index=0)
    assert "user=plexuser" in caplog.text
    assert "event=slide_view" in caplog.text
    assert "slide_id=welcome" in caplog.text


def test_telegram_notifier_skips_when_unconfigured(settings):
    settings.telegram_bot_token = ""
    notifier = TelegramNotifier(settings)
    assert notifier.enabled is False


@patch("app.activity.telegram.httpx.Client")
def test_telegram_send_login(mock_client_cls, settings):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    notifier = TelegramNotifier(settings)
    notifier.send_login_notification(
        username="plexuser",
        display_name="Plex User",
        login_method="login_portal",
        year=2025,
        user_id=42,
    )

    mock_client.post.assert_called_once()
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["chat_id"] == "-100999"
    assert "plexuser" in payload["text"]
    assert "Login portal" in payload["text"]


def test_activity_service_record_client_event(settings, tmp_path):
    from app.models.cache import WrappedCache

    cache = WrappedCache(settings, database_path=str(tmp_path / "wrapped.db"))
    cache.set(
        1,
        2025,
        {
            "year": 2025,
            "user_id": 1,
            "display_name": "Test User",
            "username": "testuser",
            "has_watch_history": True,
            "total_plays": 1,
        },
    )

    activity_logger = MagicMock(spec=ActivityLogger)
    service = ActivityService(settings, cache, logger=activity_logger, telegram=MagicMock())

    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "pytest"}
    request.cookies = {}

    body = ActivityEventBody(event="slide_view", slide_id="welcome", slide_index=0, slide_count=5)
    service.record_client_event(request, 1, body)

    activity_logger.log.assert_called_once()
    args, kwargs = activity_logger.log.call_args
    assert args[0] == "testuser"
    assert args[1] == "slide_view"
    assert kwargs["slide_id"] == "welcome"


def test_api_activity_requires_auth():
    client = TestClient(app)
    response = client.post(
        "/api/activity",
        json={"event": "slide_view", "slide_id": "welcome", "slide_index": 0},
    )
    assert response.status_code == 401


def test_session_stores_username(settings):
    from starlette.responses import Response

    response = Response()
    set_session_user_id(response, 7, settings, username="plexuser")
    cookie = response.headers.get("set-cookie", "")
    assert "wrapped_session=" in cookie
