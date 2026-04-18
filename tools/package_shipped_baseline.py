#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INCLUDES = [
    "README.md",
    ".env.example",
    "Makefile",
    "pyproject.toml",
    "manovarta_core",
    "screening",
    "data/seed",
    "data/gold",
    "reports/best_current_system_report.json",
    "reports/best_current_system_report.md",
    "reports/aya_daic_continue_full_eval_20260413.json",
    "reports/final_assignment_completion_report.json",
    "reports/final_assignment_completion_report.md",
    "reports/gold_adjudication_status.json",
    "reports/gold_adjudication_status.md",
    "reports/live_runtime_eval_20260404.json",
    "reports/gold_dataset_status.json",
    "reports/gold_dataset_status.md",
    "reports/gold_progress_dashboard.json",
    "reports/gold_progress_dashboard.md",
    "reports/ai_assisted_completion_report_20260410.md",
    "reports/strict_compliance_repo_audit_20260409.md",
    "reports/strict_compliance_repo_audit_20260410.md",
    "reports/reviewer_workflow_pack.json",
    "reports/reviewer_workflow_pack.md",
    "reports/reviewer_queue_annotator_a.csv",
    "reports/reviewer_queue_annotator_b.csv",
    "reports/reviewer_queue_adjudicator.csv",
    "tools/build_gold_annotation_packets.py",
    "tools/demo_cli.py",
    "tools/generate_gold_adjudication_report.py",
    "tools/generate_gold_progress_dashboard.py",
    "tools/generate_reviewer_workflow_pack.py",
    "tools/hf_smoketest.py",
    "tools/import_edaic_english_public.py",
    "tools/import_indicvoices_hindi_valid.py",
    "tools/init_gold_dataset.py",
    "tools/package_shipped_baseline.py",
    "tools/sync_gold_registry_status.py",
    "tools/validate_gold_dataset.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package the shipped ManoVarta baseline into a lean demo bundle.")
    parser.add_argument(
        "--checkpoint-dir",
        default=str(PROJECT_ROOT / "outputs" / "local_safety_boost" / "safety-indicbert-best-infer-fp16"),
        help="Inference-only local safety checkpoint to include in the bundle.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "artifacts"),
    )
    parser.add_argument(
        "--archive-name",
        default="manovarta_shipped_baseline_20260413.zip",
    )
    return parser.parse_args()


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def add_path(archive: zipfile.ZipFile, path: Path) -> None:
    if path.name == ".DS_Store" or "__pycache__" in path.parts:
        return
    if path.is_file():
        archive.write(path, arcname=path.relative_to(PROJECT_ROOT))
        return
    for child in sorted(path.rglob("*")):
        if child.is_file() and child.name != ".DS_Store" and "__pycache__" not in child.parts:
            archive.write(child, arcname=child.relative_to(PROJECT_ROOT))


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    checkpoint_dir = Path(args.checkpoint_dir)
    archive_path = output_dir / args.archive_name

    if not checkpoint_dir.exists():
        raise SystemExit(f"Missing checkpoint directory: {checkpoint_dir}")

    include_paths = [PROJECT_ROOT / rel for rel in DEFAULT_INCLUDES]
    missing = [path for path in include_paths if not path.exists()]
    if missing:
        missing_str = ", ".join(str(path.relative_to(PROJECT_ROOT)) for path in missing)
        raise SystemExit(f"Missing required paths for shipped bundle: {missing_str}")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "git_tag": "shipped-baseline-2026-04-13",
        "archive_name": args.archive_name,
        "default_runtime": {
            "chat_model": "/models/qwen2.5-0.5b-instruct",
            "extraction_model": "/models/qwen2.5-0.5b-instruct",
            "safety_checkpoint": str(checkpoint_dir.relative_to(PROJECT_ROOT)),
            "hybrid_safety_enabled": True,
            "rule_safety_monitor_enabled": True,
        },
        "launch": {
            "api": "source .venv/bin/activate && uvicorn manovarta_core.api:app --reload",
            "demo_cli": "source .venv/bin/activate && python tools/demo_cli.py --language en",
            "hf_smoke": "source .venv/bin/activate && python tools/hf_smoketest.py",
        },
        "included_paths": DEFAULT_INCLUDES + [str(checkpoint_dir.relative_to(PROJECT_ROOT))],
    }

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for path in include_paths:
            add_path(archive, path)
        add_path(archive, checkpoint_dir)

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
