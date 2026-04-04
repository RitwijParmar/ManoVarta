from pathlib import Path

from tools.generate_assignment_completion_report import (
    PROJECT_ROOT,
    detect_bonus_features,
    detect_deployment_assets,
    detect_voice_layer,
    render_markdown,
)


def test_detect_voice_layer_reports_browser_wrapper():
    voice = detect_voice_layer(PROJECT_ROOT)

    assert voice["status"] == "complete"
    assert voice["browser_voice_controls"] is True
    assert voice["speech_to_text"] is True
    assert voice["text_to_speech"] is True


def test_detect_deployment_assets_finds_new_configs():
    deployment = detect_deployment_assets(PROJECT_ROOT)

    assert deployment["present"]["dockerfile"] is True
    assert deployment["present"]["docker_compose_demo"] is True
    assert deployment["present"]["render_blueprint"] is True


def test_detect_bonus_features_reports_linguistic_personalization():
    bonus = detect_bonus_features(PROJECT_ROOT)

    assert "linguistic_personalization" in bonus["implemented"]


def test_render_markdown_mentions_required_metric_names():
    report = {
        "generated_at": "2026-04-04T00:00:00Z",
        "shipped_baseline": {"tag": "demo-tag"},
        "requirement_status": {
            "multilingual_text_chat": {"status": "complete"},
            "voice_capable_agent": {
                "status": "complete",
                "browser_voice_controls": True,
                "speech_to_text": True,
                "text_to_speech": True,
                "transcript_before_submit": True,
                "note": "voice note",
            },
            "task_1_smart_screening": {"status": "complete"},
            "task_2_llm_inference_engine": {"status": "complete"},
            "task_3_safety_trigger_system": {"status": "complete"},
            "deployment": {
                "status": "complete",
                "present": {
                    "dockerfile": True,
                    "docker_compose_demo": True,
                    "render_blueprint": True,
                    "shipped_bundle": True,
                },
                "note": "deploy note",
            },
            "bonus": {"implemented": ["linguistic_personalization"], "note": "bonus note"},
        },
        "evaluation_validation": {
            "disclosure_efficiency": {
                "stable_item_traces": 10,
                "avg_turns_to_stable_score": 1.5,
                "median_turns_to_stable_score": 1.0,
            },
            "safety_accuracy": {"precision": 0.3, "recall": 1.0, "f1": 0.46},
            "latency": {
                "cold_start_ms": 100.0,
                "warm_avg_ms": 80.0,
                "warm_median_ms": 70.0,
                "warm_p95_ms": 110.0,
            },
            "discourse_effectiveness": {
                "coverage_completeness": 0.8,
                "exact_match_rate": 0.7,
                "macro_f1": 0.34,
                "parse_failures": 0,
            },
        },
        "remaining_external_step": "none",
    }

    markdown = render_markdown(report)

    assert "Disclosure Efficiency" in markdown
    assert "Safety Accuracy" in markdown
    assert "Latency" in markdown
    assert "Discourse Effectiveness" in markdown
