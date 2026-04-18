from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from manovarta_core.item_ids import canonicalize_item_id, canonicalize_payload_item_ids
from manovarta_core.json_utils import normalize_safety_level


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = PROJECT_ROOT / "data" / "gold"


def load_gold_metadata_rows(
    *,
    include_hindi_pilot: bool = True,
    gold_core_only: bool = False,
) -> list[dict[str, str]]:
    metadata_path = GOLD_DIR / "metadata.csv"
    with metadata_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    selected: list[dict[str, str]] = []
    for row in rows:
        if gold_core_only and row.get("language") != "en":
            continue
        if not include_hindi_pilot and _is_hindi_pilot_row(row):
            continue
        selected.append(dict(row, dataset_role=_dataset_role(row)))
    return selected


def load_gold_profiles(
    *,
    include_hindi_pilot: bool = True,
    gold_core_only: bool = False,
) -> list[dict[str, Any]]:
    rows = load_gold_metadata_rows(include_hindi_pilot=include_hindi_pilot, gold_core_only=gold_core_only)
    profiles: dict[str, dict[str, Any]] = {}
    for row in rows:
        patient_id = row.get("participant_id") or row["session_id"]
        if patient_id in profiles:
            continue
        background_context = (
            "English gold-core public interview transcript with local dual annotation and adjudication."
            if row["language"] == "en"
            else "Repurposed Hindi pilot audio transcript from IndicVoices with local dual annotation and adjudication."
        )
        profiles[patient_id] = {
            "patient_id": patient_id,
            "language": row["language"],
            "age": _coerce_age(row.get("age_years")),
            "occupation": row.get("occupation") or "unknown_from_source",
            "background_profile": {
                "context": background_context,
                "living_situation": row.get("living_situation") or "unknown_from_source",
                "support_system": row.get("support_system") or "unknown_from_source",
            },
            "symptom_profile": {
                "depression_level": "annotated_gold",
                "anxiety_level": "annotated_gold",
            },
            "disclosure_style": "public_dataset_transcript",
            "nuance_tags": [row["dataset_role"]],
            "notes": row.get("notes", ""),
        }
    return list(profiles.values())


def load_gold_conversations(
    *,
    include_hindi_pilot: bool = True,
    gold_core_only: bool = False,
) -> list[dict[str, Any]]:
    rows = load_gold_metadata_rows(include_hindi_pilot=include_hindi_pilot, gold_core_only=gold_core_only)
    conversations: list[dict[str, Any]] = []
    for row in rows:
        transcript = _read_json(row["transcript_file"])
        labels = _read_json(row["adjudicated_label_file"])

        phq_labels: dict[str, int] = {}
        gad_labels: dict[str, int] = {}
        evidence_spans: list[dict[str, Any]] = []
        annotator_notes: list[str] = []

        for item in labels.get("items", []):
            item_id = canonicalize_item_id(item.get("item_id"))
            value = int(item.get("value", 0))
            if item_id.startswith("phq_"):
                phq_labels[item_id] = value
            elif item_id.startswith("gad_"):
                gad_labels[item_id] = value
            evidence_spans.append(
                {
                    "item_id": item_id,
                    "turn_id": _normalize_turn_id(item.get("turn_id")),
                    "speaker": item.get("speaker", "user"),
                    "text_span": str(item.get("evidence_quote", "")).strip(),
                    "notes": str(item.get("notes", "")).strip(),
                }
            )
            note = str(item.get("notes", "")).strip()
            if note:
                annotator_notes.append(note)

        safety_payload = labels.get("safety", {}) if isinstance(labels.get("safety"), dict) else {}
        safety_quote = str(safety_payload.get("evidence_quote", "")).strip()
        safety_cues = []
        if safety_quote and "no safety concerns identified" not in safety_quote.lower():
            safety_cues.append(safety_quote)

        turns = [
            {
                "turn_id": _normalize_turn_id(turn["turn_id"]),
                "speaker": turn["speaker"],
                "text": turn["text"],
                "language_tag": row["language"],
            }
            for turn in transcript.get("turns", [])
        ]

        conversation = {
            "conversation_id": row["session_id"],
            "patient_id": row.get("participant_id") or row["session_id"],
            "language": row["language"],
            "cohort": transcript.get("cohort", row.get("split", "")),
            "collection_source": row.get("collection_source", ""),
            "dataset_role": row["dataset_role"],
            "generation_source": "gold_adjudicated",
            "review_status": "adjudicated",
            "background_profile": {
                "living_situation": row.get("living_situation") or "unknown_from_source",
                "support_system": row.get("support_system") or "unknown_from_source",
                "collection_source": row.get("collection_source") or "unknown_from_source",
            },
            "conversation_turns": turns,
            "evidence_spans": evidence_spans,
            "phq9_item_labels": phq_labels,
            "gad7_item_labels": gad_labels,
            "safety_flag": {
                "level": normalize_safety_level(safety_payload.get("level", "none")),
                "cues": safety_cues,
            },
            "annotator_notes": " | ".join(dict.fromkeys(annotator_notes[:5])),
            "confidence_notes": {
                "high_confidence_items": [
                    canonicalize_item_id(item.get("item_id"))
                    for item in labels.get("items", [])
                    if str(item.get("confidence", "")).strip().lower() == "high"
                ],
                "low_confidence_items": [
                    canonicalize_item_id(item.get("item_id"))
                    for item in labels.get("items", [])
                    if str(item.get("confidence", "")).strip().lower() == "low"
                ],
            },
        }
        conversations.append(canonicalize_payload_item_ids(conversation))
    return conversations


def _read_json(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_age(value: str | None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _is_hindi_pilot_row(row: dict[str, str]) -> bool:
    return row.get("language") == "hi" and "indicvoices" in row.get("collection_source", "").lower()


def _dataset_role(row: dict[str, str]) -> str:
    if row.get("language") == "en":
        return "gold_core"
    if _is_hindi_pilot_row(row):
        return "pilot_voice_extension"
    return "gold"


def _normalize_turn_id(value: Any) -> int:
    text = str(value or "").strip()
    digits = "".join(char for char in text if char.isdigit())
    if digits:
        return int(digits)
    return 0
