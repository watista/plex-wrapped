"""Map Tautulli chart labels to Dutch for cached display values."""

from __future__ import annotations

MONTH_EN_TO_NL: dict[str, str] = {
    "January": "januari",
    "February": "februari",
    "March": "maart",
    "April": "april",
    "May": "mei",
    "June": "juni",
    "July": "juli",
    "August": "augustus",
    "September": "september",
    "October": "oktober",
    "November": "november",
    "December": "december",
    "Jan": "jan",
    "Feb": "feb",
    "Mar": "mrt",
    "Apr": "apr",
    "Jun": "jun",
    "Jul": "jul",
    "Aug": "aug",
    "Sep": "sep",
    "Oct": "okt",
    "Nov": "nov",
    "Dec": "dec",
}

DAY_EN_TO_NL: dict[str, str] = {
    "Monday": "maandag",
    "Tuesday": "dinsdag",
    "Wednesday": "woensdag",
    "Thursday": "donderdag",
    "Friday": "vrijdag",
    "Saturday": "zaterdag",
    "Sunday": "zondag",
    "Mon": "ma",
    "Tue": "di",
    "Wed": "wo",
    "Thu": "do",
    "Fri": "vr",
    "Sat": "za",
    "Sun": "zo",
}


def to_dutch_month(label: str | None) -> str | None:
    if not label:
        return None
    stripped = label.strip()
    return MONTH_EN_TO_NL.get(stripped, stripped.lower())


def to_dutch_day(label: str | None) -> str | None:
    if not label:
        return None
    stripped = label.strip()
    return DAY_EN_TO_NL.get(stripped, stripped.lower())
