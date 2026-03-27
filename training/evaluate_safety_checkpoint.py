#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


LABELS = ["none", "review", "urgent"]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a fine-tuned safety checkpoint on a held-out JSONL file.")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--max-length", type=int, default=256)
    return parser.parse_args()


def macro_f1(gold: list[str], pred: list[str]) -> float:
    scores = []
    for label in LABELS:
        tp = sum(1 for g, p in zip(gold, pred) if g == label and p == label)
        fp = sum(1 for g, p in zip(gold, pred) if g != label and p == label)
        fn = sum(1 for g, p in zip(gold, pred) if g == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        if precision + recall == 0:
            scores.append(0.0)
        else:
            scores.append(2 * precision * recall / (precision + recall))
    return round(sum(scores) / len(scores), 4)


def main() -> int:
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install training extras first: pip install -e .[train]") from exc

    from training.runtime_utils import detect_device

    args = parse_args()
    device = detect_device(torch, args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_path, trust_remote_code=True)
    if device != "cpu":
        model.to(device)
    model.eval()

    examples = [
        json.loads(line)
        for line in Path(args.eval_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gold = [example["label"] for example in examples]
    pred = []
    mistakes = []

    for example in examples:
        encoded = tokenizer(
            example["text"],
            truncation=True,
            max_length=args.max_length,
            return_tensors="pt",
        )
        if device != "cpu":
            encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
        label_id = int(logits.argmax(dim=-1).item())
        predicted = model.config.id2label.get(label_id, str(label_id)).lower()
        pred.append(predicted)
        if predicted != example["label"]:
            mistakes.append(
                {
                    "id": example["id"],
                    "gold": example["label"],
                    "predicted": predicted,
                }
            )

    accuracy = round(sum(1 for g, p in zip(gold, pred) if g == p) / max(len(gold), 1), 4)
    report = {
        "model_path": str(Path(args.model_path).resolve()),
        "device": device,
        "examples": len(examples),
        "accuracy": accuracy,
        "macro_f1": macro_f1(gold, pred),
        "gold_counts": dict(Counter(gold)),
        "predicted_counts": dict(Counter(pred)),
        "mistakes": mistakes[:20],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
