from app.i18n import (
    Translator,
    available_languages,
    get_translator,
    localize_wrapped_payload,
    normalize_language,
    position_label,
)


def test_language_aliases():
    assert normalize_language("fr") == "french"
    assert normalize_language("deutsch") == "german"
    assert normalize_language("polski") == "polish"
    assert normalize_language("español") == "spanish"
    assert normalize_language("magyar") == "hungarian"


def test_available_languages():
    langs = available_languages()
    assert "english" in langs
    assert "dutch" in langs
    assert "chart_labels" not in langs


def test_default_language_is_english():
    tr = get_translator()
    assert tr.language == "english"
    assert tr.t("login.sign_in") == "Sign in with Plex"


def test_dutch_translation_locale_arrays():
    tr = get_translator("dutch")
    assert tr.list_values("locale.months_short")[9] == "okt"
    assert len(tr.list_values("locale.months_short")) == 12


def test_dutch_translation():
    tr = get_translator("dutch")
    assert tr.t("login.sign_in") == "Inloggen met Plex"
    assert tr.html_lang() == "nl"


def test_interpolation():
    tr = get_translator("english")
    assert tr.t("wrapped.welcome.greeting", name="Alex") == "Hi Alex!"


def test_position_label_plural():
    tr = get_translator("english")
    assert position_label(tr, -3) == "3 spots higher"
    tr_nl = get_translator("dutch")
    assert position_label(tr_nl, 2) == "2 plekken lager"


def test_localize_wrapped_payload_persona():
    tr = get_translator("english")
    data = {
        "persona_id": "film_buff",
        "persona": "Filmliefhebber",
        "persona_tagline": "oud",
        "busiest_month_index": 10,
        "plays_by_weekday": [1, 2, 3, 4, 5, 20, 1],
    }
    localize_wrapped_payload(data, tr)
    assert data["persona"] == "Film Buff"
    assert data["busiest_month"] == "October"
    assert data["peak_day"] == "Saturday"
