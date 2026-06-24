from __future__ import annotations

from dataclasses import dataclass

from app.i18n import Translator, get_translator
from app.models.schemas import WrappedPayload


@dataclass(frozen=True)
class PersonaResult:
    persona_id: str
    persona: str
    persona_tagline: str


def _genre_count(payload: WrappedPayload) -> int:
    names: set[str] = set()
    for g in payload.top_movie_genres + payload.top_show_genres:
        names.add(g.name.lower())
    return len(names)


def _peak_weekday_index(payload: WrappedPayload) -> int | None:
    plays = payload.plays_by_weekday
    if not plays:
        return None
    return max(range(7), key=lambda i: int(plays[i]) if i < len(plays) else 0)


def compute_persona_id(payload: WrappedPayload) -> str:
    tg = payload.telegram
    requests_total = tg.movies_requested + tg.series_requested

    if requests_total >= 10 and payload.total_plays > 0 and requests_total > payload.total_plays * 0.3:
        return "curator"
    if payload.watch_hours >= 300:
        return "marathon_runner"
    if payload.unique_series >= 20:
        return "completionist"
    if payload.peak_hour is not None and payload.peak_hour >= 23:
        return "night_owl"
    if payload.peak_hour is not None and payload.peak_hour <= 10:
        return "early_bird"
    if payload.tv_plays > payload.movie_plays * 2:
        return "series_devourer"
    if payload.movie_plays > payload.tv_plays * 2:
        return "film_buff"
    if payload.longest_streak_days >= 12:
        return "binge_royalty"
    if _genre_count(payload) >= 6:
        return "genre_explorer"
    peak_weekday = _peak_weekday_index(payload)
    if peak_weekday in (5, 6):
        return "weekend_warrior"
    if payload.top_movies and payload.top_movies[0].plays >= 3:
        return "loyal_rewatcher"
    return "dedicated_viewer"


def compute_persona(payload: WrappedPayload, translator: Translator | None = None) -> PersonaResult:
    tr = translator or get_translator()
    persona_id = compute_persona_id(payload)
    return PersonaResult(
        persona_id,
        tr.t(f"persona.{persona_id}.name"),
        tr.t(f"persona.{persona_id}.tagline"),
    )


def apply_persona(payload: WrappedPayload, translator: Translator | None = None) -> None:
    result = compute_persona(payload, translator)
    payload.persona_id = result.persona_id
    payload.persona = result.persona
    payload.persona_tagline = result.persona_tagline
