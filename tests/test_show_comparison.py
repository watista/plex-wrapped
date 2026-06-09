from app.wrapped.aggregator import _build_comparison_caption, _comparison_headline_accent


def test_comparison_caption_same_show():
    caption = _build_comparison_caption(
        "Breaking Bad",
        "Breaking Bad",
        same_show=True,
        reason="most_played",
    )
    assert "Breaking Bad" in caption
    assert "Great minds" in caption


def test_comparison_caption_different_most_played():
    caption = _build_comparison_caption(
        "The Office",
        "Breaking Bad",
        same_show=False,
        reason="most_played",
    )
    assert "The Office" in caption
    assert "Breaking Bad" in caption
    assert "nummer één" in caption


def test_comparison_caption_first_played():
    caption = _build_comparison_caption(
        "The Office",
        "Succession",
        same_show=False,
        reason="first_played",
    )
    assert "startte jij het jaar" in caption


def test_comparison_headline_accent_is_deterministic():
    a = _comparison_headline_accent("The Bear", "Succession")
    b = _comparison_headline_accent("The Bear", "Succession")
    assert a == b
    assert a in ("eigenzinnige", "verfijnde", "unieke", "eigen")
