from app.wrapped.locale import (
    month_number_to_dutch,
    month_number_to_localized,
    to_dutch_day,
    to_dutch_month,
    to_localized_day,
    to_localized_month,
    weekday_number_to_dutch,
)


def test_to_dutch_month():
    assert to_dutch_month("January") == "januari"
    assert to_dutch_month("December") == "december"
    assert to_dutch_month("Oct") == "oktober"


def test_to_dutch_day():
    assert to_dutch_day("Saturday") == "zaterdag"
    assert to_dutch_day("Monday") == "maandag"
    assert to_dutch_day("Sat") == "zaterdag"


def test_english_month_passthrough():
    assert to_localized_month("March", "english") == "March"
    assert to_localized_day("Friday", "english") == "Friday"


def test_month_short_labels():
    assert to_localized_month("Oct", "dutch", short=True) == "okt"
    assert to_localized_month("October", "english", short=True) == "Oct"


def test_month_and_weekday_numbers():
    assert month_number_to_dutch(10) == "oktober"
    assert weekday_number_to_dutch(5) == "zaterdag"
    assert month_number_to_localized(3, "english") == "March"
