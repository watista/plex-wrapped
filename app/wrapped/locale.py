"""Map Tautulli chart labels and numeric indices to localized month/day names."""

from __future__ import annotations

from app.i18n import chart_label_index, get_translator, load_chart_labels, normalize_language


def _localized_from_chart_label(
    label: str | None,
    *,
    language: str | None,
    list_key: str,
    short_list_key: str,
    chart_keys: tuple[str, ...],
    short: bool = False,
) -> str | None:
    if not label:
        return None

    stripped = label.strip()
    lang = normalize_language(language)
    charts = load_chart_labels()

    index = chart_label_index(stripped, *chart_keys)
    if index is None:
        return stripped

    if lang == "english":
        if chart_keys[0] == "months":
            chart_key = "months_short" if short else "months"
        else:
            chart_key = "weekdays_short" if short else "weekdays"
        return charts[chart_key][index]

    value_key = short_list_key if short else list_key
    values = get_translator(lang).list_values(value_key)
    if index < len(values):
        return values[index]
    return stripped


def to_localized_month(label: str | None, language: str | None = None, *, short: bool = False) -> str | None:
    return _localized_from_chart_label(
        label,
        language=language,
        list_key="locale.months",
        short_list_key="locale.months_short",
        chart_keys=("months", "months_short"),
        short=short,
    )


def to_localized_day(label: str | None, language: str | None = None, *, short: bool = False) -> str | None:
    return _localized_from_chart_label(
        label,
        language=language,
        list_key="locale.weekdays",
        short_list_key="locale.weekdays_short",
        chart_keys=("weekdays", "weekdays_short"),
        short=short,
    )


def month_number_to_localized(month: int | None, language: str | None = None, *, short: bool = False) -> str | None:
    if month is None:
        return None
    key = "locale.months_short" if short else "locale.months"
    months = get_translator(language or "english").list_values(key)
    idx = month - 1
    if 0 <= idx < len(months):
        return months[idx]
    return None


def weekday_number_to_localized(weekday: int | None, language: str | None = None) -> str | None:
    if weekday is None or weekday < 0 or weekday > 6:
        return None
    weekdays = get_translator(language or "english").list_values("locale.weekdays")
    if 0 <= weekday < len(weekdays):
        return weekdays[weekday]
    return None


# Backwards-compatible aliases.
def to_dutch_month(label: str | None) -> str | None:
    return to_localized_month(label, "dutch")


def to_dutch_day(label: str | None) -> str | None:
    return to_localized_day(label, "dutch")


def month_number_to_dutch(month: int | None) -> str | None:
    return month_number_to_localized(month, "dutch")


def weekday_number_to_dutch(weekday: int | None) -> str | None:
    return weekday_number_to_localized(weekday, "dutch")
