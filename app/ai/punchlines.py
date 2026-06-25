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
from app.i18n import Translator, get_translator
from app.models.schemas import AICopy

logger = logging.getLogger(__name__)

_MAX_LEN = 200


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


def _kind_word(kind: str | None, translator: Translator) -> str:
    if kind == "film":
        return translator.t("ai.kind_movie")
    if kind == "serie":
        return translator.t("ai.kind_show")
    return translator.t("ai.kind_generic")


def _comparison_relation(facts: PunchlineFacts, translator: Translator) -> str:
    if facts.comparison_same_show:
        return translator.t("ai.relation_same")
    if facts.comparison_reason == "first_played":
        return translator.t("ai.relation_first_played")
    return translator.t("ai.relation_different")


def build_prompt(facts: PunchlineFacts, translator: Translator | None = None) -> str:
    tr = translator or get_translator()
    server = facts.server_top_title or tr.t("ai.unknown_title")
    user = facts.user_top_title or tr.t("ai.unknown_title")
    relation = _comparison_relation(facts, tr)
    lines = [
        tr.t("ai.prompt_intro"),
        "",
        tr.t("ai.prompt_data_heading"),
        tr.t("ai.prompt_unique_series", count=facts.unique_series),
        tr.t("ai.prompt_seasons", count=facts.unique_seasons),
        tr.t("ai.prompt_episodes", count=facts.unique_episodes),
        tr.t(
            "ai.prompt_server_top",
            title=server,
            kind=_kind_word(facts.server_top_kind, tr),
        ),
        tr.t(
            "ai.prompt_user_top",
            title=user,
            kind=_kind_word(facts.user_top_kind, tr),
        ),
        tr.t("ai.prompt_relation", relation=relation),
        "",
        tr.t("ai.prompt_task_heading"),
        tr.t("ai.prompt_series_depth_task"),
        tr.t("ai.prompt_server_vs_task", server=server, user=user),
        "",
        tr.t("ai.prompt_output"),
    ]
    return "\n".join(lines)


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


def generate_ai_copy(
    ai: CursorAIClient,
    facts: PunchlineFacts,
    *,
    language: str = "english",
) -> AICopy:
    """Run the batched punchline request. Returns empty AICopy when disabled."""
    if not ai.enabled:
        return AICopy()
    translator = get_translator(language)
    reply = ai.generate_text(
        build_prompt(facts, translator),
        system=translator.t("ai.system"),
    )
    copy = parse_ai_copy(reply)
    logger.info(
        "Cursor AI punchlines generated language=%s series_depth=%s server_vs_you=%s",
        translator.language,
        bool(copy.series_depth),
        bool(copy.server_vs_you),
    )
    return copy
