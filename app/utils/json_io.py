from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def strip_json_comments(text: str) -> str:
    """Remove // and /* */ comments outside JSON strings."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    lines: list[str] = []
    for line in text.splitlines():
        in_string = False
        escaped = False
        cut = len(line)
        for i, ch in enumerate(line):
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                cut = i
                break
        lines.append(line[:cut])
    return "\n".join(lines)


def _merge_dict_objects(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    merged: dict[str, Any] = {}
    idx = 0
    stripped = text.strip()
    while idx < len(stripped):
        while idx < len(stripped) and stripped[idx] in ", \t\r\n":
            idx += 1
        if idx >= len(stripped):
            break
        obj, end = decoder.raw_decode(stripped, idx)
        if not isinstance(obj, dict):
            raise json.JSONDecodeError(
                "Expected a JSON object for mapping files",
                stripped,
                idx,
            )
        merged.update(obj)
        idx = end
    return merged


def load_json_dict(path: Path) -> dict[str, Any]:
    """
    Load a JSON object from disk.

    Supports // comments and multiple top-level `{...}` objects (merged), which
    helps when a mapping file accidentally contains back-to-back objects.
    """
    text = strip_json_comments(path.read_text(encoding="utf-8"))
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        if "Extra data" not in str(exc):
            raise
        data = _merge_dict_objects(text)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object at the top level")
    return data
