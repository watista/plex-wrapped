from app.wrapped.aggregator import _compute_server_stats


def _users_table(rows: list[dict], total: int | None = None) -> dict:
    return {
        "recordsTotal": total if total is not None else len(rows),
        "data": rows,
    }


def test_compute_server_stats_rank_context_and_percent():
    table = _users_table(
        [
            {"user_id": 10, "friendly_name": "Alpha", "duration": 4_464_000},
            {"user_id": 20, "friendly_name": "Bravo", "duration": 3_542_400},
            {"user_id": 1, "friendly_name": "Alex (test)", "username": "alex_test", "duration": 2_987_520},
            {"user_id": 30, "friendly_name": "Charlie", "duration": 2_505_600},
            {"user_id": 40, "friendly_name": "Delta", "duration": 1_800_000},
        ],
        total=12,
    )

    stats = _compute_server_stats(
        user_id=1,
        display_name="Alex (test)",
        username="alex_test",
        user_watch_seconds=2_987_520,
        users_table=table,
        top_users=None,
    )

    assert stats.rank == 3
    assert stats.more_active_than_percent == 75
    assert len(stats.rank_context) == 3
    assert stats.rank_context[0].rank == 2
    assert stats.rank_context[0].position_label == "Eén plek hoger"
    assert stats.rank_context[0].watch_hours == 984
    assert stats.rank_context[1].is_you
    assert stats.rank_context[1].watch_hours == 830
    assert stats.rank_context[2].rank == 4
    assert stats.rank_context[2].position_label == "Eén plek lager"


def test_compute_server_stats_top10_fallback():
    top_users = {
        "categories": ["Alpha", "Alex (test)", "Charlie"],
        "series": [
            {"name": "Movies", "data": [1000, 800, 400]},
            {"name": "TV", "data": [2000, 1500, 900]},
        ],
    }

    stats = _compute_server_stats(
        user_id=99,
        display_name="Alex (test)",
        username="alex_test",
        user_watch_seconds=2300,
        users_table=None,
        top_users=top_users,
    )

    assert stats.rank == 2
    assert stats.more_active_than_percent == 33
    assert [entry.rank for entry in stats.rank_context] == [1, 2, 3]


def test_compute_server_stats_edge_rank_one():
    table = _users_table(
        [
            {"user_id": 1, "friendly_name": "Alex", "duration": 3_600_000},
            {"user_id": 2, "friendly_name": "Beta", "duration": 1_800_000},
        ]
    )

    stats = _compute_server_stats(
        user_id=1,
        display_name="Alex",
        username="alex",
        user_watch_seconds=3_600_000,
        users_table=table,
        top_users=None,
    )

    assert stats.rank == 1
    assert stats.more_active_than_percent == 50
    assert len(stats.rank_context) == 2
    assert stats.rank_context[0].is_you
    assert stats.rank_context[1].position_label == "Eén plek lager"
