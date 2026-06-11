from app.config import Settings
from app.tautulli.client import TautulliClient


def test_get_history_uses_after_before_not_start_date():
    client = TautulliClient(Settings(tautulli_url="http://tautulli.test", tautulli_api_key="key"))
    captured: dict = {}

    def fake_request(cmd: str, **params):
        captured["cmd"] = cmd
        captured["params"] = params
        return {
            "recordsTotal": 2,
            "recordsFiltered": 2,
            "data": [{"media_type": "movie", "date": 1735689600}],
        }

    client._request = fake_request  # type: ignore[method-assign]

    result = client.get_history(
        user_id=14983182,
        after="2025-01-01",
        before="2025-12-31",
        start=0,
        length=500,
    )

    assert result["recordsFiltered"] == 2
    assert captured["cmd"] == "get_history"
    assert captured["params"]["after"] == "2025-01-01"
    assert captured["params"]["before"] == "2025-12-31"
    assert "start_date" not in captured["params"]
    assert "end_date" not in captured["params"]


def test_fetch_all_history_paginates():
    client = TautulliClient(Settings(tautulli_url="http://tautulli.test", tautulli_api_key="key"))
    calls: list[int] = []

    def fake_get_history(**kwargs):
        start = kwargs["start"]
        calls.append(start)
        if start == 0:
            return {
                "recordsTotal": 3,
                "recordsFiltered": 3,
                "data": [{"media_type": "movie"}, {"media_type": "episode"}],
            }
        return {"recordsTotal": 3, "recordsFiltered": 3, "data": [{"media_type": "movie"}]}

    client.get_history = fake_get_history  # type: ignore[method-assign]

    rows = client.fetch_all_history(
        user_id=1,
        after="2025-01-01",
        before="2025-12-31",
        page_size=2,
    )

    assert calls == [0, 2]
    assert len(rows) == 3
