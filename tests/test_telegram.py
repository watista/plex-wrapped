from app.telegram.loader import (
    count_unique_matched,
    match_requests_to_history,
    normalize_title,
    parse_telegram_date,
)


def test_parse_telegram_date():
    dt = parse_telegram_date("23-01-2025 15:35:49")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 1
    assert dt.day == 23


def test_parse_invalid_date():
    assert parse_telegram_date("not-a-date") is None


def test_match_requests():
    matched = match_requests_to_history(
        ["The Matrix"],
        ["30 Rock"],
        ["30 Rock", "Something Else"],
    )
    assert "30 Rock" in matched


def test_count_unique_matched():
    assert count_unique_matched(["The Matrix", "The Matrix"], ["The Matrix Reloaded"]) == 0
    assert count_unique_matched(["30 Rock", "Other Show"], ["30 Rock", "Something"]) == 1
