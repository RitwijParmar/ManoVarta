from manovarta_core.config import RuntimeConfig
from manovarta_core.llm import HuggingFaceExtractor, HuggingFaceResponder, HuggingFaceSafetyAssessor
from manovarta_core.schemas import ChatSession, CoveragePlan, DialoguePlan, DisclosureMetrics, SafetyFlag, ScreeningSnapshot, Turn, UserStyleProfile


def _disabled_config():
    return RuntimeConfig(
        model_provider="huggingface",
        chat_model="Qwen/Qwen2.5-7B-Instruct",
        extraction_model="CohereLabs/aya-expanse-32b",
        safety_model="CohereLabs/aya-expanse-32b",
        hf_token=None,
        hf_timeout=30.0,
        assistant_temperature=0.2,
        assistant_max_tokens=180,
        extraction_max_tokens=900,
        safety_max_tokens=180,
        semantic_safety_model=None,
        semantic_safety_review_threshold=0.64,
        semantic_safety_urgent_threshold=0.72,
    )


def test_huggingface_responder_stays_disabled_without_token():
    responder = HuggingFaceResponder(_disabled_config())
    assert responder.enabled is False


def test_huggingface_extractor_stays_disabled_without_token():
    extractor = HuggingFaceExtractor(_disabled_config())
    assert extractor.enabled is False


def test_huggingface_safety_assessor_stays_disabled_without_token():
    assessor = HuggingFaceSafetyAssessor(_disabled_config())
    assert assessor.enabled is False


def test_huggingface_responder_builds_personalized_prompt_instructions():
    responder = HuggingFaceResponder(_disabled_config())
    session = ChatSession(
        session_id="test-session",
        language="hinglish",
        turns=[
            Turn(turn_id=1, speaker="user", text="Bas tired feel hota hai and sleep toot jaati hai.", language_tag="hinglish"),
        ],
    )
    snapshot = ScreeningSnapshot(
        language="hinglish",
        items={},
        evidence_spans=[],
        unresolved_items=["phq_q3_sleep"],
        totals={"PHQ9": None, "GAD7": None},
        safety=SafetyFlag(level="none"),
        coverage=CoveragePlan(
            total_items=16,
            touched_items=2,
            completion_ratio=0.12,
            dialogue=DialoguePlan(
                stage="exploration",
                next_action="symptom_probe",
                current_topic="sleep",
                target_topic="sleep",
                rationale="Sleep is the clearest open topic.",
                transition_hint="Stay with sleep and ask one focused follow-up.",
                user_style=UserStyleProfile(
                    verbosity="brief",
                    openness="cautious",
                    code_mix="high",
                    distress_trend="steady",
                    empathy_level="high",
                ),
                disclosure=DisclosureMetrics(
                    user_turns=1,
                    touched_items=2,
                    resolved_items=0,
                    stable_topics=0,
                    items_per_user_turn=2.0,
                    resolved_per_user_turn=0.0,
                ),
            ),
        ),
    )

    messages = responder._build_messages(session, snapshot, None, "Fallback question")
    assert "Mirror the user's pacing and level of detail" in messages[0]["content"]
    assert "code-mix is medium or high" in messages[0]["content"]
    assert "aligned with the user's style" in messages[1]["content"]
