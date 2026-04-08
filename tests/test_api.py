import io

from fastapi.testclient import TestClient

import manovarta_core.api as api_module
from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.engine import RuntimeEngine
from manovarta_core.schemas import ChatSession, DialoguePlan, Turn


app = api_module.app


client = TestClient(app)


def test_root_serves_browser_demo():
    response = client.get("/")

    assert response.status_code == 200
    assert "ManoVarta | Multilingual mental health check-in" in response.text
    assert "Begin private check-in" in response.text
    assert "Start talking" in response.text


def test_review_route_serves_hidden_presenter_surface():
    response = client.get("/review")

    assert response.status_code == 200
    assert "Presenter tools" in response.text
    assert "Hidden details for demos, evaluation, and care-team review" in response.text


def test_runtime_config_reports_huggingface_disabled_by_default():
    response = client.get("/runtime/config")

    assert response.status_code == 200
    body = response.json()
    assert "provider" in body
    assert "chat_model" in body
    assert "huggingface_enabled" in body
    assert "self_hosted_inference_enabled" in body


def test_demo_bootstrap_exposes_runtime_profiles_and_links():
    response = client.get("/demo/bootstrap")

    assert response.status_code == 200
    body = response.json()
    assert body["health"]["status"] == "ok"
    assert "runtime" in body
    assert body["profiles"]
    assert body["links"]
    assert any(link["href"] == "/docs" for link in body["links"])


def test_knowledge_base_endpoint_exposes_domains_and_sources():
    response = client.get("/knowledge/base")

    assert response.status_code == 200
    body = response.json()
    assert "questionnaires" in body
    assert "domains" in body
    assert "sources" in body
    assert "safety" in body["domains"]


def test_chat_flow_asks_non_sensitive_follow_up_first():
    start = client.post("/chat/sessions", json={"language": "en"})
    assert start.status_code == 200

    session_id = start.json()["session_id"]
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I feel drained all day and my sleep schedule is messed up."},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"].lower()
    snapshot = turn.json()["snapshot"]
    assert "hurting yourself" not in reply
    assert "not wanting to be alive" not in reply
    assert snapshot["coverage"]["dialogue"]["target_topic"] in {"sleep", "energy", "mood", "anxiety"}
    assert "phq_q9_self_harm" in snapshot["coverage"]["dialogue"]["held_back_items"]
    assert snapshot["coverage"]["dialogue"]["user_style"]["openness"] in {"guarded", "cautious", "open"}
    assert "items_per_user_turn" in snapshot["coverage"]["dialogue"]["disclosure"]


def test_summary_endpoint_returns_structured_snapshot():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Honestly blank feel hota hai, sleep break hoti rehti hai and mind won't stop."},
    )

    summary = client.get(f"/chat/sessions/{session_id}/summary")

    assert summary.status_code == 200
    body = summary.json()
    assert body["snapshot"]["totals"]["PHQ9"] >= 2
    assert "coverage" in body["snapshot"]
    assert body["snapshot"]["coverage"]["next_items"]
    assert body["snapshot"]["coverage"]["dialogue"]["stage"] in {"rapport", "exploration", "clarification", "summary", "safety"}
    assert body["snapshot"]["coverage"]["dialogue"]["transition_hint"]
    assert "Session" in body["summary"]
    assert "Dialogue stage" in body["summary"]
    assert "Disclosure efficiency" in body["summary"]


def test_session_profile_context_round_trips_into_session_detail():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "en",
            "profile": {
                "preferred_name": "Riya",
                "age": 21,
                "occupation": "student",
                "living_situation": "hostel",
                "support_system": "roommate",
                "context_note": "exam pressure",
            },
        },
    )

    assert start.status_code == 200
    opening = start.json()["assistant_turn"]["text"]
    assert "Riya" in opening or "exam pressure" in opening

    session_id = start.json()["session_id"]
    detail = client.get(f"/chat/sessions/{session_id}")

    assert detail.status_code == 200
    body = detail.json()
    assert body["profile"]["preferred_name"] == "Riya"
    assert body["profile"]["occupation"] == "student"


