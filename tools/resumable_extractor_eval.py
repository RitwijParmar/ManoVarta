#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.json_utils import parse_json_object
from manovarta_core.metrics import evaluate_item_predictions
from manovarta_core.seed_data import load_seed_conversations


def parse_args():
    parser = argparse.ArgumentParser(description="Run resumable extractor evaluation and persist progress after each example.")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=1200)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--stop-on-parse-failure", action="store_true")
    parser.add_argument("--max-parse-failures", type=int, default=None)
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
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / "progress.jsonl"
    summary_path = output_dir / "summary.json"
    raw_dir = output_dir / "raw_generations"
    raw_dir.mkdir(parents=True, exist_ok=True)

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
    if args.offset:
        examples = examples[args.offset:]
    if args.limit is not None:
        examples = examples[:args.limit]

    completed_ids, prior_rows = load_existing_progress(progress_path)
    todo_examples = [example for example in examples if example["id"] not in completed_ids]
    gold_index = {record["conversation_id"]: record for record in load_seed_conversations()}

    stopped_due_to_parse_failure = False
    for index, example in enumerate(todo_examples, start=1):
        prompt = example["text"].rsplit("<|assistant|>", 1)[0] + "<|assistant|>\n"
        tokens = tokenizer(prompt, return_tensors="pt")
        target_device = model.device if hasattr(model, "device") else torch.device(device)
        tokens = {key: value.to(target_device) for key, value in tokens.items()}
        with torch.no_grad():
            output_ids = model.generate(
                **tokens,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        completion = tokenizer.decode(output_ids[0][tokens["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
        parsed = parse_json_object(completion)
        row = {
            "conversation_id": example["id"],
            "parsed_ok": parsed is not None,
            "raw_path": str((raw_dir / f"{example['id']}.txt").resolve()),
            "safety_level": (parsed or {}).get("safety_level", "none"),
            "predictions": {
                item["item_id"]: item["value"]
                for item in (parsed or {}).get("items", [])
                if "item_id" in item
            },
        }
        (raw_dir / f"{example['id']}.txt").write_text(completion, encoding="utf-8")
        append_jsonl(progress_path, row)
        prior_rows.append(row)

        summary = build_summary(prior_rows, examples, gold_index, model_path, args.offset)
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            f"processed {len(prior_rows)}/{len(examples)} "
            f"recent={example['id']} parsed_ok={row['parsed_ok']} "
            f"parse_failures={summary['parse_failures']}",
            flush=True,
        )

        should_stop = False
        if not row["parsed_ok"] and args.stop_on_parse_failure:
            should_stop = True
        if args.max_parse_failures is not None and summary["parse_failures"] >= args.max_parse_failures:
            should_stop = True
        if should_stop:
            stopped_due_to_parse_failure = True
            print(
                f"stopping after parse failure recent={example['id']} "
                f"parse_failures={summary['parse_failures']} raw={row['raw_path']}",
                flush=True,
            )
            break

    final_summary = build_summary(prior_rows, examples, gold_index, model_path, args.offset)
    if stopped_due_to_parse_failure:
        final_summary["status"] = "stopped_on_parse_failure"
    elif final_summary["completed_count"] < final_summary["example_count"]:
        final_summary["status"] = "partial"
    else:
        final_summary["status"] = "completed"
    summary_path.write_text(json.dumps(final_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(final_summary, indent=2, ensure_ascii=False))
    return 2 if stopped_due_to_parse_failure else 0


def load_existing_progress(progress_path: Path) -> tuple[set[str], list[dict]]:
    if not progress_path.exists():
        return set(), []
    rows = [json.loads(line) for line in progress_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    completed_ids = {row["conversation_id"] for row in rows}
    return completed_ids, rows


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_summary(
    rows: list[dict],
    examples: list[dict],
    gold_index: dict[str, dict],
    model_path: Path,
    offset: int,
) -> dict:
    completed_ids = {row["conversation_id"] for row in rows}
    gold_records = [gold_index[example["id"]] for example in examples if example["id"] in completed_ids and example["id"] in gold_index]
    predictions = [
        {
            "conversation_id": row["conversation_id"],
            "predictions": row.get("predictions", {}),
            "safety_level": row.get("safety_level", "none"),
        }
        for row in rows
        if row["conversation_id"] in completed_ids
    ]
    report = evaluate_item_predictions(gold_records, predictions)
    report["model_path"] = str(model_path.resolve())
    report["example_count"] = len(examples)
    report["completed_count"] = len(rows)
    report["offset"] = offset
    report["parse_failures"] = sum(1 for row in rows if not row.get("parsed_ok"))
    report["parse_failure_ids"] = [row["conversation_id"] for row in rows if not row.get("parsed_ok")]
    report["last_completed_id"] = rows[-1]["conversation_id"] if rows else None
    return report


if __name__ == "__main__":
    raise SystemExit(main())
