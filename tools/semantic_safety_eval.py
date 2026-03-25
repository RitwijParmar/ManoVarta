#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.semantic_safety import SemanticSafetyConfig, SemanticSafetyMonitor
from manovarta_core.seed_data import load_seed_conversations
from manovarta_core.schemas import Turn


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate an optional semantic safety encoder on the seed corpus.")
    parser.add_argument("--model", default="google/muril-base-cased")
    parser.add_argument("--review-threshold", type=float, default=0.64)
    parser.add_argument("--urgent-threshold", type=float, default=0.72)
    args = parser.parse_args()

    monitor = SemanticSafetyMonitor(
        SemanticSafetyConfig(
            model_name=args.model,
            review_threshold=args.review_threshold,
            urgent_threshold=args.urgent_threshold,
        )
    )
    if not monitor.enabled:
        raise SystemExit("Semantic safety monitor is not enabled.")

    reports = []
    for conversation in load_seed_conversations():
        turns = [
            Turn(
                turn_id=turn["turn_id"],
                speaker=turn["speaker"],
                text=turn["text"],
                language_tag=turn["language_tag"],
            )
            for turn in conversation.get("conversation_turns", [])
        ]
        flag = monitor.assess(turns)
        review_score = next(
            (float(cue.split(":", 1)[1]) for cue in flag.cues if cue.startswith("review_score:")),
            0.0,
        )
        urgent_score = next(
            (float(cue.split(":", 1)[1]) for cue in flag.cues if cue.startswith("urgent_score:")),
            0.0,
        )

        reports.append(
            {
                "conversation_id": conversation["conversation_id"],
                "language": conversation["language"],
                "gold_level": conversation.get("safety_flag", {}).get("level", "none"),
                "predicted_level": flag.level,
                "review_score": round(review_score, 3),
                "urgent_score": round(urgent_score, 3),
            }
        )

    print(
        json.dumps(
            {
                "model": args.model,
                "review_threshold": args.review_threshold,
                "urgent_threshold": args.urgent_threshold,
                "reports": reports,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
