from __future__ import annotations

from typing import Any


ITEM_ID_ALIASES = {
    "gad_q7_fear_awful": "gad_q7_afraid",
    "gad_q7_afraid": "gad_q7_afraid",
}

ITEM_ID_LIST_KEYS = {
    "high_confidence_items",
    "low_confidence_items",
    "next_items",
    "next_probe_items",
    "resolved_items",
    "partial_items",
    "contradicted_items",
    "abstained_items",
    "unresolved_items",
    "review_items",
    "touched_items",
    "asked_items",
}

ITEM_LABEL_MAP_KEYS = {
    "phq9_item_labels",
    "gad7_item_labels",
    "predictions",
}


def canonicalize_item_id(item_id: Any) -> str:
    text = str(item_id or "").strip()
    return ITEM_ID_ALIASES.get(text, text)


def canonicalize_item_id_list(item_ids: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    if not item_ids:
        return []
    normalized: list[Any] = []
    for value in item_ids:
        if isinstance(value, str):
            normalized.append(canonicalize_item_id(value))
        else:
            normalized.append(value)
    return normalized


def canonicalize_label_map(labels: dict[str, Any] | None) -> dict[str, Any]:
    if not labels:
        return {}
    return {canonicalize_item_id(item_id): value for item_id, value in labels.items()}


def canonicalize_payload_item_ids(payload: Any, *, parent_key: str | None = None) -> Any:
    if isinstance(payload, dict):
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if key == "item_id":
                normalized[key] = canonicalize_item_id(value)
                continue
            if key in ITEM_LABEL_MAP_KEYS and isinstance(value, dict):
                normalized[key] = canonicalize_label_map(value)
                continue
            normalized[key] = canonicalize_payload_item_ids(value, parent_key=key)
        return normalized

    if isinstance(payload, list):
        if parent_key in ITEM_ID_LIST_KEYS:
            return canonicalize_item_id_list(payload)
        return [canonicalize_payload_item_ids(item, parent_key=parent_key) for item in payload]

    return payload
