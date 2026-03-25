from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manovarta_core.questionnaires import ITEM_INDEX


SYSTEM_EXTRACTION = (
    "You extract questionnaire-aligned evidence from multilingual screening transcripts. "
    "Return strict JSON only with keys: items, safety_level, safety_cues, notes."
)

SYSTEM_DIALOGUE = (
    "You are ManoVarta, a multilingual screening assistant. "
    "Ask one concise, safe follow-up in the user's language. "
    "Do not diagnose and do not give therapy."
)


@dataclass(frozen=True)
class SplitManifest:
    train_profiles: list[str]
    dev_profiles: list[str]
    test_profiles: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "train": self.train_profiles,
            "dev": self.dev_profiles,
            "test": self.test_profiles,
        }


def build_profile_splits(profiles: list[dict[str, Any]]) -> SplitManifest:
    by_language: dict[str, list[str]] = defaultdict(list)
    for profile in sorted(profiles, key=lambda item: item["patient_id"]):
        by_language[profile["language"]].append(profile["patient_id"])

    split_map = {"train": [], "dev": [], "test": []}
    for patient_ids in by_language.values():
        train_ids, dev_ids, test_ids = _three_way_split(patient_ids)
        split_map["train"].extend(train_ids)
        split_map["dev"].extend(dev_ids)
        split_map["test"].extend(test_ids)

    return SplitManifest(
        train_profiles=sorted(split_map["train"]),
        dev_profiles=sorted(split_map["dev"]),
        test_profiles=sorted(split_map["test"]),
    )


def assign_conversations_to_splits(
    conversations: list[dict[str, Any]],
    manifest: SplitManifest,
) -> dict[str, list[dict[str, Any]]]:
    split_index = {}
    for split_name, profile_ids in manifest.to_dict().items():
        for profile_id in profile_ids:
            split_index[profile_id] = split_name

    grouped = {"train": [], "dev": [], "test": []}
    for conversation in conversations:
        split_name = split_index.get(conversation.get("patient_id"), "train")
        grouped[split_name].append(conversation)
    return grouped


def build_extractor_examples(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples = []
    for conversation in conversations:
        prompt = _extractor_prompt(conversation)
        response = json.dumps(_extractor_target(conversation), ensure_ascii=False)
        examples.append(
            {
                "id": conversation["conversation_id"],
                "task": "extractor",
                "language": conversation["language"],
                "prompt": prompt,
                "response": response,
                "text": _pack_instruction(SYSTEM_EXTRACTION, prompt, response),
            }
        )
    return examples


def build_follow_up_examples(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples = []
    for conversation in conversations:
        turns = conversation.get("conversation_turns", [])
        for idx, turn in enumerate(turns):
            if turn["speaker"] != "assistant" or idx == 0:
                continue
            history = turns[:idx]
            if not history or history[-1]["speaker"] != "user":
                continue
            prompt = _follow_up_prompt(conversation["language"], history)
            response = turn["text"]
            examples.append(
                {
                    "id": f"{conversation['conversation_id']}-t{turn['turn_id']}",
                    "task": "follow_up",
                    "language": conversation["language"],
                    "prompt": prompt,
                    "response": response,
                    "text": _pack_instruction(SYSTEM_DIALOGUE, prompt, response),
                }
            )
    return examples


def build_safety_examples(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples = []
    for conversation in conversations:
        user_text = "\n".join(
            turn["text"] for turn in conversation.get("conversation_turns", []) if turn["speaker"] == "user"
        )
        safety = conversation.get("safety_flag", {})
        examples.append(
            {
                "id": conversation["conversation_id"],
                "task": "safety",
                "language": conversation["language"],
                "text": user_text,
                "label": safety.get("level", "none"),
                "cues": safety.get("cues", []),
            }
        )
    return examples


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _three_way_split(patient_ids: list[str]) -> tuple[list[str], list[str], list[str]]:
    count = len(patient_ids)
    if count <= 2:
        train = patient_ids[:1]
        dev = patient_ids[1:2]
        test = patient_ids[2:]
        return train, dev, test

    train_count = max(1, round(count * 0.5))
    dev_count = max(1, round(count * 0.25))
    test_count = count - train_count - dev_count
    if test_count <= 0:
        test_count = 1
        if train_count > dev_count:
            train_count -= 1
        else:
            dev_count -= 1

    train = patient_ids[:train_count]
    dev = patient_ids[train_count:train_count + dev_count]
    test = patient_ids[train_count + dev_count:]
    return train, dev, test


def _extractor_prompt(conversation: dict[str, Any]) -> str:
    transcript = _transcript_text(conversation.get("conversation_turns", []))
    item_lines = "\n".join(
        f"- {item_id}: {item.label} ({item.focus})"
        for item_id, item in ITEM_INDEX.items()
    )
    return (
        f"Language: {conversation['language']}\n"
        f"Use these item ids:\n{item_lines}\n\n"
        "Return JSON with items, safety_level, safety_cues, notes.\n"
        "Only include supported items in items.\n"
        f"Transcript:\n{transcript}"
    )


def _extractor_target(conversation: dict[str, Any]) -> dict[str, Any]:
    span_index = defaultdict(list)
    for span in conversation.get("evidence_spans", []):
        span_index[span["item_id"]].append(span)

    items = []
    labels = {}
    labels.update(conversation.get("phq9_item_labels", {}))
    labels.update(conversation.get("gad7_item_labels", {}))
    for item_id, value in labels.items():
        if value <= 0:
            continue
        spans = span_index.get(item_id, [])
        items.append(
            {
                "item_id": item_id,
                "value": value,
                "evidence_quote": spans[0]["text_span"] if spans else "",
                "confidence_note": conversation.get("annotator_notes", "") or "Annotated seed evidence.",
            }
        )

    return {
        "items": items,
        "safety_level": conversation.get("safety_flag", {}).get("level", "none"),
        "safety_cues": conversation.get("safety_flag", {}).get("cues", []),
        "notes": conversation.get("annotator_notes", ""),
    }


def _follow_up_prompt(language: str, turns: list[dict[str, Any]]) -> str:
    transcript = _transcript_text(turns)
    return (
        f"Language: {language}\n"
        "Draft the next assistant turn.\n"
        "Keep it to one or two sentences.\n"
        f"Transcript so far:\n{transcript}"
    )


def _transcript_text(turns: list[dict[str, Any]]) -> str:
    return "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in turns)


def _pack_instruction(system_prompt: str, prompt: str, response: str) -> str:
    return (
        "<|system|>\n"
        f"{system_prompt}\n"
        "<|user|>\n"
        f"{prompt}\n"
        "<|assistant|>\n"
        f"{response}"
    )
