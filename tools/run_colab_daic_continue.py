#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports" / "colab_daic_continue"
DEFAULT_EXTRACTOR_OUTPUT = PROJECT_ROOT / "outputs" / "colab" / "extractor-qwen25-7b-compact-daic-continue"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Continue extractor training from an existing LoRA checkpoint using DAIC-WOZ auxiliary supervision."
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="cuda")
    parser.add_argument("--daic-root", required=True, help="Mounted DAIC-WOZ root directory.")
    parser.add_argument("--init-adapter", required=True, help="Existing extractor adapter directory to continue from.")
    parser.add_argument("--drive-dir", default=None, help="Optional Drive directory for outputs and reports.")
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--extractor-output", default=str(DEFAULT_EXTRACTOR_OUTPUT))
    parser.add_argument("--extractor-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--extractor-epochs", type=int, default=1)
    parser.add_argument("--extractor-batch-size", type=int, default=1)
    parser.add_argument("--extractor-grad-accum", type=int, default=8)
    parser.add_argument("--extractor-max-length", type=int, default=1536)
    parser.add_argument("--extractor-save-steps", type=int, default=10)
    parser.add_argument("--extractor-max-new-tokens", type=int, default=900)
    parser.add_argument("--smoke-limit", type=int, default=8)
    parser.add_argument("--disable-extractor-4bit", action="store_true")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def configure_storage_paths(args: argparse.Namespace) -> None:
    if not args.drive_dir:
        return

    drive_root = Path(args.drive_dir)
    if args.reports_dir == str(DEFAULT_REPORTS_DIR):
        args.reports_dir = str(drive_root / "reports" / "colab_daic_continue")
    if args.extractor_output == str(DEFAULT_EXTRACTOR_OUTPUT):
        args.extractor_output = str(drive_root / "outputs" / "colab" / DEFAULT_EXTRACTOR_OUTPUT.name)


def export_processed_data(args: argparse.Namespace) -> Path:
    cmd = [
        args.python,
        str(PROJECT_ROOT / "tools" / "export_training_sets.py"),
        "--extractor-style",
        "compact",
        "--daic-root",
        args.daic_root,
    ]
    run(cmd)
    train_path = PROJECT_ROOT / "data" / "processed" / "extractor_train_best_augmented_daic.jsonl"
    if not train_path.exists():
        raise SystemExit(f"Expected DAIC-augmented train file was not written: {train_path}")
    return train_path


def run_extractor_training(args: argparse.Namespace, train_path: Path) -> Path:
    output_dir = Path(args.extractor_output)
    cmd = [
        args.python,
        "-m",
        "training.finetune_extractor",
        "--model-name",
        args.extractor_model,
        "--init-adapter",
        args.init_adapter,
        "--train-file",
        str(train_path),
        "--eval-file",
        str(PROJECT_ROOT / "data" / "processed" / "extractor_dev.jsonl"),
        "--output-dir",
        str(output_dir),
        "--epochs",
        str(args.extractor_epochs),
        "--batch-size",
        str(args.extractor_batch_size),
        "--grad-accum",
        str(args.extractor_grad_accum),
        "--max-length",
        str(args.extractor_max_length),
        "--device",
        args.device,
        "--precision",
        "auto",
        "--gradient-checkpointing",
        "--save-strategy",
        "steps",
        "--save-steps",
        str(args.extractor_save_steps),
        "--eval-strategy",
        "no",
        "--resume-from-checkpoint",
        "last",
    ]
    if not args.disable_extractor_4bit:
        cmd.append("--use-4bit")
    run(cmd)
    return output_dir


def run_resumable_eval(args: argparse.Namespace, model_path: Path, output_dir: Path, limit: int | None = None) -> Path:
    cmd = [
        args.python,
        str(PROJECT_ROOT / "tools" / "resumable_extractor_eval.py"),
        "--model-path",
        str(model_path),
        "--eval-file",
        str(PROJECT_ROOT / "data" / "processed" / "extractor_test.jsonl"),
        "--output-dir",
        str(output_dir),
        "--max-new-tokens",
        str(args.extractor_max_new_tokens),
        "--device",
        args.device,
    ]
    if limit is not None:
        cmd.extend(["--limit", str(limit), "--stop-on-parse-failure", "--max-parse-failures", "1"])
    run(cmd)
    return output_dir / "summary.json"


def write_summary(args: argparse.Namespace, train_path: Path, extractor_dir: Path, smoke_summary: Path, full_summary: Path, reports_dir: Path) -> Path:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip(),
        "device": args.device,
        "daic_root": args.daic_root,
        "init_adapter": args.init_adapter,
        "train_file": str(train_path.resolve()),
        "extractor_output": str(extractor_dir.resolve()),
        "smoke_summary": json.loads(smoke_summary.read_text(encoding="utf-8")),
        "full_summary": json.loads(full_summary.read_text(encoding="utf-8")),
    }
    summary_path = reports_dir / "daic_continue_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(summary_path)
    return summary_path


def main() -> int:
    args = parse_args()
    configure_storage_paths(args)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    train_path = export_processed_data(args)
    extractor_dir = run_extractor_training(args, train_path)

    smoke_summary = run_resumable_eval(args, extractor_dir, reports_dir / "extractor_eval_smoke", limit=args.smoke_limit)
    smoke_payload = json.loads(smoke_summary.read_text(encoding="utf-8"))
    if smoke_payload.get("status") == "stopped_on_parse_failure":
        raise SystemExit(f"Smoke eval stopped on parse failure: {smoke_summary}")

    full_summary = run_resumable_eval(args, extractor_dir, reports_dir / "extractor_eval_full")
    write_summary(args, train_path, extractor_dir, smoke_summary, full_summary, reports_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
