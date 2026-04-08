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
    assert voice["browser_speech_to_text"] is True
    assert voice["browser_text_to_speech"] is True
    assert voice["cloud_speech_to_text"] is True
    assert voice["cloud_text_to_speech"] is True


def test_detect_deployment_assets_finds_new_configs():
    deployment = detect_deployment_assets(PROJECT_ROOT)

    assert deployment["present"]["dockerfile"] is True
    assert deployment["present"]["docker_compose_demo"] is True
    assert deployment["present"]["render_blueprint"] is True


def test_detect_bonus_features_reports_both_bonus_features():
    bonus = detect_bonus_features(PROJECT_ROOT)

    assert "linguistic_personalization" in bonus["implemented"]
    assert "gamification" in bonus["implemented"]


def test_render_markdown_mentions_required_metric_names():
    report = {
        "generated_at": "2026-04-04T00:00:00Z",
        "shipped_baseline": {"tag": "demo-tag"},
        "requirement_status": {
            "multilingual_text_chat": {"status": "complete"},
            "voice_capable_agent": {
                "status": "complete",
                "browser_voice_controls": True,
                "browser_speech_to_text": True,
                "browser_text_to_speech": True,
                "cloud_speech_to_text": True,
                "cloud_text_to_speech": True,
                "transcript_before_submit": True,
                "note": "voice note",
            },
            "patient_profile_onboarding": {"status": "complete"},
            "clinical_knowledge_base": {"status": "complete"},
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
                "public_runtime_url": "https://example.com",
                "live_runtime": {
                    "hybrid_safety_enabled": True,
                    "cloud_voice_enabled": True,
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
            "bonus_validation": {
                "nudge_feedback_loop_present": True,
                "nudge_queue_after_brief_turn": ["example", "timing"],
                "nudged_touched_delta": 3,
                "nudge_words_added": 19,
                "nudge_evidence_gain": 2,
                "nudge_resolved_gain": 1,
                "nudge_outcome": "helpful",
                "style_adaptation_checks": {"brief_guarded_guided": True},
                "note": "bonus validation note",
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
    assert "Bonus Validation" in markdown
    assert "Nudge outcome" in markdown
    assert "Discourse Effectiveness" in markdown
