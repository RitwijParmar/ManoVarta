#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.json_utils import parse_extractor_payload
from manovarta_core.metrics import evaluate_item_predictions
from manovarta_core.safety_assessors import (
    LocalSafetyCheckpointAssessor,
    build_turns_from_extractor_example,
    evaluate_safety_stack,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a fine-tuned extractor checkpoint on a held-out JSONL file.")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=1200)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--hf-token", default=None)
    parser.add_argument("--use-rule-safety-monitor", action="store_true")
    parser.add_argument("--safety-checkpoint", default=None)
    return parser.parse_args()


def main() -> int:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftConfig, PeftModel
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install training extras first: pip install -e .[train]") from exc

    from training.runtime_utils import detect_device, pick_model_dtype

    args = parse_args()
    device = detect_device(torch, args.device)
    model_path = Path(args.model_path)
    adapter_config = model_path / "adapter_config.json"
    hf_token = args.hf_token
    model_kwargs = {
        "trust_remote_code": True,
    }
    if hf_token:
        model_kwargs["token"] = hf_token
    if device == "cuda":
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = pick_model_dtype(torch, device)
        model_kwargs["low_cpu_mem_usage"] = True
    if adapter_config.exists():
        peft_config = PeftConfig.from_pretrained(args.model_path, token=hf_token)
        base_model_path = peft_config.base_model_name_or_path
        tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True, token=hf_token)
        base_model = AutoModelForCausalLM.from_pretrained(base_model_path, **model_kwargs)
        model = PeftModel.from_pretrained(base_model, args.model_path, token=hf_token)
    else:
        tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True, token=hf_token)
        model = AutoModelForCausalLM.from_pretrained(args.model_path, **model_kwargs)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    if device != "cuda":
        model.to(device)
    model.eval()

    eval_path = Path(args.eval_file)
    examples = [json.loads(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.offset:
        examples = examples[args.offset:]
    if args.limit is not None:
        examples = examples[:args.limit]
    predictions = []
    gold_records = []
    safety_assessor = LocalSafetyCheckpointAssessor(args.safety_checkpoint, device=args.device)

    for example in examples:
        prompt = example["text"].rsplit("<|assistant|>", 1)[0] + "<|assistant|>\n"
        tokens = tokenizer(prompt, return_tensors="pt")
        target_device = model.device if hasattr(model, "device") else torch.device(device)
        tokens = {key: value.to(target_device) for key, value in tokens.items()}
        with torch.no_grad():
            output_ids = model.generate(**tokens, max_new_tokens=args.max_new_tokens, do_sample=False)
        completion = tokenizer.decode(output_ids[0][tokens["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
        parsed = parse_extractor_payload(completion) or {"items": [], "safety_level": "none", "notes": "parse_error"}
        gold = parse_extractor_payload(example["response"]) or {"items": [], "safety_level": "none"}
        turns = build_turns_from_extractor_example(example)
        safety_result = evaluate_safety_stack(
            extractor_safety_level=parsed.get("safety_level", "none"),
            turns=turns,
            language=example["language"],
            use_rule_safety_monitor=args.use_rule_safety_monitor,
            safety_assessor=safety_assessor,
        )
        predictions.append(
            {
                "conversation_id": example["id"],
                "predictions": {item["item_id"]: item["value"] for item in parsed.get("items", []) if "item_id" in item},
                "safety_level": safety_result["flag"].level,
            }
        )
        gold_items = {item["item_id"]: item["value"] for item in gold.get("items", []) if "item_id" in item}
        gold_records.append(
            {
                "conversation_id": example["id"],
                "language": example["language"],
                "phq9_item_labels": {item_id: value for item_id, value in gold_items.items() if item_id.startswith("phq_")},
                "gad7_item_labels": {item_id: value for item_id, value in gold_items.items() if item_id.startswith("gad_")},
                "safety_flag": {"level": gold.get("safety_level", "none")},
            }
        )

    report = evaluate_item_predictions(gold_records, predictions)
    report["model_path"] = str(Path(args.model_path).resolve())
    report["example_count"] = len(examples)
    report["offset"] = args.offset
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
