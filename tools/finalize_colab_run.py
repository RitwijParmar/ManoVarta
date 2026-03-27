#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
import json
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.config import get_runtime_config
from generate_eval_bundle import build_markdown, build_processed_summary, build_seed_summary, git_revision


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run post-training evaluation, save durable reports, and package Colab outputs."
    )
    parser.add_argument("--reports-dir", default=str(PROJECT_ROOT / "reports" / "colab_run"))
    parser.add_argument("--outputs-dir", default=str(PROJECT_ROOT / "outputs"))
    parser.add_argument("--artifacts-dir", default=str(PROJECT_ROOT / "artifacts"))
    parser.add_argument("--checkpoint-path", default=str(PROJECT_ROOT / "outputs" / "extractor-qwen25"))
    parser.add_argument("--safety-checkpoint-path", help="Optional local safety checkpoint path.")
    parser.add_argument("--semantic-model", default="ai4bharat/IndicBERTv2-MLM-only")
    parser.add_argument("--skip-checkpoint", action="store_true")
    parser.add_argument("--skip-safety-checkpoint", action="store_true")
    parser.add_argument("--skip-semantic", action="store_true")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--drive-dir", help="Optional directory to copy outputs, reports, and artifacts into.")
    parser.add_argument("--archive-name", default="manovarta_colab_bundle.zip")
    return parser.parse_args()


def run_json_command(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    payload = {
        "command": command,
        "returncode": result.returncode,
    }
    if result.returncode != 0:
        payload["status"] = "error"
        payload["stderr"] = (result.stderr or result.stdout).strip()[-4000:]
        return payload

    stdout = result.stdout.strip()
    try:
        payload["status"] = "ok"
        payload["result"] = json.loads(stdout)
    except json.JSONDecodeError:
        payload["status"] = "error"
        payload["stderr"] = f"Non-JSON output: {stdout[-4000:]}"
    return payload


def save_payload(reports_dir: Path, filename: str, payload: dict) -> None:
    path = reports_dir / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path)


def build_bundle(reports: dict, semantic_model: str) -> dict:
    config = get_runtime_config()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "runtime": {
            "provider": config.model_provider,
            "chat_model": config.chat_model,
            "extraction_model": config.extraction_model,
            "huggingface_enabled": config.huggingface_enabled,
            "semantic_safety_model": semantic_model,
        },
        "seed_summary": build_seed_summary(),
        "processed_summary": build_processed_summary(),
        "reports": reports,
    }


