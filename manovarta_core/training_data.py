from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manovarta_core.questionnaires import ITEM_INDEX


SYSTEM_EXTRACTION = (
    "You extract questionnaire-aligned evidence from multilingual screening transcripts. "
    "Return strict JSON only with keys: items and safety_level."
)

SYSTEM_DIALOGUE = (
    "You are ManoVarta, a multilingual screening assistant. "
    "Ask one concise, safe follow-up in the user's language. "
    "Do not diagnose and do not give therapy."
)

SAFETY_KEYWORDS = (
    "disappear",
    "vanish",
    "better off without me",
    "hurt myself",
    "kill myself",
    "don't want to live",
    "not want to live",
    "not wanting to be alive",
    "burden",
    "gayab",
    "jeena nahi",
    "nuksan",
    "khatam",
    "mar jana",
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


def build_extractor_examples(
    conversations: list[dict[str, Any]],
    *,
    schema_style: str = "compact",
) -> list[dict[str, Any]]:
    examples = []
    for conversation in conversations:
        prompt = _extractor_prompt(conversation, schema_style=schema_style)
        response = json.dumps(_extractor_target(conversation, schema_style=schema_style), ensure_ascii=False)
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


def build_best_extractor_train_examples(
    multilingual_examples: list[dict[str, Any]],
    auxiliary_english_examples: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for example in multilingual_examples:
        by_language[example.get("language", "en")].append(example)

    language_weights = {"en": 1, "hi": 2, "hinglish": 2}
    rebalanced: list[dict[str, Any]] = []
    for language in ("en", "hi", "hinglish"):
        bucket = by_language.get(language, [])
        repeats = language_weights.get(language, 1)
        for _ in range(repeats):
            rebalanced.extend(dict(example) for example in bucket)

    if auxiliary_english_examples:
        aux_cap = max(1, round(len(rebalanced) * 0.5))
        rebalanced.extend(dict(example) for example in auxiliary_english_examples[:aux_cap])

    return _interleave_by_language(rebalanced)


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
        user_turns = [
            turn["text"] for turn in conversation.get("conversation_turns", []) if turn["speaker"] == "user"
        ]
        safety = conversation.get("safety_flag", {})
        label = safety.get("level", "none")
        cues = safety.get("cues", [])
        for suffix, text in _build_safety_views(user_turns, cues, label):
            examples.append(
                {
                    "id": conversation["conversation_id"] if suffix == "full" else f"{conversation['conversation_id']}-{suffix}",
                    "task": "safety",
                    "language": conversation["language"],
                    "text": text,
                    "label": label,
                    "cues": cues,
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


def _extractor_prompt(conversation: dict[str, Any], *, schema_style: str = "compact") -> str:
    transcript = _transcript_text(conversation.get("conversation_turns", []))
    item_lines = "\n".join(
        f"- {item_id}: {item.label} ({item.focus})"
        for item_id, item in ITEM_INDEX.items()
    )
    schema_instructions = (
        "Return JSON with keys: items, safety_level.\n"
        "items must be a list of objects with item_id and value only.\n"
        "Only include supported items in items.\n"
        "Only include items with value 1, 2, or 3.\n"
        "safety_level must be one of none, review, urgent."
    )
    if schema_style != "compact":
        schema_instructions = (
            "Return JSON with items, safety_level, safety_cues, notes.\n"
            "Only include supported items in items.\n"
        )
    return (
        f"Language: {conversation['language']}\n"
        f"Use these item ids:\n{item_lines}\n\n"
        f"{schema_instructions}\n"
        f"Transcript:\n{transcript}"
    )


def _extractor_target(conversation: dict[str, Any], *, schema_style: str = "compact") -> dict[str, Any]:
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
        if schema_style == "compact":
            items.append({"item_id": item_id, "value": value})
        else:
            items.append(
                {
                    "item_id": item_id,
                    "value": value,
                    "evidence_quote": spans[0]["text_span"] if spans else "",
                    "confidence_note": conversation.get("annotator_notes", "") or "Annotated seed evidence.",
                }
            )

    target = {
        "items": items,
        "safety_level": conversation.get("safety_flag", {}).get("level", "none"),
    }
    if schema_style != "compact":
        target["safety_cues"] = conversation.get("safety_flag", {}).get("cues", [])
        target["notes"] = conversation.get("annotator_notes", "")
    return target


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


def _interleave_by_language(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        buckets[record.get("language", "en")].append(record)

    ordered: list[dict[str, Any]] = []
    active = True
    while active:
        active = False
        for language in ("en", "hi", "hinglish"):
            bucket = buckets.get(language, [])
            if bucket:
                ordered.append(bucket.pop(0))
                active = True
    return ordered


def _build_safety_views(user_turns: list[str], cues: list[str], label: str) -> list[tuple[str, str]]:
    full_text = "\n".join(turn.strip() for turn in user_turns if turn.strip()).strip()
    if not full_text:
        return [("full", "")]

    recent_turns = "\n".join(user_turns[-2:]).strip()
    latest_turn = user_turns[-1].strip()
    tail = _tail_words(full_text, 96)
    cue_lines = _cue_lines(user_turns, cues)

    base_sections = [f"Most recent disclosure:\n{latest_turn}"]
    if recent_turns and recent_turns != latest_turn:
        base_sections.append(f"Recent context:\n{recent_turns}")
    if cue_lines:
        base_sections.append(f"Risk-focused lines:\n{cue_lines}")
    if tail and tail not in recent_turns:
        base_sections.append(f"Conversation tail:\n{tail}")

    views: list[tuple[str, str]] = [("full", "\n\n".join(base_sections))]
    if label != "none":
        views.append(("recent", recent_turns or latest_turn))
        if cue_lines:
            views.append(("cue", cue_lines))
        if tail and tail not in {recent_turns, latest_turn, cue_lines}:
            views.append(("tail", tail))

    deduped: list[tuple[str, str]] = []
    seen = set()
    for suffix, text in views:
        normalized = " ".join(text.split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append((suffix, text))
    return deduped


def _tail_words(text: str, count: int) -> str:
    words = text.split()
    if len(words) <= count:
        return text
    return " ".join(words[-count:])


def _cue_lines(user_turns: list[str], cues: list[str]) -> str:
    cue_terms = {cue.replace("_", " ").lower() for cue in cues}
    cue_terms.update(SAFETY_KEYWORDS)
    matched = []
    for turn in user_turns:
        lowered = turn.lower()
        if any(term in lowered for term in cue_terms):
            matched.append(turn.strip())
    return "\n".join(dict.fromkeys(matched))
