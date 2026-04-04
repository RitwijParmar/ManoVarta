#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.config import get_runtime_config
from generate_eval_bundle import git_revision


DEFAULT_HYBRID_SUMMARY_SOURCE = (
    str(PROJECT_ROOT / "reports" / "live_runtime_eval_20260404.json")
    if (PROJECT_ROOT / "reports" / "live_runtime_eval_20260404.json").exists()
    else "https://files.catbox.moe/mt0f2k.json"
)
DEFAULT_LIVE_RUNTIME_URL = "https://manovarta-runtime-122722888597.us-east4.run.app"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the current best-system runtime report.")
    parser.add_argument(
        "--hybrid-summary-source",
        default=DEFAULT_HYBRID_SUMMARY_SOURCE,
        help="Local path or URL for the completed hybrid Colab validation summary.",
    )
    parser.add_argument(
        "--hybrid-summary-mirror",
        default=(
            str(PROJECT_ROOT / "reports" / "live_runtime_eval_20260404.json")
            if (PROJECT_ROOT / "reports" / "live_runtime_eval_20260404.json").exists()
            else str(PROJECT_ROOT / "reports" / "hybrid_runtime_validation_colab_20260404.json")
        ),
        help="Where to save the mirrored hybrid summary JSON.",
    )
    parser.add_argument(
        "--aya-baseline-json",
        default=str(PROJECT_ROOT / "reports" / "aya_colab_eval_a100_20260328.json"),
    )
    parser.add_argument(
        "--local-safety-report-json",
        default=str(PROJECT_ROOT / "reports" / "local_safety_checkpoint_default_runtime_eval.json"),
    )
    parser.add_argument(
        "--output-json",
        default=str(PROJECT_ROOT / "reports" / "best_current_system_report.json"),
    )
    parser.add_argument(
        "--output-md",
        default=str(PROJECT_ROOT / "reports" / "best_current_system_report.md"),
    )
    parser.add_argument("--device", default="auto", help="Device to use for local safety checkpoint evaluation.")
    return parser.parse_args()


