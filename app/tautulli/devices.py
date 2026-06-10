from __future__ import annotations

import logging
from typing import Any

from app.tautulli.client import TautulliClient, TautulliError

logger = logging.getLogger(__name__)


def collect_unique_devices(tautulli: TautulliClient) -> dict[str, Any]:
    """Aggregate unique Plex player names across all Tautulli users."""
    users = tautulli.get_users()
    by_name: dict[str, dict[str, Any]] = {}

    for user in users:
        user_id = user.get("user_id")
        if user_id is None:
            continue
        user_label = (user.get("friendly_name") or user.get("username") or str(user_id)).strip()
        try:
            players = tautulli.get_user_player_stats(user_id=user_id)
        except TautulliError as exc:
            logger.warning("Skipping user_id=%s player stats: %s", user_id, exc)
            continue

        for player in players:
            name = (player.get("player_name") or "").strip()
            if not name:
                continue
            entry = by_name.setdefault(
                name,
                {
                    "name": name,
                    "platform": player.get("platform"),
                    "platform_name": player.get("platform_name"),
                    "total_plays": 0,
                    "users": [],
                },
            )
            entry["total_plays"] += int(player.get("total_plays") or 0)
            if user_label and user_label not in entry["users"]:
                entry["users"].append(user_label)
            if not entry["platform"] and player.get("platform"):
                entry["platform"] = player.get("platform")
            if not entry["platform_name"] and player.get("platform_name"):
                entry["platform_name"] = player.get("platform_name")

    devices = sorted(by_name.values(), key=lambda item: (-item["total_plays"], item["name"].lower()))
    names = [item["name"] for item in devices]
    return {"count": len(devices), "names": names, "devices": devices}
