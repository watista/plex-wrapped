from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


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
        try:
            response = self._client.get(url, params=query)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise TautulliError(f"Tautulli request failed: {exc}") from exc
        except ValueError as exc:
            raise TautulliError("Tautulli returned invalid JSON") from exc
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
        after: str,
        before: str,
        user_id: int | str | None = None,
        start: int = 0,
        length: int = 500,
        grouping: int = 1,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "after": after,
            "before": before,
            "start": start,
            "length": length,
            "grouping": grouping,
            "order_column": "date",
            "order_dir": "desc",
        }
        if user_id is not None:
            params["user_id"] = str(user_id)
        return self._request("get_history", **params)

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

    def get_server_friendly_name(self) -> str | None:
        data = self._request("get_server_friendly_name")
        if isinstance(data, str) and data.strip():
            return data.strip()
        return None

    def get_users_table(
        self,
        *,
        order_column: str = "duration",
        order_dir: str = "desc",
        start: int = 0,
        length: int = 500,
        grouping: int = 1,
    ) -> dict[str, Any]:
        data = self._request(
            "get_users_table",
            order_column=order_column,
            order_dir=order_dir,
            start=str(start),
            length=str(length),
            grouping=str(grouping),
        )
        return data if isinstance(data, dict) else {}

    def get_metadata(self, *, rating_key: int | str) -> dict[str, Any]:
        data = self._request("get_metadata", rating_key=str(rating_key))
        return data if isinstance(data, dict) else {}

    def get_home_stats(
        self,
        *,
        stat_id: str = "top_movies",
        stats_count: int = 1,
        stats_type: str = "plays",
        stats_start: int = 0,
        time_range: int | None = 30,
        after: str | None = None,
        before: str | None = None,
        grouping: int = 1,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "stat_id": stat_id,
            "stats_count": str(stats_count),
            "stats_type": stats_type,
            "stats_start": str(stats_start),
            "grouping": str(grouping),
        }
        if time_range is not None:
            params["time_range"] = str(time_range)
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        data = self._request("get_home_stats", **params)
        return data if isinstance(data, list) else []

    def fetch_all_history(
        self,
        *,
        user_id: int | str,
        after: str,
        before: str,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0
        records_total: int | None = None
        records_filtered: int | None = None
        while True:
            batch = self.get_history(
                user_id=user_id,
                after=after,
                before=before,
                start=start,
                length=page_size,
            )
            if start == 0:
                raw_total = batch.get("recordsTotal")
                raw_filtered = batch.get("recordsFiltered")
                records_total = int(raw_total) if raw_total is not None else None
                records_filtered = int(raw_filtered) if raw_filtered is not None else None
            data = batch.get("data", [])
            if not data:
                break
            rows.extend(data)
            if len(data) < page_size:
                break
            start += page_size
            logger.debug(
                "Tautulli history page user_id=%s offset=%s fetched=%s total_rows=%s",
                user_id,
                start,
                len(data),
                len(rows),
            )
        logger.info(
            "Tautulli history user_id=%s after=%s before=%s recordsTotal=%s "
            "recordsFiltered=%s rows_fetched=%s",
            user_id,
            after,
            before,
            records_total,
            records_filtered,
            len(rows),
        )
        return rows

    def fetch_pms_image(
        self,
        *,
        img: str | None = None,
        rating_key: str | int | None = None,
        refresh: bool = False,
    ) -> httpx.Response:
        """Fetch a poster/image via Tautulli (uses its Plex connection + cache)."""
        params: dict[str, Any] = {
            "apikey": self.api_key,
            "cmd": "pms_image_proxy",
            "img_format": "jpg",
        }
        if img:
            params["img"] = img
        if rating_key is not None:
            params["rating_key"] = str(rating_key)
        if refresh:
            params["refresh"] = "1"
        return self._client.get(f"{self.base_url}/api/v2", params=params, timeout=30.0)

    def fetch_server_history(
        self,
        *,
        after: str,
        before: str,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        """All users' plays in a date range (for server-wide rankings)."""
        rows: list[dict[str, Any]] = []
        start = 0
        records_filtered: int | None = None
        while True:
            batch = self.get_history(
                after=after,
                before=before,
                start=start,
                length=page_size,
            )
            if start == 0:
                raw_filtered = batch.get("recordsFiltered")
                records_filtered = int(raw_filtered) if raw_filtered is not None else None
            data = batch.get("data", [])
            if not data:
                break
            rows.extend(data)
            if len(data) < page_size:
                break
            start += page_size
            logger.debug(
                "Tautulli server history offset=%s fetched=%s total_rows=%s",
                start,
                len(data),
                len(rows),
            )
        logger.info(
            "Tautulli server history after=%s before=%s recordsFiltered=%s rows_fetched=%s",
            after,
            before,
            records_filtered,
            len(rows),
        )
        return rows
