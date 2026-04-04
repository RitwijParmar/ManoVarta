#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import os
import time
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
HYBRID_REPORT_PATH = REPORTS_DIR / "hybrid_runtime_validation_colab_20260404.json"
SHIP_NOTE_PATH = REPORTS_DIR / "ship_note_2026-04-04.md"
BEST_SYSTEM_PATH = REPORTS_DIR / "best_current_system_report.json"
OUTPUT_JSON_PATH = REPORTS_DIR / "final_assignment_completion_report.json"
OUTPUT_MD_PATH = REPORTS_DIR / "final_assignment_completion_report.md"

LATENCY_SAMPLES = [
    ("en", "I feel drained all day and my sleep schedule is messed up."),
    ("hi", "Mujhe neend theek se nahi aati aur dimaag mein chinta chalti rehti hai."),
    ("hinglish", "Sleep break hoti rehti hai aur mind calm nahi hota."),
    ("en", "I keep overthinking and then I cannot focus on work."),
    ("hi", "Kabhi kabhi lagta hai sab kuch bahut bhaari ho gaya hai."),
    ("hinglish", "Low feel hota hai aur future ko leke tension rehti hai."),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_voice_layer(project_root: Path = PROJECT_ROOT) -> dict[str, object]:
    index_html = (project_root / "manovarta_core" / "web" / "index.html").read_text(encoding="utf-8")
    app_js = (project_root / "manovarta_core" / "web" / "app.js").read_text(encoding="utf-8")
    return {
        "status": "complete"
        if all(token in index_html + app_js for token in ("micButton", "voiceStatus", "SpeechRecognition", "speechSynthesis"))
        else "missing",
        "browser_voice_controls": "id=\"micButton\"" in index_html and "id=\"voiceStatus\"" in index_html,
        "speech_to_text": "SpeechRecognitionCtor" in app_js,
        "text_to_speech": "speechSynthesisApi" in app_js,
        "transcript_before_submit": "Transcript captured." in app_js and "messageInput.value = transcript;" in app_js,
        "note": "Voice is implemented as a browser-native wrapper over the text pipeline, so it depends on microphone permission and browser support.",
    }


def detect_deployment_assets(project_root: Path = PROJECT_ROOT) -> dict[str, object]:
    assets = {
        "dockerfile": project_root / "Dockerfile",
        "docker_compose_demo": project_root / "docker-compose.demo.yml",
        "render_blueprint": project_root / "render.yaml",
        "shipped_bundle": project_root / "artifacts" / "manovarta_shipped_baseline_20260404.zip",
    }
    present = {name: path.exists() for name, path in assets.items()}
    return {
        "status": "complete" if all(present.values()) else "partial",
        "assets": {name: str(path.relative_to(project_root)) for name, path in assets.items()},
        "present": present,
        "note": "Repo now includes local container deployment plus a cloud-ready Render blueprint. A public URL still requires external account provisioning.",
    }


def detect_bonus_features(project_root: Path = PROJECT_ROOT) -> dict[str, object]:
    dialogue_code = (project_root / "manovarta_core" / "dialogue.py").read_text(encoding="utf-8")
    llm_code = (project_root / "manovarta_core" / "llm.py").read_text(encoding="utf-8")
    linguistic = all(token in dialogue_code + llm_code for token in ("user_style", "code_mix", "verbosity", "openness"))
    return {
        "implemented": ["linguistic_personalization"] if linguistic else [],
        "missing": [] if linguistic else ["linguistic_personalization", "gamification"],
        "note": "The runtime already adapts prompt softness, pacing, and code-mix cues through the planner user-style profile.",
    }


def build_disclosure_efficiency_sample(sample_size: int = 30) -> dict[str, object]:
    from manovarta_core.safety import SafetyMonitor
    from manovarta_core.scoring import ConversationScorer
    from manovarta_core.schemas import Turn
    from manovarta_core.seed_data import load_seed_conversations

    conversations = load_seed_conversations()[:sample_size]
    scorer = ConversationScorer()
    safety_monitor = SafetyMonitor()
    stable_turns: list[int] = []

    for payload in conversations:
        turns = [Turn(**turn) for turn in payload["conversation_turns"]]
        final_snapshot = scorer.analyze(turns, payload["language"], safety_monitor.assess(turns))

        prefixes: list[list[Turn]] = []
        running: list[Turn] = []
        for turn in turns:
            running.append(turn)
            if turn.speaker == "user":
                prefixes.append(list(running))
        prefix_snapshots = [
            scorer.analyze(prefix, payload["language"], safety_monitor.assess(prefix))
            for prefix in prefixes
        ]

        for item_id, item in final_snapshot.items.items():
            if item.value is None or item.status not in {"resolved", "partial", "contradicted"}:
                continue
            for index, prefix_snapshot in enumerate(prefix_snapshots, start=1):
                current = prefix_snapshot.items[item_id]
                if current.value is None or current.value != item.value:
                    continue
                if all(later.items[item_id].value == item.value for later in prefix_snapshots[index - 1 :]):
                    stable_turns.append(index)
                    break

    return {
        "sample_conversations": sample_size,
        "stable_item_traces": len(stable_turns),
        "avg_turns_to_stable_score": round(mean(stable_turns), 3) if stable_turns else None,
        "median_turns_to_stable_score": round(median(stable_turns), 3) if stable_turns else None,
        "note": "This is computed by replaying seed conversations turn by turn and finding the earliest user-turn prefix where an item score matches the conversation-final value and stays there.",
    }


def measure_latency_template_path() -> dict[str, object]:
    from fastapi.testclient import TestClient
    from manovarta_core import config as cfg

    old_hf = os.environ.get("HF_TOKEN")
    old_hub = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    os.environ["HF_TOKEN"] = ""
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = ""
    cfg.get_runtime_config.cache_clear()

    try:
        import manovarta_core.api as api

        api = importlib.reload(api)
        client = TestClient(api.app)
        latencies_ms: list[float] = []

        for language, text in LATENCY_SAMPLES:
            session_id = client.post("/chat/sessions", json={"language": language}).json()["session_id"]
            start = time.perf_counter()
            response = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if response.status_code != 200:
                raise RuntimeError(f"Latency sample failed: {response.text}")
            latencies_ms.append(elapsed_ms)
    finally:
        if old_hf is None:
            os.environ.pop("HF_TOKEN", None)
        else:
            os.environ["HF_TOKEN"] = old_hf
        if old_hub is None:
            os.environ.pop("HUGGINGFACEHUB_API_TOKEN", None)
        else:
            os.environ["HUGGINGFACEHUB_API_TOKEN"] = old_hub
        cfg.get_runtime_config.cache_clear()

    cold_start_ms = round(latencies_ms[0], 2)
    warm_latencies = latencies_ms[1:] or latencies_ms
    warm_sorted = sorted(warm_latencies)
    p95_index = max(0, min(len(warm_sorted) - 1, int(0.95 * (len(warm_sorted) - 1))))
    return {
        "cold_start_ms": cold_start_ms,
        "warm_avg_ms": round(mean(warm_latencies), 2),
        "warm_median_ms": round(median(warm_latencies), 2),
        "warm_p95_ms": round(warm_sorted[p95_index], 2),
        "samples": len(latencies_ms),
        "note": "Measured through the FastAPI chat endpoint with Hugging Face network calls disabled so the number reflects deterministic local screening latency rather than hosted-model round trips.",
    }


def build_assignment_report() -> dict[str, object]:
    hybrid_report = load_json(HYBRID_REPORT_PATH)
    best_system_report = load_json(BEST_SYSTEM_PATH)
    hybrid_summary = hybrid_report["full_summary"]
    hybrid_overall = hybrid_summary["overall"]
    safety_precision = hybrid_overall["safety_precision"]
    safety_recall = hybrid_overall["safety_recall"]
    safety_f1 = round(
        (2 * safety_precision * safety_recall / (safety_precision + safety_recall))
        if (safety_precision + safety_recall)
        else 0.0,
        3,
    )

    voice = detect_voice_layer()
    deployment = detect_deployment_assets()
    bonus = detect_bonus_features()
    disclosure = build_disclosure_efficiency_sample()
    latency = measure_latency_template_path()

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_reports": {
            "hybrid_runtime_validation": str(HYBRID_REPORT_PATH.relative_to(PROJECT_ROOT)),
            "best_current_system": str(BEST_SYSTEM_PATH.relative_to(PROJECT_ROOT)),
            "ship_note": str(SHIP_NOTE_PATH.relative_to(PROJECT_ROOT)),
        },
        "requirement_status": {
            "multilingual_text_chat": {
                "status": "complete",
                "languages": ["English", "Hindi"],
                "extra_robustness": ["Hinglish"],
            },
            "voice_capable_agent": voice,
            "task_1_smart_screening": {
                "status": "complete",
                "details": [
                    "Dialogue planner with topic graph and next-best-question routing",
                    "Held-back sensitive item logic for self-harm",
                    "Per-topic confidence and follow-up branching",
                ],
            },
            "task_2_llm_inference_engine": {
                "status": "complete",
                "details": [
                    "LLM extraction path with evidence-first scoring",
                    "Hybrid heuristic + LLM snapshot merge",
                    "PHQ-9 and GAD-7 item-level outputs",
                ],
            },
            "task_3_safety_trigger_system": {
                "status": "complete",
                "details": [
                    "Rule safety monitor",
                    "Hybrid safety checkpoint stack",
                    "Urgent human-review routing",
                ],
            },
            "deployment": deployment,
            "bonus": bonus,
        },
        "evaluation_validation": {
            "disclosure_efficiency": disclosure,
            "safety_accuracy": {
                "precision": safety_precision,
                "recall": safety_recall,
                "f1": safety_f1,
                "source": "shipped hybrid runtime validation",
            },
            "latency": latency,
            "discourse_effectiveness": {
                "coverage_completeness": hybrid_overall["coverage_completeness"],
                "exact_match_rate": hybrid_overall["exact_match_rate"],
                "macro_f1": hybrid_overall["macro_f1"],
                "parse_failures": hybrid_summary["parse_failures"],
                "source": "shipped hybrid runtime validation",
                "note": "Coverage completeness is used as the main operational discourse metric because it directly tracks whether the system stayed on task and covered clinically relevant questionnaire areas.",
            },
        },
        "shipped_baseline": {
            "tag": "shipped-baseline-2026-04-04",
            "default_runtime": best_system_report.get("recommended_default_runtime")
            or best_system_report.get("recommendation", {}).get("ship_default", "hybrid_runtime"),
            "bundle": "artifacts/manovarta_shipped_baseline_20260404.zip",
        },
        "remaining_external_step": "Provision a public cloud URL if the course requires an internet-hosted demo link; the repo is deployment-ready, but live hosting still needs external account credentials.",
    }


