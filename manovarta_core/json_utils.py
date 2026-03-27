from __future__ import annotations

import json
import re
from typing import Any


def parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = strip_code_fences(text).strip()
    if not cleaned:
        return None

    direct = _try_json(cleaned)
    if direct is not None:
        return direct

    candidate = _first_balanced_object(cleaned)
    if candidate:
        return _try_json(candidate)

    return None


def parse_extractor_payload(text: str) -> dict[str, Any] | None:
    payload = parse_json_object(text)
    if payload is not None:
        return payload

    cleaned = strip_code_fences(text).strip()
    if not cleaned:
        return None

    items = []
    seen = set()
    for match in re.finditer(
        r'"item_id"\s*:\s*"(?P<item_id>[^"]+)"[\s\S]{0,240}?"value"\s*:\s*(?P<value>[0-3])',
        cleaned,
    ):
        item_id = match.group("item_id").strip()
        value = int(match.group("value"))
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        items.append({"item_id": item_id, "value": value})

    if not items:
        return None

    safety_match = re.search(r'"safety_level"\s*:\s*"(none|review|urgent)"', cleaned)
    return {
        "items": items,
        "safety_level": safety_match.group(1) if safety_match else "none",
        "safety_cues": [],
        "notes": "salvaged_partial_json",
    }


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    return cleaned


def _try_json(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]

    return None
