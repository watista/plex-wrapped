from __future__ import annotations

import random
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


def matching_persona_ids(payload: WrappedPayload) -> list[str]:
    """Every persona whose criteria the payload satisfies (empty if none match)."""
    tg = payload.telegram
    requests_total = tg.movies_requested + tg.series_requested
    peak_weekday = _peak_weekday_index(payload)

    matches: list[str] = []
    if requests_total >= 10 and payload.total_plays > 0 and requests_total > payload.total_plays * 0.3:
        matches.append("curator")
    if payload.watch_hours >= 300:
        matches.append("marathon_runner")
    if payload.unique_series >= 20:
        matches.append("completionist")
    if payload.peak_hour is not None and payload.peak_hour >= 23:
        matches.append("night_owl")
    if payload.peak_hour is not None and payload.peak_hour <= 10:
        matches.append("early_bird")
    if payload.tv_plays > payload.movie_plays * 2:
        matches.append("series_devourer")
    if payload.movie_plays > payload.tv_plays * 2:
        matches.append("film_buff")
    if payload.longest_streak_days >= 12:
        matches.append("binge_royalty")
    if _genre_count(payload) >= 6:
        matches.append("genre_explorer")
    if peak_weekday in (5, 6):
        matches.append("weekend_warrior")
    if payload.top_movies and payload.top_movies[0].plays >= 3:
        matches.append("loyal_rewatcher")
    return matches


def compute_persona_id(payload: WrappedPayload) -> str:
    matches = matching_persona_ids(payload)
    if not matches:
        return "dedicated_viewer"
    if len(matches) == 1:
        return matches[0]
    # Pick at random among the matched personas, seeded on user + year so a
    # given wrapped keeps the same crown across regenerations.
    rng = random.Random(f"{payload.user_id}:{payload.year}")
    return rng.choice(matches)


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