def copy_tree_if_present(source: Path, target: Path) -> None:
    if not source.exists():
        return
    destination = target / source.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def main() -> int:
    args = parse_args()

    reports_dir = Path(args.reports_dir)
    outputs_dir = Path(args.outputs_dir)
    artifacts_dir = Path(args.artifacts_dir)
    checkpoint_path = Path(args.checkpoint_path)
    safety_checkpoint_path = Path(args.safety_checkpoint_path) if args.safety_checkpoint_path else None

    reports_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    reports: dict[str, dict] = {}

    reports["heuristic"] = run_json_command(
        [sys.executable, str(PROJECT_ROOT / "tools" / "evaluate_seed_runtime.py"), "--mode", "heuristic"],
        PROJECT_ROOT,
    )
    save_payload(reports_dir, "heuristic_eval.json", reports["heuristic"])

    if args.skip_checkpoint:
        reports["checkpoint"] = {"status": "skipped", "reason": "Checkpoint evaluation skipped by flag."}
    elif checkpoint_path.exists():
        reports["checkpoint"] = run_json_command(
            [
                sys.executable,
                "-m",
                "training.evaluate_extractor_checkpoint",
                "--model-path",
                str(checkpoint_path),
                "--eval-file",
                str(PROJECT_ROOT / "data" / "processed" / "extractor_test.jsonl"),
            ],
            PROJECT_ROOT,
        )
    else:
        reports["checkpoint"] = {"status": "skipped", "reason": f"Checkpoint not found: {checkpoint_path}"}
    save_payload(reports_dir, "checkpoint_eval.json", reports["checkpoint"])

    if args.skip_safety_checkpoint:
        reports["safety_checkpoint"] = {"status": "skipped", "reason": "Safety checkpoint evaluation skipped by flag."}
    elif safety_checkpoint_path and safety_checkpoint_path.exists():
        reports["safety_checkpoint"] = run_json_command(
            [
                sys.executable,
                "-m",
                "training.evaluate_safety_checkpoint",
                "--model-path",
                str(safety_checkpoint_path),
                "--eval-file",
                str(PROJECT_ROOT / "data" / "processed" / "safety_test.jsonl"),
            ],
            PROJECT_ROOT,
        )
    else:
        reports["safety_checkpoint"] = {
            "status": "skipped",
            "reason": f"Safety checkpoint not found: {safety_checkpoint_path}" if safety_checkpoint_path else "No safety checkpoint path provided.",
        }
    save_payload(reports_dir, "safety_checkpoint_eval.json", reports["safety_checkpoint"])

    if args.skip_semantic:
        reports["semantic_safety"] = {"status": "skipped", "reason": "Semantic evaluation skipped by flag."}
    else:
        reports["semantic_safety"] = run_json_command(
            [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "semantic_safety_eval.py"),
                "--model",
                args.semantic_model,
            ],
            PROJECT_ROOT,
        )
    save_payload(reports_dir, "semantic_safety_eval.json", reports["semantic_safety"])

    config = get_runtime_config()
    if args.skip_llm:
        reports["llm_primary"] = {"status": "skipped", "reason": "LLM evaluation skipped by flag."}
        reports["llm_baselines"] = {"status": "skipped", "reason": "LLM evaluation skipped by flag."}
    elif config.huggingface_enabled:
        reports["llm_primary"] = run_json_command(
            [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "evaluate_seed_runtime.py"),
                "--mode",
                "llm",
                "--model",
                config.extraction_model,
            ],
            PROJECT_ROOT,
        )
        reports["llm_baselines"] = run_json_command(
            [sys.executable, str(PROJECT_ROOT / "tools" / "compare_llm_baselines.py")],
            PROJECT_ROOT,
        )
    else:
        reports["llm_primary"] = {"status": "skipped", "reason": "HF_TOKEN not configured."}
        reports["llm_baselines"] = {"status": "skipped", "reason": "HF_TOKEN not configured."}
    save_payload(reports_dir, "llm_primary_eval.json", reports["llm_primary"])
    save_payload(reports_dir, "llm_baselines.json", reports["llm_baselines"])

    bundle = build_bundle(reports, args.semantic_model)
    bundle_json = reports_dir / "eval_bundle.json"
    bundle_md = reports_dir / "eval_bundle.md"
    bundle_json.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    bundle_md.write_text(build_markdown(bundle), encoding="utf-8")
    print(bundle_json)
    print(bundle_md)

    package_command = [
        sys.executable,
        str(PROJECT_ROOT / "tools" / "package_training_artifacts.py"),
        "--source-dir",
        str(outputs_dir),
        "--include-dir",
        str(reports_dir),
        "--output-dir",
        str(artifacts_dir),
        "--archive-name",
        args.archive_name,
    ]
    package_result = subprocess.run(package_command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    if package_result.returncode != 0:
        raise SystemExit(package_result.stderr or package_result.stdout or "Artifact packaging failed.")
    archive_path = Path(package_result.stdout.strip().splitlines()[-1])
    print(archive_path)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "archive_path": str(archive_path),
        "reports_dir": str(reports_dir),
        "outputs_dir": str(outputs_dir),
    }
    manifest_path = reports_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)

    if args.drive_dir:
        drive_dir = Path(args.drive_dir)
        drive_dir.mkdir(parents=True, exist_ok=True)
        copy_tree_if_present(outputs_dir, drive_dir)
        copy_tree_if_present(reports_dir, drive_dir)
        copy_tree_if_present(artifacts_dir, drive_dir)
        if Path(PROJECT_ROOT / "data" / "processed").exists():
            copy_tree_if_present(PROJECT_ROOT / "data" / "processed", drive_dir)
        print(drive_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
