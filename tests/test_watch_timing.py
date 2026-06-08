from datetime import datetime, timezone

from app.wrapped.aggregator import _compute_watch_timing


def _row(ts: int) -> dict:
    return {"date": ts, "media_type": "episode"}


def test_compute_watch_timing_busiest_month_calendar():
    year = 2025
    history = [
        _row(int(datetime(2025, 10, 1, 12, tzinfo=timezone.utc).timestamp())),
        _row(int(datetime(2025, 10, 3, 12, tzinfo=timezone.utc).timestamp())),
        _row(int(datetime(2025, 10, 3, 18, tzinfo=timezone.utc).timestamp())),
        _row(int(datetime(2025, 3, 15, 12, tzinfo=timezone.utc).timestamp())),
    ]

    result = _compute_watch_timing(history, year)

    assert result["busiest_month"] == "oktober"
    assert result["busiest_month_index"] == 10
    assert result["busiest_month_first_weekday"] == 2
    assert len(result["busiest_month_daily_plays"]) == 31
    assert result["busiest_month_daily_plays"][0] == 1
    assert result["busiest_month_daily_plays"][1] == 0
    assert result["busiest_month_daily_plays"][2] == 2


def test_compute_watch_timing_weekday_counts():
    year = 2025
    saturday = int(datetime(2025, 10, 4, 20, tzinfo=timezone.utc).timestamp())
    sunday = int(datetime(2025, 10, 5, 20, tzinfo=timezone.utc).timestamp())
    friday = int(datetime(2025, 10, 3, 20, tzinfo=timezone.utc).timestamp())

    result = _compute_watch_timing(
        [_row(saturday), _row(saturday), _row(sunday), _row(friday)],
        year,
    )

    assert result["plays_by_weekday"] == [0, 0, 0, 0, 1, 2, 1]
    assert result["peak_day"] == "zaterdag"
