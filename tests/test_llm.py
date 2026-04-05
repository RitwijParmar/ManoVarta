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


def _local_config():
    return RuntimeConfig(
        model_provider="local",
        chat_model="/models/qwen2.5-0.5b-instruct",
        extraction_model="/models/qwen2.5-0.5b-instruct",
        safety_model="/models/qwen2.5-0.5b-instruct",
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


def test_local_responder_uses_self_hosted_provider(monkeypatch):
    class _Response:
        def __init__(self, content):
            self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]

    class _FakeClient:
        def chat_completion(self, *, messages, temperature, max_tokens):
            return _Response("Take your time. What feels heaviest right now?")

    monkeypatch.setattr("manovarta_core.llm._build_text_generation_client", lambda config, model_name: _FakeClient())
    responder = HuggingFaceResponder(_local_config())
    session = ChatSession(session_id="local-session", language="en", turns=[Turn(turn_id=1, speaker="user", text="I feel overwhelmed.", language_tag="en")])
    snapshot = ScreeningSnapshot(
        language="en",
        items={},
        evidence_spans=[],
        unresolved_items=[],
        totals={"PHQ9": None, "GAD7": None},
        safety=SafetyFlag(level="none"),
        coverage=CoveragePlan(total_items=16, touched_items=0, completion_ratio=0.0, dialogue=DialoguePlan()),
    )

    reply, source = responder.compose_reply(session, snapshot, None, "Fallback")

    assert reply == "Take your time. What feels heaviest right now?"
    assert source == "local"


def test_huggingface_extractor_stays_disabled_without_token():
    extractor = HuggingFaceExtractor(_disabled_config())
    assert extractor.enabled is False


def test_huggingface_extractor_candidate_prompt_pushes_indirect_coverage():
    extractor = HuggingFaceExtractor(_disabled_config())

    messages = extractor._build_candidate_messages(
        "en",
        "assistant: What has felt hardest lately?\nuser: I stare at the same screen, skip meals, and feel like I waste everyone's time.",
        extractor._item_lines(),
    )

    assert "supported_items" in messages[0]["content"]
    assert "staring at the same screen" in messages[1]["content"]
    assert "missed meals" in messages[1]["content"]
    assert "wasting everyone's time" in messages[1]["content"]


def test_huggingface_extractor_merges_candidate_and_final_items():
    extractor = HuggingFaceExtractor(_disabled_config())

    merged = extractor._merge_payloads(
        {
            "items": [
                {
                    "item_id": "phq_q5_appetite",
                    "value": 1,
                    "evidence_quote": "I still had not eaten properly.",
                    "confidence_note": "Missed meals.",
                }
            ],
            "safety_level": "none",
            "safety_cues": [],
            "notes": "candidate",
        },
        {
            "items": [
                {
                    "item_id": "phq_q6_worthlessness",
                    "value": 2,
                    "evidence_quote": "I am wasting everyone's time.",
                    "confidence_note": "Self-blame.",
                },
                {
                    "item_id": "phq_q5_appetite",
                    "value": 2,
                    "evidence_quote": "Late afternoon and still had not eaten properly.",
                    "confidence_note": "Clear appetite disruption.",
                },
            ],
            "safety_level": "review",
            "safety_cues": ["burden language"],
            "notes": "final",
        },
    )

    items = {item["item_id"]: item for item in merged["items"]}
    assert items["phq_q5_appetite"]["value"] == 2
    assert items["phq_q6_worthlessness"]["value"] == 2
    assert merged["safety_level"] == "review"
    assert "burden language" in merged["safety_cues"]


def test_huggingface_extractor_uses_user_only_compact_transcript():
    extractor = HuggingFaceExtractor(_disabled_config())
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What feels heaviest lately?", language_tag="hi"),
        Turn(turn_id=2, speaker="user", text="मन किसी चीज़ में टिकता नहीं और रात में नींद टूट जाती है।", language_tag="hi"),
        Turn(turn_id=3, speaker="assistant", text="Anything else?", language_tag="hi"),
        Turn(turn_id=4, speaker="user", text="भूख भी पहले जैसी नहीं है और खुद पर गुस्सा आता है।", language_tag="hi"),
    ]

    transcript = extractor._build_extraction_transcript(turns)

    assert "assistant:" not in transcript
    assert "user: मन किसी चीज़ में टिकता नहीं" in transcript
    assert "user: भूख भी पहले जैसी नहीं है" in transcript


