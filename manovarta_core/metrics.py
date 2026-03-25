from __future__ import annotations

from collections import defaultdict
from typing import Any


SAFETY_POSITIVE = {"review", "urgent"}


def evaluate_item_predictions(
    gold_records: list[dict[str, Any]],
    predicted_records: list[dict[str, Any]],
) -> dict[str, Any]:
    predicted_index = {record["conversation_id"]: record for record in predicted_records}
    per_language = defaultdict(_bucket)
    overall = _bucket()

    for gold in gold_records:
        prediction = predicted_index.get(gold["conversation_id"], {"predictions": {}, "safety_level": "none"})
        gold_labels = {}
        gold_labels.update(gold.get("phq9_item_labels", {}))
        gold_labels.update(gold.get("gad7_item_labels", {}))
        predicted_labels = prediction.get("predictions", {})
        bucket = per_language[gold["language"]]

        for item_id, gold_value in gold_labels.items():
            pred_value = predicted_labels.get(item_id)
            _update_item_metrics(bucket, gold_value, pred_value)
            _update_item_metrics(overall, gold_value, pred_value)

        gold_safety = gold.get("safety_flag", {}).get("level", "none")
        pred_safety = prediction.get("safety_level", "none")
        _update_safety(bucket, gold_safety, pred_safety)
        _update_safety(overall, gold_safety, pred_safety)

    return {
        "overall": _finalize(overall),
        "languages": {language: _finalize(bucket) for language, bucket in per_language.items()},
    }


def _bucket() -> dict[str, Any]:
    return {
        "items_total": 0,
        "items_covered": 0,
        "absolute_error": 0,
        "exact": 0,
        "labels": defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0}),
        "safety_tp": 0,
        "safety_fp": 0,
        "safety_fn": 0,
    }


def _update_item_metrics(bucket: dict[str, Any], gold_value: int, pred_value: int | None) -> None:
    bucket["items_total"] += 1
    if pred_value is None:
        bucket["labels"][gold_value]["fn"] += 1
        return

    bucket["items_covered"] += 1
    bucket["absolute_error"] += abs(pred_value - gold_value)
    if pred_value == gold_value:
        bucket["exact"] += 1
        bucket["labels"][gold_value]["tp"] += 1
        return

    bucket["labels"][gold_value]["fn"] += 1
    bucket["labels"][pred_value]["fp"] += 1


def _update_safety(bucket: dict[str, Any], gold_level: str, pred_level: str) -> None:
    gold_positive = gold_level in SAFETY_POSITIVE
    pred_positive = pred_level in SAFETY_POSITIVE
    if gold_positive and pred_positive:
        bucket["safety_tp"] += 1
    elif pred_positive and not gold_positive:
        bucket["safety_fp"] += 1
    elif gold_positive and not pred_positive:
        bucket["safety_fn"] += 1


def _finalize(bucket: dict[str, Any]) -> dict[str, Any]:
    covered = bucket["items_covered"]
    labels = bucket["labels"]
    f1_scores = []
    for label in (0, 1, 2, 3):
        tp = labels[label]["tp"]
        fp = labels[label]["fp"]
        fn = labels[label]["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        f1_scores.append(f1)

    safety_precision = bucket["safety_tp"] / (bucket["safety_tp"] + bucket["safety_fp"]) if bucket["safety_tp"] + bucket["safety_fp"] else 0.0
    safety_recall = bucket["safety_tp"] / (bucket["safety_tp"] + bucket["safety_fn"]) if bucket["safety_tp"] + bucket["safety_fn"] else 0.0

    return {
        "covered_items": covered,
        "coverage_completeness": round(covered / bucket["items_total"], 3) if bucket["items_total"] else 0.0,
        "mae": round(bucket["absolute_error"] / covered, 3) if covered else None,
        "exact_match_rate": round(bucket["exact"] / covered, 3) if covered else None,
        "macro_f1": round(sum(f1_scores) / len(f1_scores), 3),
        "safety_precision": round(safety_precision, 3),
        "safety_recall": round(safety_recall, 3),
    }
