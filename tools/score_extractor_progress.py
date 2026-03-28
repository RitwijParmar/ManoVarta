#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.json_utils import parse_extractor_payload
from manovarta_core.metrics import evaluate_item_predictions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score uploaded extractor progress.jsonl against a held-out eval JSONL.")
    parser.add_argument("--progress-file", required=True)
    parser.add_argument("--eval-file", required=True)
    return parser.parse_args()


def build_gold_records(examples: list[dict]) -> list[dict]:
    gold_records: list[dict] = []
    for example in examples:
        parsed = parse_extractor_payload(example["response"]) or {"items": [], "safety_level": "none"}
        item_map = {item["item_id"]: item["value"] for item in parsed.get("items", []) if "item_id" in item}
        gold_records.append(
            {
                "conversation_id": example["id"],
                "language": example["language"],
                "phq9_item_labels": {item_id: value for item_id, value in item_map.items() if item_id.startswith("phq_")},
                "gad7_item_labels": {item_id: value for item_id, value in item_map.items() if item_id.startswith("gad_")},
                "safety_flag": {"level": parsed.get("safety_level", "none")},
            }
        )
    return gold_records


def main() -> int:
    args = parse_args()
    progress_rows = [
        json.loads(line)
        for line in Path(args.progress_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    examples = [
        json.loads(line)
        for line in Path(args.eval_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    completed_ids = {row["conversation_id"] for row in progress_rows}
    gold_records = [record for record in build_gold_records(examples) if record["conversation_id"] in completed_ids]
    predictions = [
        {
            "conversation_id": row["conversation_id"],
            "predictions": row.get("predictions", {}),
            "safety_level": row.get("safety_level", "none"),
        }
        for row in progress_rows
    ]
    report = evaluate_item_predictions(gold_records, predictions)
    report["completed_count"] = len(progress_rows)
    report["example_count"] = len(examples)
    report["parse_failures"] = sum(1 for row in progress_rows if not row.get("parsed_ok"))
    report["parse_failure_ids"] = [row["conversation_id"] for row in progress_rows if not row.get("parsed_ok")]
    report["last_completed_id"] = progress_rows[-1]["conversation_id"] if progress_rows else None
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