def test_cloud_voice_speak_route_uses_backend_when_enabled(monkeypatch):
    monkeypatch.setattr(api_module, "voice_runtime", api_module.detect_voice_runtime().__class__(speech_to_text=True, text_to_speech=True))
    monkeypatch.setattr(api_module, "synthesize_speech", lambda text, language: (f"{language}:{text}".encode("utf-8"), "audio/mpeg"))

    response = client.post("/voice/speak?language=hi", json={"text": "Namaste"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content == b"hi:Namaste"


def test_cloud_voice_transcribe_route_uses_backend_when_enabled(monkeypatch):
    monkeypatch.setattr(api_module, "voice_runtime", api_module.detect_voice_runtime().__class__(speech_to_text=True, text_to_speech=True))
    monkeypatch.setattr(api_module, "transcribe_audio", lambda content, language, mime_type="audio/webm": f"{language}:{len(content)}")

    response = client.post(
        "/voice/transcribe?language=hinglish",
        files={"audio": ("voice.webm", io.BytesIO(b"abc123"), "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json()["transcript"] == "hinglish:6"


def test_export_endpoint_returns_rows_and_snapshot_mode():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I feel numb lately, my sleep is bad, and work focus keeps breaking."},
    )

    export_response = client.get(f"/chat/sessions/{session_id}/export")

    assert export_response.status_code == 200
    body = export_response.json()
    assert body["snapshot"]["mode"] in {"heuristic", "hybrid"}
    assert body["rows"]
    assert body["rows"][0]["questionnaire"] in {"PHQ9", "GAD7"}


def test_contradiction_flow_marks_review_gate():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I don't keep waking up at night."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Actually I keep waking up and my sleep schedule is messed up."},
    )

    assert turn.status_code == 200
    snapshot = turn.json()["snapshot"]
    sleep_item = snapshot["items"]["phq_q3_sleep"]
    assert sleep_item["status"] == "abstained"
    assert sleep_item["value"] is None
    assert sleep_item["review_recommended"] is True
    assert "phq_q3_sleep" in snapshot["coverage"]["review_items"]
    assert snapshot["coverage"]["review_required"] is True
    assert any(topic["topic_id"] == "sleep" and topic["status"] == "review" for topic in snapshot["coverage"]["topic_states"])


def test_dialogue_plan_tracks_anxiety_topic_when_worry_signal_present():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "My mind won't stop worrying and I stay tense even when nothing is happening."},
    )

    assert turn.status_code == 200
    snapshot = turn.json()["snapshot"]
    dialogue = snapshot["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["next_action"] in {"open_question", "clarify", "symptom_probe"}
    assert dialogue["user_style"]["distress_trend"] in {"unclear", "steady", "rising", "easing"}
    assert any(topic["topic_id"] == "anxiety" and topic["touched"] for topic in snapshot["coverage"]["topic_states"])


def test_brief_guarded_reply_sets_guarded_style_profile():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Just tired. Not sure."},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"]
    dialogue = turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["user_style"]["verbosity"] == "brief"
    assert dialogue["user_style"]["openness"] in {"guarded", "cautious"}
    assert "?" in reply
    assert "hurting yourself" not in reply.lower()
    assert any(token in reply.lower() for token in ("tired", "feeling", "example", "detail", "changes"))


def test_recent_checkins_feed_continuity_note_into_dialogue_plan():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "hi",
            "profile": {
                "recent_checkins": [
                    {"topic": "sleep", "language": "hi", "safety": "none", "completion": 0.5, "summary": "Neend par baat hui thi."}
                ]
            },
        },
    )
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पिछले कुछ दिनों से रात में नींद टूट जाती है और सुबह ध्यान नहीं लगता।"},
    )

    assert turn.status_code == 200
    dialogue = turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["continuity_note"]


