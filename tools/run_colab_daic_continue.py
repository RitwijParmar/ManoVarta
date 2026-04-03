#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports" / "colab_daic_continue"
DEFAULT_EXTRACTOR_OUTPUT = PROJECT_ROOT / "outputs" / "colab" / "extractor-aya-8b-compact-daic-continue"


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
    parser.add_argument("--extractor-model", default="CohereLabs/aya-expanse-8b")
    parser.add_argument("--extractor-epochs", type=int, default=1)
    parser.add_argument("--extractor-batch-size", type=int, default=1)
    parser.add_argument("--extractor-grad-accum", type=int, default=8)
    parser.add_argument("--extractor-max-length", type=int, default=1536)
    parser.add_argument("--extractor-save-steps", type=int, default=10)
    parser.add_argument("--extractor-max-new-tokens", type=int, default=900)
    parser.add_argument("--best-en-weight", type=int, default=1)
    parser.add_argument("--best-hi-weight", type=int, default=2)
    parser.add_argument("--best-hinglish-weight", type=int, default=2)
    parser.add_argument("--hinglish-hardcase-repeats", type=int, default=1)
    parser.add_argument("--daic-ratio", type=float, default=0.5)
    parser.add_argument("--select-best-checkpoint", action="store_true")
    parser.add_argument("--smoke-limit", type=int, default=8)
    parser.add_argument("--disable-extractor-4bit", action="store_true")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def resolve_git_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        return "archive-no-git"


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
        "--best-en-weight",
        str(args.best_en_weight),
        "--best-hi-weight",
        str(args.best_hi_weight),
        "--best-hinglish-weight",
        str(args.best_hinglish_weight),
        "--hinglish-hardcase-repeats",
        str(args.hinglish_hardcase_repeats),
        "--daic-ratio",
        str(args.daic_ratio),
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


def checkpoint_step(path: Path) -> int:
    if path.name.startswith("checkpoint-"):
        try:
            return int(path.name.split("-")[-1])
        except ValueError:
            return -1
    return 10**9


def iter_candidate_checkpoints(root: Path) -> list[Path]:
    candidates: list[Path] = []
    if (root / "config.json").exists() or (root / "adapter_config.json").exists():
        candidates.append(root)
    candidates.extend(sorted(root.glob("checkpoint-*"), key=checkpoint_step))
    return candidates


def pick_best_extractor_report(reports: list[dict]) -> dict:
    if not reports:
        raise ValueError("No extractor reports available to rank.")

    def average(metric_name: str, result: dict) -> float:
        languages = result.get("languages", {})
        values = [float(languages.get(language, {}).get(metric_name, 0.0)) for language in ("en", "hi", "hinglish")]
        return sum(values) / len(values)

    def minimum(metric_name: str, result: dict) -> float:
        languages = result.get("languages", {})
        values = [float(languages.get(language, {}).get(metric_name, 0.0)) for language in ("en", "hi", "hinglish")]
        return min(values)

    def sort_key(report: dict) -> tuple[float, float, float, float, float, float, int]:
        result = report["result"]
        overall = result.get("overall", {})
        return (
            average("macro_f1", result),
            minimum("macro_f1", result),
            average("exact_match_rate", result),
            minimum("coverage_completeness", result),
            float(overall.get("macro_f1", 0.0)),
            -float(overall.get("mae", 999.0)),
            int(report.get("step", -1)),
        )

    return max(reports, key=sort_key)


def select_best_extractor_checkpoint(args: argparse.Namespace, output_dir: Path, reports_dir: Path) -> tuple[Path, Path]:
    eval_dir = reports_dir / "extractor_checkpoint_candidates"
    eval_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict] = []

    for checkpoint in iter_candidate_checkpoints(output_dir):
        report_path = eval_dir / f"{checkpoint.name}.json"
        cmd = [
            args.python,
            str(PROJECT_ROOT / "training" / "evaluate_extractor_checkpoint.py"),
            "--model-path",
            str(checkpoint),
            "--eval-file",
            str(PROJECT_ROOT / "data" / "processed" / "extractor_dev.jsonl"),
            "--max-new-tokens",
            str(args.extractor_max_new_tokens),
            "--device",
            args.device,
        ]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise SystemExit(result.stderr or result.stdout or f"Extractor evaluation failed for {checkpoint}")
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

    best = pick_best_extractor_report(reports)
    selected_root = reports_dir / "selected_extractor_checkpoint"
    if selected_root.exists():
        shutil.rmtree(selected_root)
    shutil.copytree(best["checkpoint_path"], selected_root)

    selection_path = reports_dir / "best_extractor_checkpoint.json"
    selection_payload = {
        "selected_checkpoint": best["checkpoint_name"],
        "selected_checkpoint_path": str(selected_root.resolve()),
        "selected_report_path": best["report_path"],
        "score_basis": "avg_language_macro_f1 -> min_language_macro_f1 -> avg_exact_match -> min_coverage -> overall_macro_f1 -> lower_mae",
        "candidates": reports,
    }
    selection_path.write_text(json.dumps(selection_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return selected_root, selection_path


def write_summary(args: argparse.Namespace, train_path: Path, extractor_dir: Path, smoke_summary: Path, full_summary: Path, reports_dir: Path) -> Path:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": resolve_git_revision(),
        "device": args.device,
        "daic_root": args.daic_root,
        "init_adapter": args.init_adapter,
        "data_recipe": {
            "best_en_weight": args.best_en_weight,
            "best_hi_weight": args.best_hi_weight,
            "best_hinglish_weight": args.best_hinglish_weight,
            "hinglish_hardcase_repeats": args.hinglish_hardcase_repeats,
            "daic_ratio": args.daic_ratio,
            "select_best_checkpoint": args.select_best_checkpoint,
        },
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
    eval_model_dir = extractor_dir
    if args.select_best_checkpoint:
        eval_model_dir, _ = select_best_extractor_checkpoint(args, extractor_dir, reports_dir)

    smoke_summary = run_resumable_eval(args, eval_model_dir, reports_dir / "extractor_eval_smoke", limit=args.smoke_limit)
    smoke_payload = json.loads(smoke_summary.read_text(encoding="utf-8"))
    if smoke_payload.get("status") == "stopped_on_parse_failure":
        raise SystemExit(f"Smoke eval stopped on parse failure: {smoke_summary}")

    full_summary = run_resumable_eval(args, eval_model_dir, reports_dir / "extractor_eval_full")
    write_summary(args, train_path, eval_model_dir, smoke_summary, full_summary, reports_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
