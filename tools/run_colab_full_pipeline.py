#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports" / "colab_run"
DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_EXTRACTOR_OUTPUT = PROJECT_ROOT / "outputs" / "colab" / "extractor-qwen25-7b-compact"
DEFAULT_SAFETY_OUTPUT = PROJECT_ROOT / "outputs" / "colab" / "safety-indicbert"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the end-to-end Colab training and evaluation pipeline with resumable checkpoints and durable reports."
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="cuda")
    parser.add_argument("--daic-root", default=None, help="Optional DAIC-WOZ root directory for English auxiliary supervision.")
    parser.add_argument("--drive-dir", default=None, help="Optional Drive directory to copy outputs, reports, and artifacts into.")
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--artifacts-dir", default=str(DEFAULT_ARTIFACTS_DIR))
    parser.add_argument("--extractor-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--extractor-output", default=str(DEFAULT_EXTRACTOR_OUTPUT))
    parser.add_argument("--extractor-epochs", type=int, default=2)
    parser.add_argument("--extractor-batch-size", type=int, default=1)
    parser.add_argument("--extractor-grad-accum", type=int, default=8)
    parser.add_argument("--extractor-max-length", type=int, default=1536)
    parser.add_argument("--extractor-save-steps", type=int, default=10)
    parser.add_argument("--extractor-max-new-tokens", type=int, default=900)
    parser.add_argument("--disable-extractor-4bit", action="store_true")
    parser.add_argument("--safety-model", default="ai4bharat/IndicBERTv2-MLM-only")
    parser.add_argument("--safety-output", default=str(DEFAULT_SAFETY_OUTPUT))
    parser.add_argument("--safety-epochs", type=int, default=4)
    parser.add_argument("--safety-batch-size", type=int, default=8)
    parser.add_argument("--safety-save-steps", type=int, default=10)
    parser.add_argument("--smoke-limit", type=int, default=8)
    parser.add_argument("--skip-semantic", action="store_true")
    parser.add_argument("--run-llm-baselines", action="store_true")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def checkpoint_step(path: Path) -> int:
    if path.name.startswith("checkpoint-"):
        try:
            return int(path.name.split("-")[-1])
        except ValueError:
            return -1
    return 10**9


def configure_storage_paths(args: argparse.Namespace) -> None:
    if not args.drive_dir:
        return

    drive_root = Path(args.drive_dir)
    if args.reports_dir == str(DEFAULT_REPORTS_DIR):
        args.reports_dir = str(drive_root / "reports" / "colab_run")
    if args.artifacts_dir == str(DEFAULT_ARTIFACTS_DIR):
        args.artifacts_dir = str(drive_root / "artifacts")
    if args.extractor_output == str(DEFAULT_EXTRACTOR_OUTPUT):
        args.extractor_output = str(drive_root / "outputs" / "colab" / DEFAULT_EXTRACTOR_OUTPUT.name)
    if args.safety_output == str(DEFAULT_SAFETY_OUTPUT):
        args.safety_output = str(drive_root / "outputs" / "colab" / DEFAULT_SAFETY_OUTPUT.name)


def iter_candidate_checkpoints(root: Path) -> list[Path]:
    candidates: list[Path] = []
    if (root / "config.json").exists() or (root / "adapter_config.json").exists():
        candidates.append(root)
    candidates.extend(sorted(root.glob("checkpoint-*"), key=checkpoint_step))
    return candidates


def pick_best_safety_report(reports: list[dict]) -> dict:
    if not reports:
        raise ValueError("No safety reports available to rank.")

    def sort_key(report: dict) -> tuple[float, float, int]:
        result = report["result"]
        return (
            float(result.get("macro_f1", 0.0)),
            float(result.get("accuracy", 0.0)),
            int(report.get("step", -1)),
        )

    return max(reports, key=sort_key)


def export_processed_data(args: argparse.Namespace) -> None:
    cmd = [
        args.python,
        str(PROJECT_ROOT / "tools" / "export_training_sets.py"),
        "--extractor-style",
        "compact",
    ]
    if args.daic_root:
        cmd.extend(["--daic-root", args.daic_root])
    run(cmd)


def extractor_train_file(args: argparse.Namespace) -> Path:
    if args.daic_root:
        candidate = PROJECT_ROOT / "data" / "processed" / "extractor_train_best_augmented_daic.jsonl"
        if candidate.exists():
            return candidate
    return PROJECT_ROOT / "data" / "processed" / "extractor_train_best.jsonl"


