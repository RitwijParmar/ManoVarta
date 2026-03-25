#!/usr/bin/env python3
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.config import get_runtime_config
from manovarta_core.llm import HuggingFaceExtractor
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import Turn


def load_gold_conversations():
    path = PROJECT_ROOT / "data" / "seed" / "conversations.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_turns(payload):
    return [
        Turn(
            turn_id=turn["turn_id"],
            speaker=turn["speaker"],
            text=turn["text"],
            language_tag=turn["language_tag"],
        )
        for turn in payload["conversation_turns"]
    ]


def gold_labels(payload):
    labels = {}
    labels.update(payload.get("phq9_item_labels", {}))
    labels.update(payload.get("gad7_item_labels", {}))
    return labels


def evaluate_heuristic(conversations):
    scorer = ConversationScorer()
    safety_monitor = SafetyMonitor()
    predictions = []
    for payload in conversations:
        turns = build_turns(payload)
        snapshot = scorer.analyze(turns, payload["language"], safety_monitor.assess(turns))
        predictions.append(
            {
                "conversation_id": payload["conversation_id"],
                "language": payload["language"],
                "predictions": {item_id: item.value for item_id, item in snapshot.items.items()},
            }
        )
    return predictions


def evaluate_llm(conversations):
    config = get_runtime_config()
    extractor = HuggingFaceExtractor(config)
    if not extractor.enabled:
        raise RuntimeError("HF_TOKEN is missing. LLM evaluation cannot run.")

    predictions = []
    for payload in conversations:
        turns = build_turns(payload)
        result = extractor.extract(turns, payload["language"]) or {}
        item_map = {item["item_id"]: item["value"] for item in result.get("items", []) if "item_id" in item}
        predictions.append(
            {
                "conversation_id": payload["conversation_id"],
                "language": payload["language"],
                "predictions": item_map,
                "raw": result,
            }
        )
    return predictions


def summarize(conversations, predictions, mode):
    per_language = defaultdict(lambda: {"covered": 0, "exact": 0, "absolute_error": 0, "count": 0})
    for payload, predicted in zip(conversations, predictions):
        gold = gold_labels(payload)
        for item_id, gold_value in gold.items():
            pred_value = predicted["predictions"].get(item_id)
            if pred_value is None:
                continue
            bucket = per_language[payload["language"]]
            bucket["covered"] += 1
            bucket["count"] += 1
            bucket["absolute_error"] += abs(pred_value - gold_value)
            if pred_value == gold_value:
                bucket["exact"] += 1

    report = {"mode": mode, "languages": {}}
    for language, values in per_language.items():
        covered = values["covered"]
        report["languages"][language] = {
            "covered_items": covered,
            "mae": round(values["absolute_error"] / covered, 3) if covered else None,
            "exact_match_rate": round(values["exact"] / covered, 3) if covered else None,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate seed conversations against current runtime.")
    parser.add_argument("--mode", choices=["heuristic", "llm"], default="heuristic")
    args = parser.parse_args()

    conversations = load_gold_conversations()
    if args.mode == "heuristic":
        predictions = evaluate_heuristic(conversations)
    else:
        predictions = evaluate_llm(conversations)

    report = summarize(conversations, predictions, args.mode)
    if args.mode == "llm":
        report["model"] = get_runtime_config().extraction_model
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
