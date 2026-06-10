import httpx
import pytest

from app.tautulli.client import TautulliClient, TautulliError


def test_tautulli_connect_error_wrapped_as_tautulli_error(monkeypatch):
    client = TautulliClient.__new__(TautulliClient)
    client.base_url = "http://127.0.0.1:1"
    client.api_key = "test"
    client._client = httpx.Client(timeout=1.0)

    def raise_connect(*_args, **_kwargs):
        raise httpx.ConnectError("Connection refused", request=httpx.Request("GET", "http://127.0.0.1:1"))

    monkeypatch.setattr(client._client, "get", raise_connect)

    with pytest.raises(TautulliError, match="Tautulli request failed"):
        client.get_users()

    client._client.close()
