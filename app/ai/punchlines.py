"""Build, request, and parse AI punchlines for wrapped slides.

A single batched request asks the model for all punchlines at once and expects
a JSON object back. Every value is validated; anything missing or malformed is
dropped so the frontend falls back to its rule-based default. Generation is a
no-op (returns an empty ``AICopy``) when the Cursor connection is disabled.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.ai.client import CursorAIClient
from app.models.schemas import AICopy

logger = logging.getLogger(__name__)

_MAX_LEN = 200

_SYSTEM = (
    "Je schrijft korte, pakkende Nederlandse 'wrapped' punchlines in de stijl "
    "van Spotify Wrapped: informeel, speels en persoonlijk (jij/je-vorm). "
    "Elke punchline is precies één zin, maximaal ~160 tekens, zonder "
    "aanhalingstekens en zonder emoji."
)


@dataclass(frozen=True)
class PunchlineFacts:
    unique_series: int
    unique_seasons: int
    unique_episodes: int
    server_top_title: str | None
    server_top_kind: str | None  # "serie" | "film"
    user_top_title: str | None
    user_top_kind: str | None  # "serie" | "film"
    user_top_plays: int | None
    comparison_same_show: bool | None
    comparison_reason: str | None  # "most_played" | "first_played"


def build_facts(
    *,
    unique_series: int,
    unique_seasons: int,
    unique_episodes: int,
    server_top_show: str | None,
    server_top_movie: str | None,
    user_comparison_show: str | None,
    user_comparison_movie: str | None,
    comparison_same_show: bool | None,
    user_top_plays: int | None = None,
    comparison_reason: str | None = None,
) -> PunchlineFacts:
    server_kind = "serie" if server_top_show else ("film" if server_top_movie else None)
    user_kind = "serie" if user_comparison_show else ("film" if user_comparison_movie else None)
    return PunchlineFacts(
        unique_series=unique_series,
        unique_seasons=unique_seasons,
        unique_episodes=unique_episodes,
        server_top_title=server_top_show or server_top_movie,
        server_top_kind=server_kind,
        user_top_title=user_comparison_show or user_comparison_movie,
        user_top_kind=user_kind,
        user_top_plays=user_top_plays,
        comparison_same_show=comparison_same_show,
        comparison_reason=comparison_reason,
    )


def _kind_word(kind: str | None) -> str:
    if kind == "film":
        return "de film"
    if kind == "serie":
        return "de serie"
    return "titel"


def build_prompt(facts: PunchlineFacts) -> str:
    server = facts.server_top_title or "onbekend"
    user = facts.user_top_title or "onbekend"
    if facts.comparison_same_show:
        relation = "De gebruiker en de rest van de server hadden dezelfde nummer één."
    elif facts.comparison_reason == "first_played":
        relation = "Hiermee begon de gebruiker het jaar, terwijl de server iets anders draaide."
    else:
        relation = "De smaak van de gebruiker week af van wat de server het meest keek."
    return (
        "Genereer punchlines voor een Plex Wrapped op basis van deze data.\n\n"
        "DATA:\n"
        f"- Aantal verschillende series: {facts.unique_series}\n"
        f"- Aantal seizoenen: {facts.unique_seasons}\n"
        f"- Aantal afleveringen: {facts.unique_episodes}\n"
        f"- Populairste op de server: {server} ({_kind_word(facts.server_top_kind)})\n"
        f"- Favoriet van de gebruiker: {user} ({_kind_word(facts.user_top_kind)})\n"
        f"- Relatie: {relation}\n\n"
        "OPDRACHT:\n"
        "1. 'series_depth': een punchline over hoe diep de gebruiker in series "
        "dook, gebaseerd op het aantal series/seizoenen/afleveringen.\n"
        "2. 'server_vs_you': een gevatte punchline die de smaak van de server "
        f"('{server}') vergelijkt met die van de gebruiker ('{user}'). "
        "Baseer de grap op WAAR deze titels inhoudelijk over gaan — hun thema's, "
        "sfeer, setting of genre — en speel met het contrast of de overeenkomst "
        "daartussen. Plak GEEN labels als '(serie)' of '(film)' achter de titels "
        "en som geen kale cijfers op.\n\n"
        "Antwoord UITSLUITEND met een geldig JSON-object met exact deze twee "
        "sleutels, zonder markdown, zonder codeblok en zonder uitleg:\n"
        '{"series_depth": "...", "server_vs_you": "..."}'
    )


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = re.sub(r"\s+", " ", value).strip().strip('"').strip()
    if not text or len(text) > _MAX_LEN:
        return None
    return text


def _extract_json(text: str) -> dict | None:
    """Pull the first JSON object out of a possibly-noisy model reply."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_ai_copy(text: str | None) -> AICopy:
    if not text:
        return AICopy()
    data = _extract_json(text)
    if not data:
        logger.warning("Cursor AI punchline reply was not valid JSON")
        return AICopy()
    return AICopy(
        series_depth=_clean(data.get("series_depth")),
        server_vs_you=_clean(data.get("server_vs_you")),
    )


def generate_ai_copy(ai: CursorAIClient, facts: PunchlineFacts) -> AICopy:
    """Run the batched punchline request. Returns empty AICopy when disabled."""
    if not ai.enabled:
        return AICopy()
    reply = ai.generate_text(build_prompt(facts), system=_SYSTEM)
    copy = parse_ai_copy(reply)
    logger.info(
        "Cursor AI punchlines generated series_depth=%s server_vs_you=%s",
        bool(copy.series_depth),
        bool(copy.server_vs_you),
    )
    return copy
