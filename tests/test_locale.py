from app.wrapped.locale import month_number_to_dutch, to_dutch_day, to_dutch_month, weekday_number_to_dutch


def test_to_dutch_month():
    assert to_dutch_month("January") == "januari"
    assert to_dutch_month("December") == "december"


def test_to_dutch_day():
    assert to_dutch_day("Saturday") == "zaterdag"
    assert to_dutch_day("Monday") == "maandag"


def test_month_and_weekday_numbers():
    assert month_number_to_dutch(10) == "oktober"
    assert weekday_number_to_dutch(5) == "zaterdag"
