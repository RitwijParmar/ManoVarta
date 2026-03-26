#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the full local training and evaluation flow on the best available accelerator."
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--extractor-model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--safety-model", default="ai4bharat/IndicBERTv2-MLM-only")
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--extractor-output", default=str(PROJECT_ROOT / "outputs" / "local_mps" / "extractor-qwen25-1_5b"))
    parser.add_argument("--safety-output", default=str(PROJECT_ROOT / "outputs" / "local_mps" / "safety-indicbert"))
    parser.add_argument("--reports-dir", default=str(PROJECT_ROOT / "reports" / "local_run"))
    parser.add_argument("--artifacts-dir", default=str(PROJECT_ROOT / "artifacts"))
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def main() -> int:
    args = parse_args()

    run([args.python, str(PROJECT_ROOT / "tools" / "generate_seed_scaleup.py")])
    run([args.python, str(PROJECT_ROOT / "tools" / "create_data_splits.py")])
    run([args.python, str(PROJECT_ROOT / "tools" / "export_training_sets.py")])

    run(
        [
            args.python,
            "-m",
            "training.finetune_extractor",
            "--model-name",
            args.extractor_model,
            "--train-file",
            str(PROJECT_ROOT / "data" / "processed" / "extractor_train.jsonl"),
            "--eval-file",
            str(PROJECT_ROOT / "data" / "processed" / "extractor_dev.jsonl"),
            "--output-dir",
            args.extractor_output,
            "--device",
            args.device,
            "--precision",
            "auto",
            "--model-dtype",
            "auto",
            "--batch-size",
            "1",
            "--grad-accum",
            "4",
            "--epochs",
            "3",
            "--max-length",
            "1024",
            "--gradient-checkpointing",
            "--save-strategy",
            "steps",
            "--save-steps",
            "2",
            "--save-total-limit",
            "6",
            "--eval-strategy",
            "steps",
            "--eval-steps",
            "2",
            "--resume-from-checkpoint",
            "last",
        ]
    )

    run(
        [
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
            args.safety_output,
            "--device",
            args.device,
            "--precision",
            "auto",
            "--batch-size",
            "4",
            "--epochs",
            "4",
            "--save-strategy",
            "steps",
            "--save-steps",
            "5",
            "--save-total-limit",
            "6",
            "--eval-strategy",
            "steps",
            "--eval-steps",
            "5",
            "--resume-from-checkpoint",
            "last",
        ]
    )

    run(
        [
            args.python,
            str(PROJECT_ROOT / "tools" / "finalize_colab_run.py"),
            "--checkpoint-path",
            args.extractor_output,
            "--semantic-model",
            args.safety_model,
            "--reports-dir",
            args.reports_dir,
            "--artifacts-dir",
            args.artifacts_dir,
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
