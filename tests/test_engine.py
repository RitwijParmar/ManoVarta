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


class ExplicitDenialExtractor:
    enabled = True

    def extract(self, turns, language):
        return {
            "items": [
                {
                    "item_id": "phq_q9_self_harm",
                    "value": 0,
                    "evidence_quote": "I have not had thoughts of hurting myself or not wanting to be alive.",
                    "confidence_note": "Explicit denial of self-harm or suicidal intent.",
                }
            ],
            "safety_level": "none",
            "safety_cues": [],
            "notes": "Explicit denial.",
        }


class RecordingExtractor:
    enabled = True

    def __init__(self):
        self.seen_speakers = []

    def extract(self, turns, language):
        self.seen_speakers = [turn.speaker for turn in turns]
        return {
            "items": [
                {
                    "item_id": "phq_q2_low_mood",
                    "value": 2,
                    "evidence_quote": "My mood stays heavy most of the day.",
                    "confidence_note": "Persistent heaviness through the day.",
                }
            ],
            "safety_level": "none",
            "safety_cues": [],
            "notes": "Recorded user-only analysis turns.",
        }


class CorroboratingSleepExtractor:
    enabled = True

    def extract(self, turns, language):
        return {
            "items": [
                {
                    "item_id": "phq_q3_sleep",
                    "value": 3,
                    "evidence_quote": "Mostly waking during the night and then too early, probably five nights a week.",
                    "confidence_note": "Repeated nighttime waking and early waking most nights.",
                }
            ],
            "safety_level": "none",
            "safety_cues": [],
            "notes": "Corroborated sleep evidence.",
        }


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


def test_runtime_engine_resolves_explicit_negative_closure_items():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="Have thoughts of hurting yourself shown up at all?", language_tag="en"),
        Turn(
            turn_id=2,
            speaker="user",
            text="I have not had thoughts of hurting myself or not wanting to be alive.",
            language_tag="en",
        ),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=ExplicitDenialExtractor(),
    )

    snapshot = engine.analyze(turns, "en")

    assert snapshot.items["phq_q9_self_harm"].value == 0
    assert snapshot.items["phq_q9_self_harm"].status == "resolved"


def test_runtime_engine_passes_full_conversation_into_extractor_for_contextual_scoring():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="How has your mood been?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="My mood stays heavy most of the day.", language_tag="en"),
        Turn(turn_id=3, speaker="assistant", text="Has appetite shifted too?", language_tag="en"),
    ]
    extractor = RecordingExtractor()
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=extractor,
    )

    snapshot = engine.analyze(turns, "en")

    assert extractor.seen_speakers == ["assistant", "user", "assistant"]
    assert snapshot.items["phq_q2_low_mood"].value == 2


def test_runtime_engine_uses_assistant_question_context_for_brief_hindi_answers():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="क्या आपको रात में सोने की शुरुआत करने में मुश्किल होती है?", language_tag="hi"),
        Turn(turn_id=2, speaker="user", text="मुश्किल होती है", language_tag="hi"),
        Turn(turn_id=3, speaker="assistant", text="क्या आजकल आपको किसी चीज़ पर ध्यान लगाने या फोकस करने में मुश्किल महसूस हो रही है?", language_tag="hi"),
        Turn(turn_id=4, speaker="user", text="हो रही है जब मैं पढ़ाई के लिए बैठता हूं नहीं कर पाता", language_tag="hi"),
        Turn(turn_id=5, speaker="assistant", text="क्या इस वजह से आपको थकान या ऊर्जा की कमी भी महसूस होती है?", language_tag="hi"),
        Turn(turn_id=6, speaker="user", text="होती है काफी थकान और ऊर्जा की कमी महसूस होती है", language_tag="hi"),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=None,
    )

    snapshot = engine.analyze(turns, "hi", use_llm=False)

    assert snapshot.items["phq_q3_sleep"].value is not None
    assert snapshot.items["phq_q7_concentration"].value is not None
    assert snapshot.items["phq_q4_fatigue"].value is not None


def test_runtime_engine_resolves_correlated_one_step_sleep_difference_when_evidence_is_shared():
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has sleep been like?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="Sleep has been broken for the last two weeks. I wake around 3 or 4 and drag through the next day.", language_tag="en"),
        Turn(turn_id=3, speaker="assistant", text="What tends to happen once you wake up?", language_tag="en"),
        Turn(turn_id=4, speaker="user", text="Mostly waking during the night and then too early, probably five nights a week.", language_tag="en"),
    ]
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        extractor=CorroboratingSleepExtractor(),
    )

    snapshot = engine.analyze(turns, "en")

    assert snapshot.items["phq_q3_sleep"].status == "resolved"
    assert snapshot.items["phq_q3_sleep"].value in {2, 3}
    assert snapshot.items["phq_q3_sleep"].source == "hybrid"
