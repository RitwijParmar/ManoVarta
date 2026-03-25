#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles


def main() -> int:
    profiles = load_seed_profiles()
    conversations = load_seed_conversations()
    profile_ids = {profile["patient_id"] for profile in profiles}
    errors: list[str] = []

    for conversation in conversations:
        patient_id = conversation.get("patient_id")
        if patient_id and patient_id not in profile_ids:
            errors.append(f"{conversation['conversation_id']}: unknown patient_id {patient_id}")

        turn_ids = {turn["turn_id"] for turn in conversation.get("conversation_turns", [])}
        if len(turn_ids) != len(conversation.get("conversation_turns", [])):
            errors.append(f"{conversation['conversation_id']}: duplicate turn ids")

        for span in conversation.get("evidence_spans", []):
            if span["turn_id"] not in turn_ids:
                errors.append(f"{conversation['conversation_id']}: span {span['span_id']} points to missing turn")
            if span["score_hint"] < 0 or span["score_hint"] > 3:
                errors.append(f"{conversation['conversation_id']}: span {span['span_id']} has invalid score_hint")

        for label_group in ("phq9_item_labels", "gad7_item_labels"):
            for item_id, value in conversation.get(label_group, {}).items():
                if value < 0 or value > 3:
                    errors.append(f"{conversation['conversation_id']}: {item_id} label out of range")

    languages = Counter(conversation["language"] for conversation in conversations)
    print("profiles", len(profiles))
    print("conversations", len(conversations))
    print("languages", dict(languages))
    if errors:
        for error in errors:
            print("ERROR", error)
        return 1
    print("seed data valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
