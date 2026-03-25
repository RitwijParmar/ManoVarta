#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.seed_data import load_seed_conversations


REVIEW_PROTOTYPES = [
    "I wish I could disappear for a while.",
    "Sab bekaar lag raha hai aur gayab ho jana hai.",
    "Nothing feels worth it and I want to vanish.",
]

URGENT_PROTOTYPES = [
    "I want to kill myself.",
    "Mujhe jeena nahi hai aur khud ko nuksan pahunchana hai.",
    "I am planning to hurt myself tonight.",
]


def load_encoder(model_name: str):
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install optional GPU dependencies first: pip install -e .[gpu]") from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    model.eval()
    return torch, tokenizer, model


def encode_texts(torch, tokenizer, model, texts):
    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )
    with torch.no_grad():
        outputs = model(**encoded, output_hidden_states=True)
    hidden = getattr(outputs, "last_hidden_state", None)
    if hidden is None:
        hidden = outputs.hidden_states[-1]
    mask = encoded["attention_mask"].unsqueeze(-1)
    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
    return torch.nn.functional.normalize(pooled, p=2, dim=1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate an optional semantic safety encoder on the seed corpus.")
    parser.add_argument("--model", default="ai4bharat/IndicBERT-v3-1B")
    parser.add_argument("--review-threshold", type=float, default=0.64)
    parser.add_argument("--urgent-threshold", type=float, default=0.72)
    args = parser.parse_args()

    torch, tokenizer, model = load_encoder(args.model)
    review_vectors = encode_texts(torch, tokenizer, model, REVIEW_PROTOTYPES)
    urgent_vectors = encode_texts(torch, tokenizer, model, URGENT_PROTOTYPES)

    reports = []
    for conversation in load_seed_conversations():
        user_text = " ".join(
            turn["text"] for turn in conversation.get("conversation_turns", []) if turn["speaker"] == "user"
        )
        conversation_vector = encode_texts(torch, tokenizer, model, [user_text])[0]
        review_score = torch.max(review_vectors @ conversation_vector).item()
        urgent_score = torch.max(urgent_vectors @ conversation_vector).item()

        predicted = "none"
        if urgent_score >= args.urgent_threshold:
            predicted = "urgent"
        elif review_score >= args.review_threshold:
            predicted = "review"

        reports.append(
            {
                "conversation_id": conversation["conversation_id"],
                "language": conversation["language"],
                "gold_level": conversation.get("safety_flag", {}).get("level", "none"),
                "predicted_level": predicted,
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
