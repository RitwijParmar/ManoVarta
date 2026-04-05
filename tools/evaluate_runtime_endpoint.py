#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.json_utils import normalize_safety_level, parse_extractor_payload
from manovarta_core.metrics import evaluate_item_predictions
from manovarta_core.safety_assessors import build_turns_from_extractor_example


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a public or local ManoVarta runtime endpoint on extractor_test.jsonl.")
    parser.add_argument(
        "--base-url",
        default="https://manovarta-runtime-122722888597.us-east4.run.app",
        help="Runtime base URL exposing /screen/transcript.",
    )
    parser.add_argument(
        "--eval-file",
        default=str(PROJECT_ROOT / "data" / "processed" / "extractor_test.jsonl"),
    )
    parser.add_argument(
        "--output-json",
        default=str(PROJECT_ROOT / "reports" / "live_runtime_eval_20260404.json"),
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def post_json(url: str, payload: dict, timeout: float) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_gold_index(examples: list[dict]) -> dict[str, dict]:
    gold_index = {}
    for example in examples:
        gold = parse_extractor_payload(example["response"]) or {"items": [], "safety_level": "none"}
        item_map = {item["item_id"]: item["value"] for item in gold.get("items", []) if "item_id" in item}
        gold_index[example["id"]] = {
            "conversation_id": example["id"],
            "language": example["language"],
            "phq9_item_labels": {item_id: value for item_id, value in item_map.items() if item_id.startswith("phq_")},
            "gad7_item_labels": {item_id: value for item_id, value in item_map.items() if item_id.startswith("gad_")},
            "safety_flag": {"level": normalize_safety_level(gold.get("safety_level", "none"))},
        }
    return gold_index


def build_item_breakdowns(gold_index: dict[str, dict], predictions: list[dict]) -> tuple[dict, dict]:
    predicted_index = {record["conversation_id"]: record for record in predictions}
    per_item = {}
    per_language = {}

    for conversation_id, gold in gold_index.items():
        prediction = predicted_index.get(conversation_id, {"predictions": {}})
        predicted_labels = prediction.get("predictions", {})
        language = gold["language"]
        gold_labels = {}
        gold_labels.update(gold.get("phq9_item_labels", {}))
        gold_labels.update(gold.get("gad7_item_labels", {}))

        language_bucket = per_language.setdefault(language, {})
        for item_id, gold_value in gold_labels.items():
            item_bucket = per_item.setdefault(item_id, {"gold_count": 0, "covered_count": 0, "exact_count": 0, "predicted_values": []})
            lang_bucket = language_bucket.setdefault(item_id, {"gold_count": 0, "covered_count": 0, "exact_count": 0, "predicted_values": []})
            pred_value = predicted_labels.get(item_id)

            item_bucket["gold_count"] += 1
            lang_bucket["gold_count"] += 1
            if pred_value is None:
                continue

            item_bucket["covered_count"] += 1
            lang_bucket["covered_count"] += 1
            item_bucket["predicted_values"].append(pred_value)
            lang_bucket["predicted_values"].append(pred_value)
            if pred_value == gold_value:
                item_bucket["exact_count"] += 1
                lang_bucket["exact_count"] += 1

    return _finalize_item_breakdown(per_item), {
        language: _finalize_item_breakdown(items)
        for language, items in per_language.items()
    }


def _finalize_item_breakdown(buckets: dict) -> dict:
    finalized = {}
    for item_id, bucket in buckets.items():
        gold_count = bucket["gold_count"]
        covered_count = bucket["covered_count"]
        finalized[item_id] = {
            "gold_count": gold_count,
            "covered_count": covered_count,
            "coverage": round(covered_count / gold_count, 3) if gold_count else 0.0,
            "exact_rate_when_covered": round(bucket["exact_count"] / covered_count, 3) if covered_count else 0.0,
            "predicted_values": bucket["predicted_values"],
        }
    return finalized


def main() -> int:
    args = parse_args()
    eval_path = Path(args.eval_file)
    output_path = Path(args.output_json)
    examples = [json.loads(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    gold_index = build_gold_index(examples)
    predictions = []

    for index, example in enumerate(examples, start=1):
        turns = build_turns_from_extractor_example(example)
        payload = {
            "language": example["language"],
            "turns": [
                {
                    "turn_id": turn.turn_id,
                    "speaker": turn.speaker,
                    "text": turn.text,
                    "language_tag": turn.language_tag,
                }
                for turn in turns
            ],
        }
        response = post_json(args.base_url.rstrip("/") + "/screen/transcript", payload, timeout=args.timeout)
        snapshot = response["snapshot"]
        predictions.append(
            {
                "conversation_id": example["id"],
                "predictions": {
                    item_id: item["value"]
                    for item_id, item in snapshot["items"].items()
                    if item.get("value") is not None
                },
                "safety_level": normalize_safety_level(snapshot["safety"]["level"]),
            }
        )
        print(
            f"evaluated {index}/{len(examples)} recent={example['id']} "
            f"safety={snapshot['safety']['level']}",
            flush=True,
        )

    summary = evaluate_item_predictions(list(gold_index.values()), predictions)
    per_item, per_language_items = build_item_breakdowns(gold_index, predictions)
    summary.update(
        {
            "model_path": args.base_url.rstrip("/") + "/screen/transcript",
            "example_count": len(examples),
            "completed_count": len(predictions),
            "offset": 0,
            "parse_failures": 0,
            "parse_failure_ids": [],
            "last_completed_id": examples[-1]["id"] if examples else None,
            "status": "completed",
            "evaluation_mode": "runtime_endpoint",
            "per_item": per_item,
            "per_language_items": per_language_items,
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