def run_extractor_training(args: argparse.Namespace) -> Path:
    output_dir = Path(args.extractor_output)
    cmd = [
        args.python,
        "-m",
        "training.finetune_extractor",
        "--model-name",
        args.extractor_model,
        "--train-file",
        str(extractor_train_file(args)),
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


def run_safety_training(args: argparse.Namespace) -> Path:
    output_dir = Path(args.safety_output)
    cmd = [
        args.python,
        "-m",
        "training.train_safety_classifier",
        "--model-name",
        args.safety_model,
        "--train-file",
        str(PROJECT_ROOT / "data" / "processed" / "safety_train.jsonl"),
        "--eval-file",
        str(PROJECT_ROOT / "data" / "processed" / "safety_dev.jsonl"),
        "--output-dir",
        str(output_dir),
        "--epochs",
        str(args.safety_epochs),
        "--batch-size",
        str(args.safety_batch_size),
        "--device",
        args.device,
        "--precision",
        "auto",
        "--save-strategy",
        "steps",
        "--save-steps",
        str(args.safety_save_steps),
        "--eval-strategy",
        "steps",
        "--eval-steps",
        str(args.safety_save_steps),
        "--resume-from-checkpoint",
        "last",
    ]
    run(cmd)
    return output_dir


def select_best_safety_checkpoint(args: argparse.Namespace, output_dir: Path, reports_dir: Path) -> tuple[Path, Path]:
    eval_dir = reports_dir / "safety_checkpoint_candidates"
    eval_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict] = []

    for checkpoint in iter_candidate_checkpoints(output_dir):
        report_path = eval_dir / f"{checkpoint.name}.json"
        cmd = [
            args.python,
            str(PROJECT_ROOT / "training" / "evaluate_safety_checkpoint.py"),
            "--model-path",
            str(checkpoint),
            "--eval-file",
            str(PROJECT_ROOT / "data" / "processed" / "safety_test.jsonl"),
            "--device",
            args.device,
        ]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise SystemExit(result.stderr or result.stdout or f"Safety evaluation failed for {checkpoint}")
        report = json.loads(result.stdout)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        reports.append(
            {
                "checkpoint_name": checkpoint.name,
                "checkpoint_path": str(checkpoint.resolve()),
                "step": checkpoint_step(checkpoint),
                "result": report,
                "report_path": str(report_path.resolve()),
            }
        )

    best = pick_best_safety_report(reports)
    selected_root = reports_dir / "selected_safety_checkpoint"
    if selected_root.exists():
        shutil.rmtree(selected_root)
    shutil.copytree(best["checkpoint_path"], selected_root)

    selection_path = reports_dir / "best_safety_checkpoint.json"
    selection_payload = {
        "selected_checkpoint": best["checkpoint_name"],
        "selected_checkpoint_path": str(selected_root.resolve()),
        "selected_report_path": best["report_path"],
        "macro_f1": best["result"]["macro_f1"],
        "accuracy": best["result"]["accuracy"],
        "candidates": reports,
    }
    selection_path.write_text(json.dumps(selection_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return selected_root, Path(best["report_path"])


def run_extractor_eval(args: argparse.Namespace, extractor_dir: Path, reports_dir: Path) -> Path:
    eval_dir = reports_dir / "extractor_eval"
    smoke_cmd = [
        args.python,
        str(PROJECT_ROOT / "tools" / "resumable_extractor_eval.py"),
        "--model-path",
        str(extractor_dir),
        "--eval-file",
        str(PROJECT_ROOT / "data" / "processed" / "extractor_test.jsonl"),
        "--output-dir",
        str(eval_dir),
        "--device",
        args.device,
        "--max-new-tokens",
        str(args.extractor_max_new_tokens),
        "--limit",
        str(args.smoke_limit),
        "--stop-on-parse-failure",
        "--max-parse-failures",
        "1",
    ]
    run(smoke_cmd)

    summary_path = eval_dir / "summary.json"
    smoke_summary = load_json(summary_path)
    if smoke_summary.get("parse_failures", 0) > 0 or smoke_summary.get("status") == "stopped_on_parse_failure":
        raise SystemExit(
            f"Extractor smoke eval found parse failures. Inspect {summary_path} and {eval_dir / 'raw_generations'} before full eval."
        )

    full_cmd = [
        args.python,
        str(PROJECT_ROOT / "tools" / "resumable_extractor_eval.py"),
        "--model-path",
        str(extractor_dir),
        "--eval-file",
        str(PROJECT_ROOT / "data" / "processed" / "extractor_test.jsonl"),
        "--output-dir",
        str(eval_dir),
        "--device",
        args.device,
        "--max-new-tokens",
        str(args.extractor_max_new_tokens),
    ]
    run(full_cmd)
    return summary_path


def finalize(args: argparse.Namespace, extractor_dir: Path, extractor_eval_json: Path, safety_dir: Path, safety_eval_json: Path, reports_dir: Path) -> None:
    cmd = [
        args.python,
        str(PROJECT_ROOT / "tools" / "finalize_colab_run.py"),
        "--checkpoint-path",
        str(extractor_dir),
        "--checkpoint-eval-json",
        str(extractor_eval_json),
        "--safety-checkpoint-path",
        str(safety_dir),
        "--safety-eval-json",
        str(safety_eval_json),
        "--semantic-model",
        args.safety_model,
        "--reports-dir",
        str(reports_dir),
        "--artifacts-dir",
        str(args.artifacts_dir),
    ]
    if args.skip_semantic:
        cmd.append("--skip-semantic")
    if not args.run_llm_baselines:
        cmd.append("--skip-llm")
    if args.drive_dir:
        cmd.extend(["--drive-dir", args.drive_dir])
    run(cmd)


def main() -> int:
    args = parse_args()
    configure_storage_paths(args)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    export_processed_data(args)
    extractor_dir = run_extractor_training(args)
    safety_dir = run_safety_training(args)
    selected_safety_dir, selected_safety_eval = select_best_safety_checkpoint(args, safety_dir, reports_dir)
    extractor_eval_json = run_extractor_eval(args, extractor_dir, reports_dir)
    finalize(args, extractor_dir, extractor_eval_json, selected_safety_dir, selected_safety_eval, reports_dir)
    print(reports_dir / "eval_bundle.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
