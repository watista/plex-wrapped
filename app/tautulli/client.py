from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class TautulliError(Exception):
    pass


class TautulliClient:
    def __init__(self, settings: Settings):
        self.base_url = settings.tautulli_url.rstrip("/")
        self.api_key = settings.tautulli_api_key
        self._client = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._client.close()

    def _request(self, cmd: str, **params: Any) -> Any:
        url = f"{self.base_url}/api/v2"
        query = {"apikey": self.api_key, "cmd": cmd, **params}
        response = self._client.get(url, params=query)
        response.raise_for_status()
        payload = response.json()
        if payload.get("response", {}).get("result") != "success":
            message = payload.get("response", {}).get("message", "Unknown Tautulli error")
            raise TautulliError(message)
        return payload.get("response", {}).get("data")

    def get_users(self) -> list[dict[str, Any]]:
        data = self._request("get_users")
        return data if isinstance(data, list) else []

    def get_user(self, user_id: int | str) -> dict[str, Any]:
        return self._request("get_user", user_id=str(user_id))

    def get_history(
        self,
        *,
        user_id: int | str,
        start_date: str,
        end_date: str,
        start: int = 0,
        length: int = 500,
        grouping: int = 1,
    ) -> dict[str, Any]:
        return self._request(
            "get_history",
            user_id=str(user_id),
            start_date=start_date,
            end_date=end_date,
            start=start,
            length=length,
            grouping=grouping,
            order_column="date",
            order_dir="desc",
        )

    def get_plays_by_dayofweek(
        self, *, user_id: int | str, time_range: int, y_axis: str = "duration"
    ) -> dict[str, Any]:
        return self._request(
            "get_plays_by_dayofweek",
            user_id=str(user_id),
            time_range=str(time_range),
            y_axis=y_axis,
        )

    def get_plays_by_hourofday(
        self, *, user_id: int | str, time_range: int, y_axis: str = "duration"
    ) -> dict[str, Any]:
        return self._request(
            "get_plays_by_hourofday",
            user_id=str(user_id),
            time_range=str(time_range),
            y_axis=y_axis,
        )

    def get_plays_per_month(
        self, *, user_id: int | str, time_range: int, y_axis: str = "duration"
    ) -> dict[str, Any]:
        return self._request(
            "get_plays_per_month",
            user_id=str(user_id),
            time_range=str(time_range),
            y_axis=y_axis,
        )

    def get_user_player_stats(self, *, user_id: int | str, grouping: int = 1) -> list[dict[str, Any]]:
        data = self._request("get_user_player_stats", user_id=str(user_id), grouping=grouping)
        return data if isinstance(data, list) else []

    def get_plays_by_stream_type(
        self, *, user_id: int | str, time_range: int, y_axis: str = "duration"
    ) -> dict[str, Any]:
        return self._request(
            "get_plays_by_stream_type",
            user_id=str(user_id),
            time_range=str(time_range),
            y_axis=y_axis,
        )

    def get_plays_by_top_10_users(self, *, time_range: int, y_axis: str = "duration") -> dict[str, Any]:
        return self._request(
            "get_plays_by_top_10_users",
            time_range=str(time_range),
            y_axis=y_axis,
        )

    def get_metadata(self, *, rating_key: int | str) -> dict[str, Any]:
        data = self._request("get_metadata", rating_key=str(rating_key))
        return data if isinstance(data, dict) else {}

    def get_home_stats(
        self,
        *,
        time_range: int,
        stat_id: str = "top_movies",
        stats_count: int = 1,
    ) -> list[dict[str, Any]]:
        data = self._request(
            "get_home_stats",
            time_range=str(time_range),
            stat_id=stat_id,
            stats_count=str(stats_count),
        )
        return data if isinstance(data, list) else []

    def fetch_all_history(
        self,
        *,
        user_id: int | str,
        start_date: str,
        end_date: str,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            batch = self.get_history(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                start=start,
                length=page_size,
            )
            data = batch.get("data", [])
            if not data:
                break
            rows.extend(data)
            if len(data) < page_size:
                break
            start += page_size
        return rows
