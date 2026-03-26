#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles


def main() -> int:
    parser = argparse.ArgumentParser(description="Export seed conversations into JSONL annotation packets.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data" / "seed" / "annotation_packets.jsonl"),
        help="Output JSONL path.",
    )
    args = parser.parse_args()

    profiles = {profile["patient_id"]: profile for profile in load_seed_profiles()}
    conversations = load_seed_conversations()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for conversation in conversations:
            profile = profiles.get(conversation.get("patient_id"), {})
            packet = {
                "conversation_id": conversation["conversation_id"],
                "patient_id": conversation.get("patient_id"),
                "language": conversation["language"],
                "review_status": conversation.get("review_status", "draft"),
                "nuance_tags": profile.get("nuance_tags", []),
                "seed_metadata": profile.get("seed_metadata", {}),
                "conversation_metadata": conversation.get("conversation_metadata", {}),
                "background_profile": conversation.get("background_profile", {}),
                "symptom_profile": conversation.get("symptom_profile", {}),
                "turns": [
                    {
                        "turn_id": turn["turn_id"],
                        "speaker": turn["speaker"],
                        "text": turn["text"],
                    }
                    for turn in conversation.get("conversation_turns", [])
                ],
                "annotation_template": {
                    "evidence_spans": [],
                    "phq9_item_labels": {},
                    "gad7_item_labels": {},
                    "safety_flag": {"level": "none", "cues": []},
                    "annotator_notes": "",
                    "confidence_notes": {"high_confidence_items": [], "low_confidence_items": []},
                },
            }
            handle.write(json.dumps(packet, ensure_ascii=False) + "\n")

    print(f"wrote {len(conversations)} packets to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
