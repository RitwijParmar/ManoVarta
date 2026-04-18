#!/usr/bin/env python3
import argparse
import os
import sys
from contextlib import contextmanager
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.config import get_runtime_config
from manovarta_core.gold_data import load_gold_conversations
from manovarta_core.llm import HuggingFaceExtractor
from manovarta_core.metrics import evaluate_item_predictions
from manovarta_core.seed_data import load_seed_conversations
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import Turn


def load_eval_conversations(source: str):
    if source == "seed":
        return load_seed_conversations()
    if source == "gold-core":
        return load_gold_conversations(include_hindi_pilot=False, gold_core_only=True)
    if source == "gold":
        return load_gold_conversations(include_hindi_pilot=True, gold_core_only=False)
    if source == "hybrid":
        return [
            *load_seed_conversations(),
            *load_gold_conversations(include_hindi_pilot=True, gold_core_only=False),
        ]
    raise ValueError(f"Unsupported evaluation source: {source}")


def build_turns(payload):
    return [
        Turn(
            turn_id=_normalize_turn_id(turn["turn_id"]),
            speaker=turn["speaker"],
            text=turn["text"],
            language_tag=turn["language_tag"],
        )
        for turn in payload["conversation_turns"]
    ]


def _normalize_turn_id(value):
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    digits = "".join(char for char in text if char.isdigit())
    return int(digits) if digits else 0


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
                "safety_level": snapshot.safety.level,
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
                "safety_level": result.get("safety_level", "none"),
                "raw": result,
            }
        )
    return predictions


@contextmanager
def temporary_env(name, value):
    old = os.getenv(name)
    if value is None:
        yield
        return
    os.environ[name] = value
    try:
        get_runtime_config.cache_clear()
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old
        get_runtime_config.cache_clear()


def summarize(conversations, predictions, mode):
    report = evaluate_item_predictions(conversations, predictions)
    report["mode"] = mode
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate seed, gold-core, gold, or hybrid conversations against current runtime.")
    parser.add_argument("--mode", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--model", help="Optional override for MANOVARTA_EXTRACTION_MODEL in llm mode.")
    parser.add_argument("--source", choices=["seed", "gold-core", "gold", "hybrid"], default="gold-core")
    args = parser.parse_args()

    conversations = load_eval_conversations(args.source)
    with temporary_env("MANOVARTA_EXTRACTION_MODEL", args.model):
        if args.mode == "heuristic":
            predictions = evaluate_heuristic(conversations)
        else:
            predictions = evaluate_llm(conversations)

        report = summarize(conversations, predictions, args.mode)
        if args.mode == "llm":
            report["model"] = get_runtime_config().extraction_model
        report["source"] = args.source
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
