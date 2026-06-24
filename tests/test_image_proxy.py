from unittest.mock import MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app


@patch("app.main.httpx.Client")
def test_external_image_proxy_returns_tmdb_image(mock_client_cls):
    mock_client = MagicMock()
    mock_response = httpx.Response(
        200,
        content=b"fake-jpeg",
        headers={"content-type": "image/jpeg"},
        request=httpx.Request("GET", "https://image.tmdb.org/t/p/w500/test.jpg"),
    )
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    client = TestClient(app)
    url = "https://image.tmdb.org/t/p/w500/test.jpg"
    response = client.get("/api/image", params={"url": url})

    assert response.status_code == 200
    assert response.content == b"fake-jpeg"
    assert response.headers["content-type"] == "image/jpeg"
    mock_client.get.assert_called_once_with(url)


def test_external_image_proxy_rejects_unknown_host():
    client = TestClient(app)
    response = client.get("/api/image", params={"url": "https://evil.example/poster.jpg"})
    assert response.status_code == 403


def test_external_image_proxy_rejects_invalid_scheme():
    client = TestClient(app)
    response = client.get("/api/image", params={"url": "ftp://image.tmdb.org/poster.jpg"})
    assert response.status_code == 400
