from __future__ import annotations

import json
import re
from typing import Any

SAFETY_LEVEL_ALIASES = {
    "none": "none",
    "safe": "none",
    "low": "none",
    "low_risk": "none",
    "lowrisk": "none",
    "review": "review",
    "caution": "review",
    "moderate": "review",
    "medium": "review",
    "needs_review": "review",
    "need_review": "review",
    "high_caution": "review",
    "highcaution": "review",
    "urgent": "urgent",
    "high": "urgent",
    "severe": "urgent",
    "crisis": "urgent",
    "immediate": "urgent",
}


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
        return normalize_extractor_payload(payload)

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
        for match in re.finditer(
            r'(?im)(?P<item_id>(?:phq|gad)_q\d+_[a-z_]+)\s*(?:[:=|\-]|->|\bis\b)\s*(?P<value>[0-3])',
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

    safety_match = re.search(r'"safety_level"\s*:\s*"([^"]+)"', cleaned)
    return normalize_extractor_payload({
        "items": items,
        "safety_level": safety_match.group(1) if safety_match else "none",
        "safety_cues": [],
        "notes": "salvaged_partial_json",
    })


def normalize_safety_level(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return SAFETY_LEVEL_ALIASES.get(text, "none")


def normalize_extractor_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    items = []
    seen = set()
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id", "")).strip()
        if not item_id or item_id in seen:
            continue
        try:
            value = int(item.get("value"))
        except (TypeError, ValueError):
            continue
        if value < 1 or value > 3:
            continue
        normalized_item = {"item_id": item_id, "value": value}
        if "evidence_quote" in item and str(item.get("evidence_quote", "")).strip():
            normalized_item["evidence_quote"] = str(item["evidence_quote"]).strip()
        if "confidence_note" in item and str(item.get("confidence_note", "")).strip():
            normalized_item["confidence_note"] = str(item["confidence_note"]).strip()
        items.append(normalized_item)
        seen.add(item_id)

    return {
        "items": items,
        "safety_level": normalize_safety_level(payload.get("safety_level", "none")),
        "safety_cues": [str(cue).strip() for cue in payload.get("safety_cues", []) if str(cue).strip()],
        "notes": str(payload.get("notes", "")).strip(),
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