def load_json_source(source: str) -> dict:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        request = Request(source, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            result = subprocess.run(
                ["curl", "-fsSL", source],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise
            return json.loads(result.stdout)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_live_runtime(url: str = DEFAULT_LIVE_RUNTIME_URL) -> dict:
    request = Request(url.rstrip("/") + "/runtime/config", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_path_value(value: str | None) -> str | None:
    if not value:
        return value
    path = Path(value).expanduser()
    try:
        relative = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except Exception:
        return str(path)
    return relative.as_posix()


def evaluate_local_safety_checkpoint(checkpoint_path: str | None, *, device: str) -> dict:
    if not checkpoint_path:
        return {"status": "skipped", "reason": "No local safety checkpoint configured."}

    checkpoint = Path(checkpoint_path)
    if not checkpoint.exists():
        return {"status": "skipped", "reason": f"Configured safety checkpoint not found: {checkpoint}"}

    command_preview = [
        "python",
        "-m",
        "training.evaluate_safety_checkpoint",
        "--model-path",
        normalize_path_value(str(checkpoint)),
        "--eval-file",
        "data/processed/safety_test.jsonl",
        "--device",
        device,
    ]
    command = [
        sys.executable,
        "-m",
        "training.evaluate_safety_checkpoint",
        "--model-path",
        str(checkpoint),
        "--eval-file",
        str(PROJECT_ROOT / "data" / "processed" / "safety_test.jsonl"),
        "--device",
        device,
    ]
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    payload = {"status": "ok" if result.returncode == 0 else "error", "command": command_preview}
    if result.returncode != 0:
        payload["stderr"] = (result.stderr or result.stdout).strip()[-4000:]
        return payload
    payload["result"] = json.loads(result.stdout)
    if "model_path" in payload["result"]:
        payload["result"]["model_path"] = normalize_path_value(payload["result"]["model_path"])
    return payload


def overall_metrics(payload: dict) -> dict:
    if "overall" in payload:
        return payload["overall"]
    if "full_summary" in payload:
        return payload["full_summary"]["overall"]
    return {}


def compare_metrics(aya_payload: dict, hybrid_payload: dict) -> dict:
    aya = overall_metrics(aya_payload)
    hybrid = overall_metrics(hybrid_payload)
    metrics = [
        "coverage_completeness",
        "mae",
        "exact_match_rate",
        "macro_f1",
        "safety_precision",
        "safety_recall",
    ]
    deltas = {}
    for metric in metrics:
        if metric in aya and metric in hybrid:
            deltas[metric] = round(hybrid[metric] - aya[metric], 3)
    return deltas


def build_report(
    *,
    hybrid_payload: dict,
    aya_payload: dict,
    local_safety_report: dict,
    hybrid_source: str,
    hybrid_mirror: Path,
) -> dict:
    config = get_runtime_config()
    resolved_hybrid = hybrid_payload.get("full_summary", hybrid_payload)
    best_safety_report = hybrid_payload.get("best_safety_report")
    live_runtime = fetch_live_runtime()
    runtime_summary_label = "live runtime endpoint evaluation" if Path(hybrid_source).expanduser().exists() else "hybrid runtime validation"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(),
        "public_runtime_url": DEFAULT_LIVE_RUNTIME_URL,
        "recommended_default_runtime": {
            "provider": config.model_provider,
            "chat_model": config.chat_model,
            "extraction_model": config.extraction_model,
            "local_safety_checkpoint": normalize_path_value(config.local_safety_checkpoint),
            "hybrid_safety_enabled": bool(config.local_safety_checkpoint),
            "rule_safety_monitor_enabled": True,
            "semantic_safety_enabled": config.semantic_safety_enabled,
            "decision": "Use the Aya extractor with the promoted local safety checkpoint and rule monitor as the default runtime.",
        },
        "live_deployment_runtime": live_runtime,
        "source_artifacts": {
            "aya_baseline_json": "reports/aya_colab_eval_a100_20260328.json",
            "hybrid_summary_source": hybrid_source,
            "hybrid_summary_mirror": normalize_path_value(str(hybrid_mirror)),
        },
        "extractor_baseline": aya_payload,
        "hybrid_runtime_validation": resolved_hybrid,
        "best_colab_safety_checkpoint": best_safety_report,
        "local_default_safety_checkpoint_eval": local_safety_report,
        "hybrid_vs_extractor_baseline": compare_metrics(aya_payload, resolved_hybrid),
        "recommendation": {
            "ship_default": "hybrid_runtime",
            "why": [
                f"Hybrid runtime preserved zero parse failures while pushing safety recall to 1.0 in the latest {runtime_summary_label}.",
                "The promoted local safety checkpoint can now be auto-discovered by the repo without a private env file.",
                "The pure extractor checkpoints remain useful benchmarks, but the safer runtime stack is the better default for demos and guarded screening.",
            ],
            "known_gaps": [
                "Safety precision is still low, so the stack remains conservative and will over-trigger review flags.",
                "Hinglish coverage remains the weakest language slice in the hybrid runtime evaluation.",
            ],
        },
    }


def build_markdown(report: dict) -> str:
    runtime = report["recommended_default_runtime"]
    baseline = report["extractor_baseline"]["overall"]
    hybrid = report["hybrid_runtime_validation"]["overall"]
    local_safety = report["local_default_safety_checkpoint_eval"]
    local_result = local_safety.get("result", {}) if isinstance(local_safety, dict) else {}
    deltas = report["hybrid_vs_extractor_baseline"]

    lines = [
        "# Best Current System Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Git revision: `{report['git_revision']}`",
        f"- Public runtime URL: `{report['public_runtime_url']}`",
        "",
        "## Default Runtime",
        "",
        f"- Provider: `{runtime['provider']}`",
        f"- Chat model: `{runtime['chat_model']}`",
        f"- Extraction model: `{runtime['extraction_model']}`",
        f"- Hybrid safety enabled: `{runtime['hybrid_safety_enabled']}`",
        f"- Rule safety monitor enabled: `{runtime['rule_safety_monitor_enabled']}`",
        f"- Local safety checkpoint: `{runtime['local_safety_checkpoint']}`",
        "",
        "## Live Deployment Runtime",
        "",
        f"- Provider: `{report['live_deployment_runtime']['provider']}`",
        f"- Chat model: `{report['live_deployment_runtime']['chat_model']}`",
        f"- Extraction model: `{report['live_deployment_runtime']['extraction_model']}`",
        f"- Hybrid safety enabled: `{report['live_deployment_runtime']['hybrid_safety_enabled']}`",
        f"- Cloud voice enabled: `{report['live_deployment_runtime']['cloud_voice_enabled']}`",
        f"- Local safety checkpoint enabled: `{report['live_deployment_runtime']['local_safety_checkpoint_enabled']}`",
        "",
        "## Extractor Baseline",
        "",
        f"- Coverage completeness: `{baseline['coverage_completeness']}`",
        f"- MAE: `{baseline['mae']}`",
        f"- Exact match: `{baseline['exact_match_rate']}`",
        f"- Macro-F1: `{baseline['macro_f1']}`",
        f"- Safety precision: `{baseline['safety_precision']}`",
        f"- Safety recall: `{baseline['safety_recall']}`",
        "",
        "## Hybrid Runtime Validation",
        "",
        f"- Coverage completeness: `{hybrid['coverage_completeness']}`",
        f"- MAE: `{hybrid['mae']}`",
        f"- Exact match: `{hybrid['exact_match_rate']}`",
        f"- Macro-F1: `{hybrid['macro_f1']}`",
        f"- Safety precision: `{hybrid['safety_precision']}`",
        f"- Safety recall: `{hybrid['safety_recall']}`",
        "",
        "## Delta Vs Extractor Baseline",
        "",
    ]
    for metric, delta in deltas.items():
        lines.append(f"- `{metric}`: `{delta:+.3f}`")

    lines.extend(
        [
            "",
            "## Local Default Safety Checkpoint",
            "",
            f"- Status: `{local_safety.get('status', 'unknown')}`",
        ]
    )
    if local_result:
        lines.extend(
            [
                f"- Accuracy: `{local_result.get('accuracy')}`",
                f"- Macro-F1: `{local_result.get('macro_f1')}`",
                f"- Model path: `{local_result.get('model_path')}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- Ship default: `{report['recommendation']['ship_default']}`",
        ]
    )
    for reason in report["recommendation"]["why"]:
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("## Known Gaps")
    lines.append("")
    for note in report["recommendation"]["known_gaps"]:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    for key, value in report["source_artifacts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    hybrid_mirror = Path(args.hybrid_summary_mirror)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    local_safety_report_json = Path(args.local_safety_report_json)

    try:
        hybrid_payload = load_json_source(args.hybrid_summary_source)
        save_json(hybrid_mirror, hybrid_payload)
    except Exception:
        if not hybrid_mirror.exists():
            raise
        hybrid_payload = json.loads(hybrid_mirror.read_text(encoding="utf-8"))

    aya_payload = json.loads(Path(args.aya_baseline_json).read_text(encoding="utf-8"))
    local_safety_report = evaluate_local_safety_checkpoint(get_runtime_config().local_safety_checkpoint, device=args.device)
    save_json(local_safety_report_json, local_safety_report)

    report = build_report(
        hybrid_payload=hybrid_payload,
        aya_payload=aya_payload,
        local_safety_report=local_safety_report,
        hybrid_source=args.hybrid_summary_source,
        hybrid_mirror=hybrid_mirror,
    )
    save_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")
    print(output_json)
    print(output_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
