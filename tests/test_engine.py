from manovarta_core.engine import RuntimeEngine
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import Turn


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
    assert snapshot.safety.level == "review"
    assert any(span.span_id.startswith("LLM-") for span in snapshot.evidence_spans)