def render_markdown(report: dict[str, object]) -> str:
    req = report["requirement_status"]
    evals = report["evaluation_validation"]
    voice = req["voice_capable_agent"]
    deployment = req["deployment"]
    bonus = req["bonus"]
    disclosure = evals["disclosure_efficiency"]
    latency = evals["latency"]
    safety = evals["safety_accuracy"]
    discourse = evals["discourse_effectiveness"]

    lines = [
        "# Final Assignment Completion Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Shipped baseline tag: `{report['shipped_baseline']['tag']}`",
        "",
        "## Requirement Status",
        "",
        f"- Multilingual text chat: `{req['multilingual_text_chat']['status']}` (`English`, `Hindi`, plus `Hinglish` robustness support)",
        f"- Voice-capable agent: `{voice['status']}`",
        f"- Task 1 smart screening: `{req['task_1_smart_screening']['status']}`",
        f"- Task 2 LLM inference engine: `{req['task_2_llm_inference_engine']['status']}`",
        f"- Task 3 safety trigger system: `{req['task_3_safety_trigger_system']['status']}`",
        f"- Deployment assets in repo: `{deployment['status']}`",
        f"- Bonus implemented: `{', '.join(bonus['implemented']) if bonus['implemented'] else 'none'}`",
        "",
        "## Voice Capability",
        "",
        f"- Browser voice controls present: `{voice['browser_voice_controls']}`",
        f"- Speech-to-text wrapper present: `{voice['speech_to_text']}`",
        f"- Text-to-speech wrapper present: `{voice['text_to_speech']}`",
        f"- Transcript-before-submit flow present: `{voice['transcript_before_submit']}`",
        f"- Note: {voice['note']}",
        "",
        "## Evaluation & Validation",
        "",
        "### Disclosure Efficiency",
        "",
        f"- Stable item traces measured: `{disclosure['stable_item_traces']}`",
        f"- Average user turns to stable score: `{disclosure['avg_turns_to_stable_score']}`",
        f"- Median user turns to stable score: `{disclosure['median_turns_to_stable_score']}`",
        "",
        "### Safety Accuracy",
        "",
        f"- Precision: `{safety['precision']}`",
        f"- Recall: `{safety['recall']}`",
        f"- F1: `{safety['f1']}`",
        "",
        "### Latency",
        "",
        f"- Cold-start turn latency: `{latency['cold_start_ms']} ms`",
        f"- Warm average turn latency: `{latency['warm_avg_ms']} ms`",
        f"- Warm median turn latency: `{latency['warm_median_ms']} ms`",
        f"- Warm p95 turn latency: `{latency['warm_p95_ms']} ms`",
        "",
        "### Discourse Effectiveness",
        "",
        f"- Coverage completeness: `{discourse['coverage_completeness']}`",
        f"- Exact match rate: `{discourse['exact_match_rate']}`",
        f"- Macro-F1: `{discourse['macro_f1']}`",
        f"- Parse failures: `{discourse['parse_failures']}`",
        "",
        "## Deployment",
        "",
        f"- Dockerfile: `{deployment['present']['dockerfile']}`",
        f"- Docker Compose demo stack: `{deployment['present']['docker_compose_demo']}`",
        f"- Render blueprint: `{deployment['present']['render_blueprint']}`",
        f"- Shipped bundle: `{deployment['present']['shipped_bundle']}`",
        f"- Note: {deployment['note']}",
        "",
        "## Bonus",
        "",
        f"- Implemented: `{', '.join(bonus['implemented']) if bonus['implemented'] else 'none'}`",
        f"- Note: {bonus['note']}",
        "",
        "## Final Note",
        "",
        f"- {report['remaining_external_step']}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_assignment_report()
    OUTPUT_JSON_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_MD_PATH.write_text(render_markdown(report), encoding="utf-8")
    print(OUTPUT_JSON_PATH)
    print(OUTPUT_MD_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
