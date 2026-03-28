#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Aya eval artifacts on Colab and run resumable held-out evaluation.")
    parser.add_argument("--repo-id", default="ritwijar/manovarta-aya-eval-artifacts")
    parser.add_argument("--bundle-filename", default="aya_eval_upload.tar.gz")
    parser.add_argument("--repo-type", default="model")
    parser.add_argument("--hf-token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument("--work-root", default="/content")
    parser.add_argument("--output-dir", default="/content/aya_eval_outputs")
    parser.add_argument("--max-new-tokens", type=int, default=1200)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="cuda")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--stop-on-parse-failure", action="store_true", default=True)
    parser.add_argument("--max-parse-failures", type=int, default=None)
    parser.add_argument("--results-repo-id", default=None)
    parser.add_argument("--results-repo-type", default="model")
    parser.add_argument("--results-prefix", default="aya_colab_eval/latest")
    parser.add_argument("--upload-every", type=int, default=1)
    parser.add_argument("--skip-install", action="store_true")
    return parser.parse_args()


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("RUN", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=True)


def prepare_project(args: argparse.Namespace, env: dict[str, str]) -> tuple[Path, Path]:
    from huggingface_hub import hf_hub_download

    work_root = Path(args.work_root)
    artifact_root = work_root / "aya_artifacts"
    outer_root = work_root / "aya_outer"
    project_root = work_root / "aya_project"

    artifact_root.mkdir(parents=True, exist_ok=True)
    if outer_root.exists():
        shutil.rmtree(outer_root)
    if project_root.exists():
        shutil.rmtree(project_root)
    outer_root.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)

    outer_path = Path(
        hf_hub_download(
            repo_id=args.repo_id,
            filename=args.bundle_filename,
            repo_type=args.repo_type,
            token=args.hf_token,
            local_dir=str(artifact_root),
        )
    )
    with tarfile.open(outer_path, "r:gz") as tf:
        tf.extractall(outer_root)

    nested_tar = outer_root / "manovarta_eval_min.tar.gz"
    if not nested_tar.exists():
        raise SystemExit(f"Missing nested eval tar: {nested_tar}")
    with tarfile.open(nested_tar, "r:gz") as tf:
        tf.extractall(project_root)

    model_path = outer_root / "aya_bundle"
    eval_file = project_root / "data" / "processed" / "extractor_test.jsonl"
    if not (model_path / "adapter_config.json").exists():
        raise SystemExit(f"Missing Aya adapter config under {model_path}")
    if not eval_file.exists():
        raise SystemExit(f"Missing held-out eval file: {eval_file}")

    return project_root, model_path


def maybe_install_training(project_root: Path, env: dict[str, str], skip_install: bool) -> None:
    if skip_install:
        return
    run([sys.executable, "-m", "pip", "install", "-q", "-U", "pip"], env=env)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "huggingface_hub>=0.34.0,<1.0",
            "transformers>=4.45",
            "peft>=0.12.0",
            "accelerate>=0.33.0",
            "sentencepiece>=0.2.0",
            "hf_transfer",
        ],
        env=env,
    )
    run([sys.executable, "-m", "pip", "install", "-q", "-e", ".[training]"], cwd=project_root, env=env)


def load_project_modules(project_root: Path):
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from manovarta_core.json_utils import parse_extractor_payload
    from manovarta_core.metrics import evaluate_item_predictions
    from manovarta_core.seed_data import load_seed_conversations
    from training.runtime_utils import detect_device, pick_model_dtype

    return parse_extractor_payload, evaluate_item_predictions, load_seed_conversations, detect_device, pick_model_dtype


