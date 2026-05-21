from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import WrappedPayload


@dataclass(frozen=True)
class PersonaResult:
    persona_id: str
    persona: str
    persona_tagline: str


PERSONAS: dict[str, PersonaResult] = {
    "curator": PersonaResult(
        "curator",
        "De Curator",
        "Je vraagt meer aan dan je scrollt.",
    ),
    "series_devourer": PersonaResult(
        "series_devourer",
        "Serieverslinder",
        "Afleveringen zijn je comfortfood.",
    ),
    "film_buff": PersonaResult(
        "film_buff",
        "Filmliefhebber",
        "Films zijn jouw hoofdprogramma.",
    ),
    "marathon_runner": PersonaResult(
        "marathon_runner",
        "Marathonloper",
        "Je meet het leven in uren.",
    ),
    "binge_royalty": PersonaResult(
        "binge_royalty",
        "Binge-koning(in)",
        "Streaks zijn je superkracht.",
    ),
    "night_owl": PersonaResult(
        "night_owl",
        "Nachtuil",
        "De server gloeit na 22:00.",
    ),
    "early_bird": PersonaResult(
        "early_bird",
        "Vroege vogel",
        "Eerste licht, eerste play.",
    ),
    "completionist": PersonaResult(
        "completionist",
        "De Voltooier",
        "Je proeft van alles.",
    ),
    "genre_explorer": PersonaResult(
        "genre_explorer",
        "Genreverkenner",
        "Je kiest niet één pad.",
    ),
    "weekend_warrior": PersonaResult(
        "weekend_warrior",
        "Weekendstrijder",
        "Za en zo is showtijd.",
    ),
    "loyal_rewatcher": PersonaResult(
        "loyal_rewatcher",
        "Trouwe herkijker",
        "Favorieten verdienen een herkansing.",
    ),
    "dedicated_viewer": PersonaResult(
        "dedicated_viewer",
        "Toegewijde kijker",
        "Stabiel en trouw.",
    ),
}


def _genre_count(payload: WrappedPayload) -> int:
    names: set[str] = set()
    for g in payload.top_movie_genres + payload.top_show_genres:
        names.add(g.name.lower())
    return len(names)


def compute_persona(payload: WrappedPayload) -> PersonaResult:
    tg = payload.telegram
    requests_total = tg.movies_requested + tg.series_requested

    if requests_total >= 10 and payload.total_plays > 0 and requests_total > payload.total_plays * 0.3:
        return PERSONAS["curator"]
    if payload.tv_plays > payload.movie_plays * 2:
        return PERSONAS["series_devourer"]
    if payload.movie_plays > payload.tv_plays * 2:
        return PERSONAS["film_buff"]
    if payload.watch_hours >= 300:
        return PERSONAS["marathon_runner"]
    if payload.longest_streak_days >= 7:
        return PERSONAS["binge_royalty"]
    if payload.peak_hour is not None and payload.peak_hour >= 22:
        return PERSONAS["night_owl"]
    if payload.peak_hour is not None and payload.peak_hour <= 8:
        return PERSONAS["early_bird"]
    if payload.unique_series >= 15:
        return PERSONAS["completionist"]
    if _genre_count(payload) >= 6:
        return PERSONAS["genre_explorer"]
    if payload.peak_day and payload.peak_day.lower() in ("zaterdag", "zondag"):
        return PERSONAS["weekend_warrior"]
    if payload.top_movies and payload.top_movies[0].plays >= 3:
        return PERSONAS["loyal_rewatcher"]
    return PERSONAS["dedicated_viewer"]


def apply_persona(payload: WrappedPayload) -> None:
    result = compute_persona(payload)
    payload.persona_id = result.persona_id
    payload.persona = result.persona
    payload.persona_tagline = result.persona_tagline
