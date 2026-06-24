"""Load UI strings from translate/{language}.json."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT

# Major European languages. Each canonical name maps to translate/{name}.json.
# Smaller regional languages (e.g. Lithuanian, Czech) are intentionally omitted.
_LANGUAGE_ALIASES: dict[str, str] = {
    # English
    "en": "english",
    "english": "english",
    # Dutch
    "nl": "dutch",
    "dutch": "dutch",
    "nederlands": "dutch",
    # French
    "fr": "french",
    "french": "french",
    "français": "french",
    "francais": "french",
    # German
    "de": "german",
    "german": "german",
    "deutsch": "german",
    # Polish
    "pl": "polish",
    "polish": "polish",
    "polski": "polish",
    # Spanish
    "es": "spanish",
    "spanish": "spanish",
    "español": "spanish",
    "espanol": "spanish",
    # Italian
    "it": "italian",
    "italian": "italian",
    "italiano": "italian",
    # Portuguese
    "pt": "portuguese",
    "portuguese": "portuguese",
    "português": "portuguese",
    "portugues": "portuguese",
    # Swedish
    "sv": "swedish",
    "swedish": "swedish",
    "svenska": "swedish",
    # Norwegian
    "no": "norwegian",
    "nb": "norwegian",
    "nn": "norwegian",
    "norwegian": "norwegian",
    "norsk": "norwegian",
    # Danish
    "da": "danish",
    "danish": "danish",
    "dansk": "danish",
    # Finnish
    "fi": "finnish",
    "finnish": "finnish",
    "suomi": "finnish",
    # Greek
    "el": "greek",
    "greek": "greek",
    # Romanian
    "ro": "romanian",
    "romanian": "romanian",
    # Hungarian
    "hu": "hungarian",
    "hungarian": "hungarian",
    "magyar": "hungarian",
}

_CHART_LABELS_FILE = "chart_labels.json"


def normalize_language(language: str | None) -> str:
    key = (language or "english").strip().lower()
    return _LANGUAGE_ALIASES.get(key, key)


@lru_cache
def load_chart_labels() -> dict[str, list[str]]:
    path = PROJECT_ROOT / "translate" / _CHART_LABELS_FILE
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {key: list(value) for key, value in raw.items()}


def chart_label_index(label: str, *variant_keys: str) -> int | None:
    charts = load_chart_labels()
    target = label.strip().lower()
    for key in variant_keys:
        for index, name in enumerate(charts.get(key, [])):
            if name.lower() == target:
                return index
    return None


@lru_cache
def available_languages() -> tuple[str, ...]:
    translate_dir = PROJECT_ROOT / "translate"
    names = sorted(
        path.stem
        for path in translate_dir.glob("*.json")
        if path.is_file() and path.name != _CHART_LABELS_FILE
    )
    return tuple(names)


def _flatten_strings(data: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten_strings(value, path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            path = f"{prefix}.{index}"
            if isinstance(value, (dict, list)):
                out.update(_flatten_strings(value, path))
            else:
                out[path] = str(value)
    elif data is not None:
        out[prefix] = str(data)
    return out


@lru_cache
def load_translation_file(language: str) -> dict[str, str]:
    lang = normalize_language(language)
    path = PROJECT_ROOT / "translate" / f"{lang}.json"
    if not path.is_file():
        if lang != "english":
            return load_translation_file("english")
        raise FileNotFoundError(f"Missing translation file: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _flatten_strings(raw)


class Translator:
    def __init__(self, language: str = "english"):
        self.language = normalize_language(language)
        self._strings = load_translation_file(self.language)

    def t(self, key: str, **kwargs: Any) -> str:
        text = self._strings.get(key, key)
        if not kwargs:
            return text
        try:
            return text.format(**kwargs)
        except KeyError:
            return text

    def get(self, key: str, default: str | None = None) -> str | None:
        if key in self._strings:
            return self._strings[key]
        return default

    def html_lang(self) -> str:
        return self.get("meta.html_lang", "en") or "en"

    def date_locale(self) -> str:
        return self.get("meta.date_locale", "en-US") or "en-US"

    def list_values(self, prefix: str) -> list[str]:
        pattern = re.compile(rf"^{re.escape(prefix)}\.(\d+)$")
        indexed: list[tuple[int, str]] = []
        for key, value in self._strings.items():
            match = pattern.match(key)
            if match:
                indexed.append((int(match.group(1)), value))
        indexed.sort(key=lambda item: item[0])
        return [value for _, value in indexed]

    def client_bundle(self) -> dict[str, Any]:
        bundle: dict[str, Any] = dict(self._strings)
        bundle["locale.weekdays"] = self.list_values("locale.weekdays")
        bundle["locale.weekdays_short"] = self.list_values("locale.weekdays_short")
        bundle["locale.months"] = self.list_values("locale.months")
        bundle["locale.months_short"] = self.list_values("locale.months_short")
        return bundle


@lru_cache
def get_translator(language: str = "english") -> Translator:
    return Translator(language)


def localize_persona(data: dict[str, Any], translator: Translator) -> None:
    persona_id = data.get("persona_id") or "dedicated_viewer"
    data["persona"] = translator.t(f"persona.{persona_id}.name")
    data["persona_tagline"] = translator.t(f"persona.{persona_id}.tagline")


def localize_wrapped_payload(data: dict[str, Any], translator: Translator) -> dict[str, Any]:
    localize_persona(data, translator)

    month_index = data.get("busiest_month_index")
    if month_index:
        months = translator.list_values("locale.months")
        idx = int(month_index) - 1
        if 0 <= idx < len(months):
            data["busiest_month"] = months[idx]

    weekdays = translator.list_values("locale.weekdays")
    plays_by_weekday = data.get("plays_by_weekday") or []
    if weekdays and plays_by_weekday:
        peak_idx = max(range(7), key=lambda i: int(plays_by_weekday[i]) if i < len(plays_by_weekday) else 0)
        if 0 <= peak_idx < len(weekdays):
            data["peak_day"] = weekdays[peak_idx]

    server = data.get("server") or {}
    rank_context = server.get("rank_context") or []
    if rank_context:
        user_rank = next((entry["rank"] for entry in rank_context if entry.get("is_you")), None)
        if user_rank is not None:
            for entry in rank_context:
                offset = int(entry["rank"]) - int(user_rank)
                is_leader = entry["rank"] == 1 and not entry.get("is_you") and offset < -1
                entry["position_label"] = position_label(translator, offset, is_leader)

    server_title = (server.get("server_top_show") or server.get("server_top_movie") or "").strip()
    user_title = (data.get("user_comparison_show") or data.get("user_comparison_movie") or "").strip()
    if server_title and user_title and not (data.get("ai_copy") or {}).get("server_vs_you"):
        same = data.get("comparison_same_show")
        if same is None:
            same = server_title.lower() == user_title.lower()
        reason = data.get("user_comparison_reason")
        data["comparison_caption"] = comparison_caption(
            translator, server_title, user_title, same_show=bool(same), reason=reason
        )

    accents = translator.list_values("comparison.accents")
    if accents and not data.get("comparison_headline_accent"):
        key = f"{server_title.lower()}|{user_title.lower()}"
        idx = sum(ord(c) for c in key) % len(accents)
        data["comparison_headline_accent"] = accents[idx]

    return data


def position_label(translator: Translator, offset: int, is_leader: bool = False) -> str:
    if is_leader:
        return translator.t("rank.leader")
    if offset == 0:
        return translator.t("rank.you")
    if offset == -1:
        return translator.t("rank.one_higher")
    if offset == 1:
        return translator.t("rank.one_lower")
    if offset < -1:
        return translator.t("rank.higher", count=abs(offset))
    return translator.t("rank.lower", count=offset)


def comparison_caption(
    translator: Translator,
    server_title: str,
    user_title: str,
    *,
    same_show: bool,
    reason: str | None,
) -> str:
    if same_show:
        return translator.t("comparison.caption.same", server_title=server_title)
    if reason == "first_played":
        return translator.t("comparison.caption.first_played", server_title=server_title, user_title=user_title)
    return translator.t("comparison.caption.different", server_title=server_title, user_title=user_title)