def test_huggingface_extractor_retries_with_compact_prompt_after_failure():
    extractor = HuggingFaceExtractor(_disabled_config())

    class _Response:
        def __init__(self, content):
            self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]

    class _FakeClient:
        def __init__(self):
            self.calls = []

        def chat_completion(self, *, messages, temperature, max_tokens):
            self.calls.append({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
            if len(self.calls) == 1:
                raise RuntimeError("transient upstream failure")
            return _Response('{"items":[{"item_id":"phq_q6_worthlessness","value":2,"evidence_quote":"मैं अच्छी माँ नहीं हूँ"}],"safety_level":"none","safety_cues":[],"notes":"ok"}')

    extractor._client = _FakeClient()
    turns = [
        Turn(turn_id=1, speaker="assistant", text="इन दिनों सबसे भारी क्या है?", language_tag="hi"),
        Turn(turn_id=2, speaker="user", text="अक्सर लगता है मैं अच्छी माँ नहीं हूँ।", language_tag="hi"),
    ]

    payload = extractor.extract(turns, "hi")

    assert payload is not None
    assert payload["items"][0]["item_id"] == "phq_q6_worthlessness"
    assert len(extractor._client.calls) == 2
    assert "User disclosures:" in extractor._client.calls[1]["messages"][1]["content"]


def test_huggingface_extractor_builds_english_windows_with_context():
    extractor = HuggingFaceExtractor(_disabled_config())
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has been feeling hardest?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="I feel flat most of the day.", language_tag="en"),
        Turn(turn_id=3, speaker="assistant", text="What happens at night?", language_tag="en"),
        Turn(turn_id=4, speaker="user", text="I replay whole conversations and cannot switch off.", language_tag="en"),
        Turn(turn_id=5, speaker="assistant", text="Anything else?", language_tag="en"),
        Turn(turn_id=6, speaker="user", text="Sometimes it feels like everyone would be better off without me around.", language_tag="en"),
    ]

    windows = extractor._build_english_window_transcripts(turns)

    assert len(windows) >= 3
    assert windows[0].startswith("assistant: What has been feeling hardest?")
    assert "assistant: What happens at night?" in windows[1]
    assert any("better off without me around" in window for window in windows)


def test_huggingface_extractor_english_windows_merge_with_verifier():
    extractor = HuggingFaceExtractor(_disabled_config())

    class _Response:
        def __init__(self, content):
            self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]

    class _FakeClient:
        def __init__(self):
            self.calls = []

        def chat_completion(self, *, messages, temperature, max_tokens):
            self.calls.append({"messages": messages, "max_tokens": max_tokens})
            if len(self.calls) == 1:
                return _Response('{"items":[{"item_id":"gad_q1_nervous","value":2,"evidence_quote":"my jaw stays tight all day"}],"safety_level":"none","safety_cues":[],"notes":"window1"}')
            return _Response('{"items":[{"item_id":"gad_q4_trouble_relaxing","value":2,"evidence_quote":"I cannot really switch off"},{"item_id":"phq_q9_self_harm","value":1,"evidence_quote":"everyone would be better off without me around"}],"safety_level":"review","safety_cues":["disappearance language"],"notes":"verifier"}')

    extractor._client = _FakeClient()
    turns = [
        Turn(turn_id=1, speaker="assistant", text="What has stress looked like lately?", language_tag="en"),
        Turn(turn_id=2, speaker="user", text="My jaw stays tight all day before difficult calls.", language_tag="en"),
        Turn(turn_id=3, speaker="assistant", text="What thoughts show up when it gets heavy?", language_tag="en"),
        Turn(turn_id=4, speaker="user", text="I replay whole conversations, cannot really switch off, and sometimes it feels like everyone would be better off without me around.", language_tag="en"),
    ]

    payload = extractor.extract(turns, "en")

    assert payload is not None
    items = {item["item_id"] for item in payload["items"]}
    assert {"gad_q1_nervous", "gad_q4_trouble_relaxing", "phq_q9_self_harm"} <= items
    assert payload["safety_level"] == "review"
    assert "Priority English miss-check items:" in extractor._client.calls[-1]["messages"][1]["content"]


def test_huggingface_extractor_refines_english_anxiety_items():
    extractor = HuggingFaceExtractor(_disabled_config())
    transcript = (
        "assistant: What has your body been doing when stress spikes at work?\n"
        "user: My jaw stays tight all day and I notice I am clenching my hands before difficult calls even start.\n"
        "assistant: And emotionally, what changes after those stressful shifts?\n"
        "user: By the time I get home I replay whole conversations, feel snappy for no good reason, and cannot really switch off.\n"
        "assistant: What do you find yourself worrying about most once you get home?\n"
        "user: Mostly that I am going to say the wrong thing, get written up, and suddenly not be able to cover rent."
    )
    payload = {
        "items": [
            {"item_id": "gad_q2_control_worry", "value": 3, "evidence_quote": "replay whole conversations"},
        ],
        "safety_level": "none",
        "safety_cues": [],
        "notes": "raw",
    }

    refined = extractor._refine_english_anxiety_payload(transcript, payload)
    items = {item["item_id"]: item for item in refined["items"]}

    assert items["gad_q2_control_worry"]["value"] == 2
    assert items["gad_q3_excessive_worry"]["value"] == 2
    assert items["gad_q4_trouble_relaxing"]["value"] == 2
    assert "english_anxiety_refined" in refined["notes"]


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
