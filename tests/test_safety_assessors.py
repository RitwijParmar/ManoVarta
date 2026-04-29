from manovarta_core.safety_assessors import (
    CompositeSafetyAssessor,
    LocalSafetyCheckpointAssessor,
    build_safety_assessment_text,
    build_turns_from_extractor_example,
    compose_runtime_safety_flag,
    evaluate_safety_stack,
    merge_safety_flags,
)
from manovarta_core.schemas import SafetyFlag, Turn


class StubAssessor:
    enabled = True

    def assess(self, turns, language):
        del turns, language
        return SafetyFlag(
            level="urgent",
            cues=["stub:urgent"],
            rationale="Stub assessor flagged urgent risk.",
            needs_human_review=True,
        )


def test_merge_safety_flags_keeps_highest_severity_and_combines_cues():
    merged = merge_safety_flags(
        SafetyFlag(level="review", cues=["rule:review"], rationale="Rule flagged review."),
        SafetyFlag(level="urgent", cues=["model:urgent"], rationale="Model flagged urgent."),
    )

    assert merged.level == "urgent"
    assert merged.needs_human_review is True
    assert merged.cues == ["rule:review", "model:urgent"]
    assert "Rule flagged review." in merged.rationale
    assert "Model flagged urgent." in merged.rationale


def test_build_turns_from_extractor_example_recovers_transcript_turns():
    example = {
        "language": "hinglish",
        "text": (
            "<|system|>\nExtract\n"
            "<|user|>\nLanguage: hinglish\nTranscript:\n"
            "assistant: What has felt the heaviest?\n"
            "user: Kabhi lagta hai bas gayab ho jaun.\n"
            "<|assistant|>\n{\"items\": [], \"safety_level\": \"review\"}"
        ),
    }

    turns = build_turns_from_extractor_example(example)

    assert len(turns) == 2
    assert turns[0].speaker == "assistant"
    assert turns[1].speaker == "user"
    assert turns[1].language_tag == "hinglish"


def test_build_safety_assessment_text_matches_recent_context_shape():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="How have things been?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="I feel low most days.", language_tag="en"),
        Turn(turn_id=3, speaker="user", text="Sometimes I wish I could disappear.", language_tag="en"),
    ]

    text = build_safety_assessment_text(turns)

    assert "Most recent disclosure:" in text
    assert "Recent context:" in text
    assert "Sometimes I wish I could disappear." in text


def test_composite_safety_assessor_merges_multiple_assessors():
    assessor = CompositeSafetyAssessor([StubAssessor(), None])
    turns = [Turn(turn_id=1, speaker="user", text="I feel awful.", language_tag="en")]

    flag = assessor.assess(turns, "en")

    assert flag is not None
    assert flag.level == "urgent"
    assert "stub:urgent" in flag.cues


def test_compose_runtime_safety_flag_ignores_extractor_only_alerts():
    merged = compose_runtime_safety_flag(
        extractor_flag=SafetyFlag(
            level="review",
            cues=["extractor:review"],
            rationale="Extractor suggested review.",
            needs_human_review=True,
        )
    )

    assert merged.level == "none"
    assert merged.needs_human_review is False


def test_compose_runtime_safety_flag_keeps_runtime_signal_and_marks_extractor_advisory():
    merged = compose_runtime_safety_flag(
        extractor_flag=SafetyFlag(
            level="urgent",
            cues=["llm:urgent"],
            rationale="Extractor suggested urgent risk.",
            needs_human_review=True,
        ),
        rule_flag=SafetyFlag(
            level="review",
            cues=["rule:review"],
            rationale="Rule monitor flagged review.",
            needs_human_review=True,
        ),
    )

    assert merged.level == "review"
    assert "rule:review" in merged.cues
    assert "extractor_advisory:urgent" in merged.cues
    assert "advisory" in (merged.rationale or "").lower()


def test_evaluate_safety_stack_can_combine_rule_and_checkpoint_levels():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has felt hardest?", language_tag="hinglish"),
        Turn(turn_id=2, speaker="user", text="Kabhi lagta hai mere bina sab theek hoga.", language_tag="hinglish"),
    ]

    result = evaluate_safety_stack(
        extractor_safety_level="none",
        turns=turns,
        language="hinglish",
        use_rule_safety_monitor=True,
        safety_assessor=StubAssessor(),
    )

    assert result["components"]["extractor"] == "none"
    assert result["components"]["rule"] == "review"
    assert result["components"]["checkpoint"] == "urgent"
    assert result["flag"].level == "urgent"


def test_evaluate_safety_stack_does_not_escalate_extractor_signal_without_support():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has felt hardest?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="I feel exhausted and low.", language_tag="en"),
    ]

    result = evaluate_safety_stack(
        extractor_safety_level="review",
        turns=turns,
        language="en",
        use_rule_safety_monitor=False,
        safety_assessor=None,
    )

    assert result["components"]["extractor"] == "review"
    assert result["flag"].level == "none"


def test_local_safety_checkpoint_assessor_is_disabled_without_checkpoint():
    assessor = LocalSafetyCheckpointAssessor(None)

    assert assessor.enabled is False
    assert assessor.assess([], "en") is None


def test_local_safety_checkpoint_assessor_warmup_loads_backend_once(tmp_path, monkeypatch):
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    assessor = LocalSafetyCheckpointAssessor(checkpoint)
    calls: list[str] = []

    def fake_load_backend():
        calls.append("load")
        assessor._backend = ("torch", "tokenizer", "model", "cpu")
        assessor._load_complete.set()

    monkeypatch.setattr(assessor, "_load_backend", fake_load_backend)

    assert assessor.warmup() is True
    assert assessor.warmup() is True
    assert calls == ["load"]