def load_existing_progress(progress_path: Path) -> tuple[set[str], list[dict]]:
    if not progress_path.exists():
        return set(), []
    rows = [json.loads(line) for line in progress_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {row["conversation_id"] for row in rows}, rows


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def maybe_upload_file(api, repo_id: str | None, repo_type: str, token: str | None, local_path: Path, path_in_repo: str) -> None:
    if not api or not repo_id or not token or not local_path.exists():
        return
    try:
        api.upload_file(
            repo_id=repo_id,
            repo_type=repo_type,
            token=token,
            path_or_fileobj=str(local_path),
            path_in_repo=path_in_repo,
        )
        print(f"uploaded {local_path.name} -> {path_in_repo}", flush=True)
    except Exception as exc:  # pragma: no cover - best effort for remote runtime
        print(f"warning: upload failed for {local_path.name}: {exc}", flush=True)


def upload_eval_state(
    api,
    args: argparse.Namespace,
    progress_path: Path,
    summary_path: Path,
    raw_path: Path | None = None,
) -> None:
    if not args.results_repo_id or not args.hf_token:
        return
    prefix = args.results_prefix.rstrip("/")
    maybe_upload_file(
        api,
        args.results_repo_id,
        args.results_repo_type,
        args.hf_token,
        progress_path,
        f"{prefix}/progress.jsonl",
    )
    maybe_upload_file(
        api,
        args.results_repo_id,
        args.results_repo_type,
        args.hf_token,
        summary_path,
        f"{prefix}/summary.json",
    )
    if raw_path is not None:
        maybe_upload_file(
            api,
            args.results_repo_id,
            args.results_repo_type,
            args.hf_token,
            raw_path,
            f"{prefix}/raw_generations/{raw_path.name}",
        )


def build_summary(
    rows: list[dict],
    examples: list[dict],
    gold_index: dict[str, dict],
    evaluate_item_predictions,
    model_path: Path,
    offset: int,
) -> dict:
    completed_ids = {row["conversation_id"] for row in rows}
    gold_records = [
        gold_index[example["id"]]
        for example in examples
        if example["id"] in completed_ids and example["id"] in gold_index
    ]
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


def build_gold_index_from_examples(examples: list[dict], parse_extractor_payload) -> dict[str, dict]:
    gold_index: dict[str, dict] = {}
    for example in examples:
        gold = parse_extractor_payload(example["response"]) or {"items": [], "safety_level": "none"}
        gold_items = {item["item_id"]: item["value"] for item in gold.get("items", []) if "item_id" in item}
        gold_index[example["id"]] = {
            "conversation_id": example["id"],
            "language": example["language"],
            "phq9_item_labels": {item_id: value for item_id, value in gold_items.items() if item_id.startswith("phq_")},
            "gad7_item_labels": {item_id: value for item_id, value in gold_items.items() if item_id.startswith("gad_")},
            "safety_flag": {"level": gold.get("safety_level", "none")},
        }
    return gold_index


def run_eval(
    args: argparse.Namespace,
    model_path: Path,
    eval_file: Path,
    project_root: Path,
    parse_extractor_payload,
    evaluate_item_predictions,
    load_seed_conversations,
    detect_device,
    pick_model_dtype,
) -> int:
    import torch
    from huggingface_hub import HfApi
    from peft import PeftConfig, PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / "progress.jsonl"
    summary_path = output_dir / "summary.json"
    raw_dir = output_dir / "raw_generations"
    raw_dir.mkdir(parents=True, exist_ok=True)
    api = HfApi() if args.results_repo_id and args.hf_token else None

    device = detect_device(torch, args.device)

    model_kwargs = {"trust_remote_code": True}
    if args.hf_token:
        model_kwargs["token"] = args.hf_token
    adapter_config = model_path / "adapter_config.json"
    if device == "cuda":
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = pick_model_dtype(torch, device)
        model_kwargs["low_cpu_mem_usage"] = True
    if adapter_config.exists():
        peft_config = PeftConfig.from_pretrained(model_path, token=args.hf_token)
        base_model_path = peft_config.base_model_name_or_path
        tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True, token=args.hf_token)
        base_model = AutoModelForCausalLM.from_pretrained(base_model_path, **model_kwargs)
        model = PeftModel.from_pretrained(base_model, model_path, token=args.hf_token)
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, token=args.hf_token)
        model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    if device != "cuda":
        model.to(device)
    model.eval()

    examples = [json.loads(line) for line in eval_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.offset:
        examples = examples[args.offset:]
    if args.limit is not None:
        examples = examples[:args.limit]

    completed_ids, prior_rows = load_existing_progress(progress_path)
    todo_examples = [example for example in examples if example["id"] not in completed_ids]
    gold_index = build_gold_index_from_examples(examples, parse_extractor_payload)

    stopped_due_to_parse_failure = False
    for example in todo_examples:
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
        completion = tokenizer.decode(output_ids[0][tokens["input_ids"].shape[-1] :], skip_special_tokens=True).strip()
        parsed = parse_extractor_payload(completion)
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
        raw_path = raw_dir / f"{example['id']}.txt"
        raw_path.write_text(completion, encoding="utf-8")
        append_jsonl(progress_path, row)
        prior_rows.append(row)

        summary = build_summary(
            prior_rows,
            examples,
            gold_index,
            evaluate_item_predictions,
            model_path,
            args.offset,
        )
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            f"processed {len(prior_rows)}/{len(examples)} "
            f"recent={example['id']} parsed_ok={row['parsed_ok']} "
            f"parse_failures={summary['parse_failures']}",
            flush=True,
        )
        if args.upload_every > 0 and len(prior_rows) % args.upload_every == 0:
            upload_eval_state(api, args, progress_path, summary_path)

        should_stop = False
        if not row["parsed_ok"] and args.stop_on_parse_failure:
            should_stop = True
        if args.max_parse_failures is not None and summary["parse_failures"] >= args.max_parse_failures:
            should_stop = True
        if should_stop:
            stopped_due_to_parse_failure = True
            upload_eval_state(api, args, progress_path, summary_path, raw_path=raw_path)
            print(
                f"stopping after parse failure recent={example['id']} "
                f"parse_failures={summary['parse_failures']} raw={row['raw_path']}",
                flush=True,
            )
            break

    final_summary = build_summary(
        prior_rows,
        examples,
        gold_index,
        evaluate_item_predictions,
        model_path,
        args.offset,
    )
    if stopped_due_to_parse_failure:
        final_summary["status"] = "stopped_on_parse_failure"
    elif final_summary["completed_count"] < final_summary["example_count"]:
        final_summary["status"] = "partial"
    else:
        final_summary["status"] = "completed"
    summary_path.write_text(json.dumps(final_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    upload_eval_state(api, args, progress_path, summary_path)
    print(json.dumps(final_summary, indent=2, ensure_ascii=False))
    return 2 if stopped_due_to_parse_failure else 0


def main() -> int:
    args = parse_args()
    if not args.hf_token:
        raise SystemExit("Provide --hf-token or set HF_TOKEN.")

    env = os.environ.copy()
    env.setdefault("HF_TOKEN", args.hf_token)
    env.setdefault("HF_HOME", str(Path(args.work_root) / ".hf_home"))
    env.setdefault("HF_HUB_CACHE", str(Path(args.work_root) / ".hf_home" / "hub"))
    env.setdefault("TRANSFORMERS_CACHE", str(Path(args.work_root) / ".hf_home" / "transformers"))
    env.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")

    project_root, model_path = prepare_project(args, env)
    maybe_install_training(project_root, env, args.skip_install)
    parse_extractor_payload, evaluate_item_predictions, load_seed_conversations, detect_device, pick_model_dtype = load_project_modules(project_root)
    eval_file = project_root / "data" / "processed" / "extractor_test.jsonl"
    return run_eval(
        args,
        model_path,
        eval_file,
        project_root,
        parse_extractor_payload,
        evaluate_item_predictions,
        load_seed_conversations,
        detect_device,
        pick_model_dtype,
    )


if __name__ == "__main__":
    raise SystemExit(main())
