#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.metrics import evaluate_item_predictions
from manovarta_core.seed_data import load_seed_conversations


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a fine-tuned extractor checkpoint on a held-out JSONL file.")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=400)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    return parser.parse_args()


def main() -> int:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import AutoPeftModelForCausalLM
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install training extras first: pip install -e .[train]") from exc

    from training.runtime_utils import detect_device, pick_model_dtype

    args = parse_args()
    device = detect_device(torch, args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    model_path = Path(args.model_path)
    adapter_config = model_path / "adapter_config.json"
    model_kwargs = {
        "trust_remote_code": True,
    }
    if device == "cuda":
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = pick_model_dtype(torch, device)
        model_kwargs["low_cpu_mem_usage"] = True
    if adapter_config.exists():
        model = AutoPeftModelForCausalLM.from_pretrained(args.model_path, **model_kwargs)
    else:
        model = AutoModelForCausalLM.from_pretrained(args.model_path, **model_kwargs)
    if device != "cuda":
        model.to(device)
    model.eval()

    eval_path = Path(args.eval_file)
    examples = [json.loads(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    gold_index = {record["conversation_id"]: record for record in load_seed_conversations()}
    predictions = []

    for example in examples:
        prompt = example["text"].rsplit("<|assistant|>", 1)[0] + "<|assistant|>\n"
        tokens = tokenizer(prompt, return_tensors="pt")
        target_device = model.device if hasattr(model, "device") else torch.device(device)
        tokens = {key: value.to(target_device) for key, value in tokens.items()}
        with torch.no_grad():
            output_ids = model.generate(**tokens, max_new_tokens=args.max_new_tokens, do_sample=False)
        completion = tokenizer.decode(output_ids[0][tokens["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
        parsed = _safe_json(completion)
        predictions.append(
            {
                "conversation_id": example["id"],
                "predictions": {item["item_id"]: item["value"] for item in parsed.get("items", []) if "item_id" in item},
                "safety_level": parsed.get("safety_level", "none"),
            }
        )

    gold_records = [gold_index[example["id"]] for example in examples if example["id"] in gold_index]
    report = evaluate_item_predictions(gold_records, predictions)
    report["model_path"] = str(Path(args.model_path).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def _safe_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"items": [], "safety_level": "none", "notes": "parse_error"}


if __name__ == "__main__":
    raise SystemExit(main())
