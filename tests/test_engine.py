from manovarta_core.engine import RuntimeEngine
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import SafetyFlag, Turn


class StubExtractor:
    enabled = True

    def extract(self, turns, language):
        return {
            "items": [
                {
                    "item_id": "phq_q2_low_mood",
                    "value": 2,
                    "evidence_quote": "Everything feels heavy and I do not enjoy much now.",
                    "confidence_note": "Direct low mood statement.",
                }
            ],
            "safety_level": "review",
            "safety_cues": ["nothing matters"],
            "notes": "Indirect hopelessness language.",
        }


class CompactStubExtractor:
    enabled = True

    def extract(self, turns, language):
        return {
            "items": [
                {
                    "item_id": "phq_q2_low_mood",
                    "value": 2,
                }
            ],
            "safety_level": "high_caution",
        }


class StubSemanticMonitor:
    def assess(self, turns):
        return SafetyFlag(
            level="review",
            cues=["semantic:test"],
            rationale="Semantic review flag.",
            needs_human_review=True,
        )


class StubSafetyAssessor:
    enabled = True

    def assess(self, turns, language):
        return SafetyFlag(
            level="urgent",
            cues=["llm-safety:test"],
            rationale="LLM safety assessor flagged urgent intent.",
            needs_human_review=True,
        )


class FailingExtractor:
    enabled = True

    def extract(self, turns, language):
        raise RuntimeError("extractor failed")


def test_runtime_engine_merges_llm_output_into_snapshot():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has been hardest lately?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Everything feels heavy and I do not enjoy much now.",
            language_tag="en",
        ),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=StubExtractor(),
    )

    snapshot = engine.analyze(turns, "en")

    assert snapshot.mode == "hybrid"
    assert snapshot.items["phq_q2_low_mood"].value == 2
    assert snapshot.items["phq_q2_low_mood"].source in {"llm", "hybrid"}
    assert snapshot.safety.level == "none"
    assert any(span.span_id.startswith("LLM-") for span in snapshot.evidence_spans)


def test_runtime_engine_handles_compact_llm_payload():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has been hardest lately?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Everything feels heavy and I do not enjoy much now.",
            language_tag="en",
        ),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=CompactStubExtractor(),
    )

    snapshot = engine.analyze(turns, "en")

    assert snapshot.mode == "hybrid"
    assert snapshot.items["phq_q2_low_mood"].value == 2
    assert snapshot.safety.level == "none"


def test_runtime_engine_can_merge_semantic_safety_signal():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has been hardest lately?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="Mostly I am just tired.", language_tag="en"),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        semantic_safety_monitor=StubSemanticMonitor(),
        extractor=None,
    )

    snapshot = engine.analyze(turns, "en", use_llm=False)

    assert snapshot.safety.level == "review"
    assert "semantic:test" in snapshot.safety.cues


def test_runtime_engine_can_merge_llm_safety_signal():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="How have evenings been?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="I feel empty and want everything to stop.", language_tag="en"),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        safety_assessor=StubSafetyAssessor(),
        extractor=None,
    )

    snapshot = engine.analyze(turns, "en", use_llm=False)

    assert snapshot.safety.level == "urgent"
    assert "llm-safety:test" in snapshot.safety.cues


def test_runtime_engine_keeps_rule_signal_when_extractor_overcalls_safety():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has felt heaviest?", language_tag="hinglish"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Kabhi lagta hai mere bina sab theek hoga, but I am here talking about it.",
            language_tag="hinglish",
        ),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=StubExtractor(),
    )

    snapshot = engine.analyze(turns, "hinglish")

    assert snapshot.safety.level == "review"
    assert "extractor_advisory:review" in snapshot.safety.cues


def test_runtime_engine_falls_back_to_heuristic_snapshot_when_extractor_raises():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has felt heaviest?", language_tag="hinglish"),
        Turn(
            turn_id=2,
            speaker="user",
            text="Kaafi time se low aur disconnected feel ho raha hai.",
            language_tag="hinglish",
        ),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=FailingExtractor(),
    )

    snapshot = engine.analyze(turns, "hinglish")

    assert snapshot.mode == "heuristic"
    assert snapshot.items["phq_q1_anhedonia"].status == "partial"
    assert snapshot.items["phq_q2_low_mood"].status == "partial"
