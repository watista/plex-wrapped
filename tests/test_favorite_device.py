from app.wrapped.aggregator import WrappedAggregator


def test_favorite_device_watch_percent_from_history(monkeypatch):
    monkeypatch.setattr(
        WrappedAggregator,
        "compute",
        lambda self, user_id: None,
    )

    media_history = [
        {"media_type": "movie", "duration": 3600, "player": "Apple TV", "date": 1735689600},
        {"media_type": "episode", "duration": 1800, "player": "Apple TV", "date": 1735776000},
        {"media_type": "movie", "duration": 1800, "player": "iPhone", "date": 1735862400},
    ]

    player_durations: dict[str, int] = {}
    total_seconds = 0
    for row in media_history:
        duration = int(row.get("duration") or 0)
        total_seconds += duration
        player = row.get("player")
        if player:
            player_durations[player] = player_durations.get(player, 0) + duration

    favorite_device, favorite_duration = max(
        player_durations.items(), key=lambda item: item[1]
    )
    percent = int(round(favorite_duration / total_seconds * 100))

    assert favorite_device == "Apple TV"
    assert favorite_duration == 5400
    assert percent == 75
