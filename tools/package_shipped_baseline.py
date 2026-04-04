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
    "data/seed",
    "reports/best_current_system_report.json",
    "reports/best_current_system_report.md",
    "reports/hybrid_runtime_validation_colab_20260404.json",
    "reports/local_safety_checkpoint_default_runtime_eval.json",
    "reports/ship_note_2026-04-04.md",
    "tools/demo_cli.py",
    "tools/hf_smoketest.py",
    "tools/package_shipped_baseline.py",
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
        default="manovarta_shipped_baseline_20260404.zip",
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
        "git_tag": "shipped-baseline-2026-04-04",
        "archive_name": args.archive_name,
        "default_runtime": {
            "chat_model": "Qwen/Qwen2.5-7B-Instruct",
            "extraction_model": "CohereLabs/aya-expanse-32b",
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
