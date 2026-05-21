from app.wrapped.locale import to_dutch_day, to_dutch_month


def test_to_dutch_month():
    assert to_dutch_month("January") == "januari"
    assert to_dutch_month("December") == "december"


def test_to_dutch_day():
    assert to_dutch_day("Saturday") == "zaterdag"
    assert to_dutch_day("Monday") == "maandag"
