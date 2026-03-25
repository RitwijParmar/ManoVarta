#!/usr/bin/env python3
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.config import get_runtime_config
from manovarta_core.seed_data import load_seed_conversations, load_seed_profiles


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a saved evaluation bundle for the current repo state.")
    parser.add_argument("--output-json", default=str(PROJECT_ROOT / "reports" / "eval_bundle.json"))
    parser.add_argument("--output-md", default=str(PROJECT_ROOT / "reports" / "eval_bundle.md"))
    parser.add_argument("--checkpoint", help="Optional local extractor checkpoint path.")
    parser.add_argument("--semantic-model", default="ai4bharat/IndicBERTv2-MLM-only")
    parser.add_argument("--skip-semantic", action="store_true")
    return parser.parse_args()


def run_json_command(command: list[str]) -> dict:
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = {
        "command": command,
        "returncode": result.returncode,
    }
    if result.returncode != 0:
        payload["status"] = "error"
        payload["stderr"] = (result.stderr or result.stdout).strip()[-4000:]
        return payload

    try:
        payload["status"] = "ok"
        payload["result"] = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload["status"] = "error"
        payload["stderr"] = f"Non-JSON output: {result.stdout.strip()[-4000:]}"
    return payload


def build_seed_summary() -> dict:
    conversations = load_seed_conversations()
    profiles = load_seed_profiles()
    return {
        "profiles": len(profiles),
        "conversations": len(conversations),
        "languages": dict(Counter(conv["language"] for conv in conversations)),
        "review_status": dict(Counter(conv["review_status"] for conv in conversations)),
        "safety_levels": dict(Counter(conv.get("safety_flag", {}).get("level", "none") for conv in conversations)),
    }


def build_processed_summary() -> dict:
    processed_dir = PROJECT_ROOT / "data" / "processed"
    summary = {}
    for path in sorted(processed_dir.glob("*")):
        if path.is_file():
            summary[path.name] = len(path.read_text(encoding="utf-8").splitlines())
    return summary


def maybe_checkpoint_report(checkpoint_path: Optional[str]) -> dict:
    if not checkpoint_path:
        return {"status": "skipped", "reason": "No checkpoint path provided."}

    checkpoint = Path(checkpoint_path)
    if not checkpoint.exists():
        return {"status": "skipped", "reason": f"Checkpoint not found: {checkpoint}"}

    return run_json_command(
        [
            sys.executable,
            "-m",
            "training.evaluate_extractor_checkpoint",
            "--model-path",
            str(checkpoint),
            "--eval-file",
            str(PROJECT_ROOT / "data" / "processed" / "extractor_test.jsonl"),
        ]
    )


def build_bundle(args) -> dict:
    config = get_runtime_config()
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "runtime": {
            "provider": config.model_provider,
            "chat_model": config.chat_model,
            "extraction_model": config.extraction_model,
            "huggingface_enabled": config.huggingface_enabled,
            "semantic_safety_model": args.semantic_model,
        },
        "seed_summary": build_seed_summary(),
        "processed_summary": build_processed_summary(),
        "reports": {},
    }

    bundle["reports"]["heuristic"] = run_json_command(
        [sys.executable, str(PROJECT_ROOT / "tools" / "evaluate_seed_runtime.py"), "--mode", "heuristic"]
    )
    bundle["reports"]["checkpoint"] = maybe_checkpoint_report(args.checkpoint)

    if args.skip_semantic:
        bundle["reports"]["semantic_safety"] = {"status": "skipped", "reason": "Semantic evaluation skipped by flag."}
    else:
        bundle["reports"]["semantic_safety"] = run_json_command(
            [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "semantic_safety_eval.py"),
                "--model",
                args.semantic_model,
            ]
        )

    if config.huggingface_enabled:
        bundle["reports"]["llm_primary"] = run_json_command(
            [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "evaluate_seed_runtime.py"),
                "--mode",
                "llm",
                "--model",
                config.extraction_model,
            ]
        )
        bundle["reports"]["llm_baselines"] = run_json_command(
            [sys.executable, str(PROJECT_ROOT / "tools" / "compare_llm_baselines.py")]
        )
    else:
        bundle["reports"]["llm_primary"] = {"status": "skipped", "reason": "HF_TOKEN not configured."}
        bundle["reports"]["llm_baselines"] = {"status": "skipped", "reason": "HF_TOKEN not configured."}

    return bundle


def build_markdown(bundle: dict) -> str:
    lines = [
        "# Evaluation Bundle",
        "",
        f"- Generated: `{bundle['generated_at']}`",
        f"- Git revision: `{bundle['git_revision']}`",
        f"- Chat model: `{bundle['runtime']['chat_model']}`",
        f"- Extraction model: `{bundle['runtime']['extraction_model']}`",
        "",
        "## Seed Summary",
        "",
        f"- Profiles: `{bundle['seed_summary']['profiles']}`",
        f"- Conversations: `{bundle['seed_summary']['conversations']}`",
        f"- Languages: `{bundle['seed_summary']['languages']}`",
        f"- Safety levels: `{bundle['seed_summary']['safety_levels']}`",
        "",
        "## Processed Files",
        "",
    ]
    for name, count in bundle["processed_summary"].items():
        lines.append(f"- `{name}`: `{count}` lines")

    lines.extend(["", "## Reports", ""])
    for name, report in bundle["reports"].items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- Status: `{report.get('status', 'unknown')}`")
        if report.get("status") == "ok":
            result = report.get("result", {})
            if isinstance(result, dict):
                overall = result.get("overall")
                if overall:
                    lines.append(f"- Overall: `{overall}`")
                model = result.get("model") or result.get("model_path")
                if model:
                    lines.append(f"- Model: `{model}`")
        elif "reason" in report:
            lines.append(f"- Reason: {report['reason']}")
        elif "stderr" in report:
            lines.append(f"- Error: `{report['stderr'][:300]}`")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def main() -> int:
    args = parse_args()
    bundle = build_bundle(args)

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_md.write_text(build_markdown(bundle), encoding="utf-8")

    print(output_json)
    print(output_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