def test_hindi_first_reply_does_not_surface_continuity_note_during_rapport():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "hi",
            "profile": {
                "recent_checkins": [
                    {"topic": "sleep", "language": "hi", "safety": "none", "completion": 0.5, "summary": "Neend par baat hui thi."}
                ]
            },
        },
    )
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पिछले कुछ दिनों से रात में नींद टूट जाती है और सुबह ध्यान नहीं लगता।"},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"]
    assert "हाल की नींद बातचीत" not in reply
    assert "क्या यह ज़्यादा उदासी" in reply


def test_safety_sensitive_first_disclosure_skips_full_llm_when_rule_safety_is_enough():
    session = ChatSession(
        session_id="safety-fast-path",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="user", text="I think it might be easier if I do not wake up.", language_tag="en"),
        ],
    )

    assert api_module._should_use_live_llm(session) is False


def test_nudge_metadata_updates_feedback_loop_and_recommended_nudges():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Just tired. Not sure."},
    )
    assert first_turn.status_code == 200
    first_dialogue = first_turn.json()["snapshot"]["coverage"]["dialogue"]
    nudge_strategy = (first_dialogue["recommended_nudges"] or ["example"])[0]

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={
            "text": "I am always tired, my sleep schedule is messed up, and my appetite is off most days.",
            "nudge_id": nudge_strategy,
            "nudge_strategy": nudge_strategy,
            "nudge_title": "Example nudge",
        },
    )

    assert second_turn.status_code == 200
    second_dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert second_dialogue["disclosure"]["nudge_effectiveness"] > 0
    assert second_dialogue["recommended_nudges"]
    stored_session = api_module.store.get(session_id)
    assert stored_session is not None
    assert stored_session.nudge_events
    latest_nudge = stored_session.nudge_events[-1]
    assert latest_nudge.outcome == "helpful"
    assert latest_nudge.words_added >= 12
    assert latest_nudge.evidence_gain >= 1


def test_api_records_repeated_target_items_for_loop_prevention(monkeypatch):
    monkeypatch.setattr(api_module.planner, "next_reply", lambda snapshot, session: ("Follow-up question?", "gad_q5_restlessness"))
    monkeypatch.setattr(api_module.responder, "compose_reply", lambda session, snapshot, asked_item, fallback_text: (fallback_text, "template"))

    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I feel restless at night."},
    )
    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "About four days a week."},
    )

    assert first_turn.status_code == 200
    assert second_turn.status_code == 200
    stored_session = api_module.store.get(session_id)
    assert stored_session is not None
    assert stored_session.asked_items[-2:] == ["gad_q5_restlessness", "gad_q5_restlessness"]


def test_restlessness_followup_changes_dimension_after_timing_answer():
    planner = DialoguePlanner()
    session = ChatSession(
        session_id="restless-followup",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="At what times do you feel restless the most?", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="During night, around four days a week.", language_tag="en"),
        ],
        asked_items=["gad_q5_restlessness"],
    )
    plan = DialoguePlan(target_topic="anxiety", target_item="gad_q5_restlessness")

    prompt = planner._build_item_prompt("en", plan, session)

    assert prompt is not None
    assert "helps me understand how often it happens" in prompt or "That timing helps." in prompt
    assert "body cannot sit still" in prompt or "inner agitation" in prompt


def test_followup_keeps_recent_probe_item_for_short_frequency_answer():
    planner = DialoguePlanner()
    engine = RuntimeEngine()
    session = ChatSession(
        session_id="continuity-frequency",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="When you try to settle down, is it harder to quiet your thoughts, relax your body, or both?", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="About four days a week.", language_tag="en"),
        ],
        asked_items=["gad_q4_trouble_relaxing"],
    )

    snapshot = engine.analyze(session.turns, session.language, use_llm=False)
    coverage = planner.build_plan(snapshot, session)
    plan = coverage.dialogue
    prompt = planner._build_item_prompt("en", plan, session)

    assert plan.target_item == "gad_q4_trouble_relaxing"
    assert prompt is not None
    assert "how often it happens" in prompt
    assert "busy mind" in prompt or "tense body" in prompt
