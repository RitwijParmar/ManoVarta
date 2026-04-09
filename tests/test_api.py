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
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert "ManoVarta | Multilingual mental health check-in" in response.text
    assert "Begin private check-in" in response.text
    assert "Start talking" in response.text
    assert 'id="profileSheet"' in response.text
    assert 'id="composerToggle"' in response.text
    assert 'id="composerDropbar"' in response.text
    assert 'id="composerQuickOpen"' in response.text
    assert 'id="composerQuickMic"' in response.text
    assert 'id="downloadButton"' not in response.text
    assert 'id="personalizationBlend"' not in response.text
    assert "/app-assets/app.js?v=" in response.text
    assert "/app-assets/app.css?v=" in response.text
    assert "Presenter tools" not in response.text
    assert 'id="backstagePanel"' not in response.text


def test_review_route_serves_hidden_presenter_surface():
    response = client.get("/review")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert 'id="phqTotal"' in response.text
    assert "/app-assets/app.js?v=" in response.text
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
    assert "जब नींद बिगड़ती है" in reply or "ध्यान" in reply or "चिंता" in reply


def test_substantive_first_turn_gets_targeted_followup_not_generic_mix_prompt():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been feeling restless lately and it gets worse during the night."},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"]
    dialogue = turn.json()["snapshot"]["coverage"]["dialogue"]
    assert "mix of those" not in reply.lower()
    assert "settle down" in reply.lower() or "sit still" in reply.lower()
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] in {"gad_q5_restlessness", "gad_q4_trouble_relaxing"}


def test_english_mood_opening_stays_on_mood_not_generic_anxiety():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been feeling low and disconnected from things I usually enjoy."},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"].lower()
    dialogue = turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "mood"
    assert dialogue["target_item"] in {"phq_q1_anhedonia", "phq_q2_low_mood"}
    assert "worry starts" not in reply


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


def test_restlessness_followup_pivots_after_short_timing_answer():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been feeling restless lately and it gets worse during the night."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Mostly during the night."},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"].lower()
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] in {"gad_q5_restlessness", "gad_q4_trouble_relaxing"}
    assert "can you pull your mind away from it" not in reply
    assert "sit still" in reply or "inner agitation" in reply or "pacing" in reply or "busy mind" in reply or "tense body" in reply


def test_restlessness_frequency_answer_stays_on_restlessness_branch_before_worry_control():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been feeling restless lately and it gets worse during the night."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Mostly during the night."},
    )
    assert second_turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "About four days a week."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "gad_q5_restlessness"
    assert "can you pull your mind away from it" not in reply
    assert "sit still" in reply or "inner agitation" in reply or "pacing" in reply


def test_hindi_sleep_followup_acknowledges_timing_answer():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पिछले कुछ दिनों से रात में नींद टूट जाती है और सुबह ध्यान नहीं लगता।"},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "ज़्यादातर रात में।"},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"]
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q3_sleep"
    assert "समय-सूचना मददगार" in reply
    assert "नींद बनाए रखने" in reply or "नींद आने" in reply


def test_hindi_sleep_followup_acknowledges_frequency_answer():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पिछले कुछ दिनों से रात में नींद टूट जाती है और सुबह ध्यान नहीं लगता।"},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "हफ़्ते में चार-पाँच दिन हो जाता है।"},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"]
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q3_sleep"
    assert "यह कितनी बार होता है" in reply
    assert "उन रातों में" in reply
    assert "नींद बनाए रखने" in reply or "नींद शुरू" in reply


def test_english_sleep_pattern_then_frequency_pivots_to_fatigue():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "My sleep has been broken this week."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Mostly I wake up around 3 or 4 am."},
    )
    assert second_turn.status_code == 200
    assert "how many nights a week" in second_turn.json()["assistant_turn"]["text"].lower()

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "About five nights a week."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "energy drops" in reply or "body feels heavy" in reply or "slow to get going" in reply


def test_hindi_sleep_pattern_then_frequency_pivots_to_fatigue():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "कुछ दिनों से नींद बहुत टूट रही है"},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "ज्यादातर रात में बीच में जाग जाता हूँ"},
    )
    assert second_turn.status_code == 200
    assert "कितनी रातों" in second_turn.json()["assistant_turn"]["text"]

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "लगभग पांच दिन हफ्ते में"},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"]
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "ऊर्जा की कमी" in reply or "शरीर भारी" in reply or "दिमाग शुरू होने में धीमा" in reply


def test_hinglish_sleep_pattern_then_frequency_pivots_to_fatigue():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Sleep ka pattern kaafi kharab ho gaya hai."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Raat ko 3 baje ke around aankh khul jaati hai."},
    )
    assert second_turn.status_code == 200
    assert "roughly week mein kitni raaton" in second_turn.json()["assistant_turn"]["text"].lower()

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Week mein 4-5 din aisa ho raha hai."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "low energy" in reply or "body heavy" in reply or "mind ko start hone" in reply


def test_english_energy_followup_acknowledges_frequency_answer():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I feel drained all day and my sleep schedule is messed up."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "About four days a week."},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"]
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "energy"
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "how often it happens" in reply
    assert "body heaviness" in reply or "slow-starting mind" in reply


def test_hindi_heavy_burden_opening_stays_on_mood_not_generic_anxiety():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पिछले दो हफ़्तों से मन बहुत भारी रहता है और कई बार लगता है कि मैं सबके लिए बोझ हूँ।"},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"]
    dialogue = turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "mood"
    assert dialogue["target_item"] in {"phq_q1_anhedonia", "phq_q2_low_mood"}
    assert "चिंता शुरू" not in reply


def test_hindi_mood_followup_pivots_to_focus_or_interest_not_anxiety():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पिछले दो हफ़्तों से मन बहुत भारी रहता है और कई बार लगता है कि मैं सबके लिए बोझ हूँ।"},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "काम पर ध्यान नहीं टिकता और किसी चीज़ में मन नहीं लगता।"},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"]
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] in {"mood", "focus"}
    assert dialogue["target_item"] in {"phq_q1_anhedonia", "phq_q7_concentration"}
    assert "चिंता शुरू" not in reply


def test_hindi_energy_answer_after_focus_pivots_to_fatigue():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "मन बहुत भारी लग रहा है",
        "सुबह में उठने का मन नहीं करता",
        "ध्यान भी ठीक से नहीं लगता",
        "ऊर्जा बहुत कम रहती है",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    reply = body["assistant_turn"]["text"]
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "शरीर भारी" in reply or "ऊर्जा की कमी" in reply


def test_english_low_energy_followup_stays_on_focus_or_energy_live_flow():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Lately I sleep late, feel heavy in the morning, and it is harder to focus at work."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Mostly in the mornings and after lunch. It happens around four days a week."},
    )
    assert second_turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "It feels like low energy plus my mind taking longer to get started."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] in {"focus", "energy"}
    assert dialogue["target_item"] in {"phq_q7_concentration", "phq_q4_fatigue"}
    assert "worry starts" not in reply
    assert "looping even when you try to stop it" not in reply
    assert "techniques" not in reply
    assert "mindfulness" not in reply


def test_english_anxiety_body_tension_pivots_to_relaxation_live_flow():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "My mind keeps worrying even when nothing is wrong and I cannot switch it off at night."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "It loops for hours and I stay tense in my body too."},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"].lower()
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "gad_q4_trouble_relaxing"
    assert "can you pull your mind away from it" not in reply
    assert "relax your body" in reply or "quiet your thoughts" in reply or "tense body" in reply


def test_hinglish_tense_body_followup_does_not_jump_to_generic_fear_item():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Pichhle do hafte se mind bahut overloaded lag raha hai aur raat ko switch off nahi hota."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Phir body bhi tense lagti hai aur neend disturb ho jaati hai."},
    )

    assert second_turn.status_code == 200
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] in {"gad_q4_trouble_relaxing", "phq_q3_sleep"}


def test_hinglish_low_energy_followup_stays_on_focus_or_energy_live_flow():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Lately meri sleep late ho rahi hai, subah heavy feel hota hai, aur kaam par focus karna harder ho gaya hai."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Yeh mostly subah aur lunch ke baad zyada hota hai. Week mein around chaar din hota hai."},
    )
    assert second_turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Lagta low energy bhi hai aur mind ko start hone mein time lagta hai."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] in {"focus", "energy"}
    assert dialogue["target_item"] in {"phq_q7_concentration", "phq_q4_fatigue"}
    assert "worry start hoti hai" not in reply
    assert "loop hoti rehti hai" not in reply


def test_hinglish_low_energy_frequency_answer_stays_on_energy_branch():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Pichhle kuch dino se low energy feel hoti hai aur mind ko start hone mein time lagta hai."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Subah zyada hota hai."},
    )
    assert second_turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Hafte mein 4-5 din."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "energy"
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "kitni baar" in reply or "how often" in reply
    assert "body heavy" in reply or "mind slow start" in reply


def test_hinglish_recent_relaxation_branch_uses_fresh_followup_wording():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Pichhle do hafte se mind bahut overloaded lag raha hai aur raat ko switch off nahi hota."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Mostly jab kaam khatam hota hai tab start hota hai."},
    )
    assert second_turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Phir body bhi tense lagti hai aur neend disturb ho jaati hai."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"]
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "gad_q4_trouble_relaxing"
    assert "body relax karna, ya dono?" not in reply
    assert "tension" in reply.lower()


def test_hindi_anxiety_flow_does_not_loop_generic_question_after_worry_confirmation():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "काफी चिंता का माहौल है",
        "हां लग रहा है खास करके नींद ना आना",
        "दोनों दोनों समस्याएं हैं",
        "सुबह में तो नहीं रहता पर रात में काफी ज्यादा",
        "आप जैसे मेरा दिन अच्छा नहीं रहा तो आज मुझे यह सब काफी ज्यादा लग रहा था",
        "साथ में",
        "करती है आज तो काफी ज्यादा चले",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    reply = body["assistant_turn"]["text"]
    dialogue = body["snapshot"]["coverage"]["dialogue"]

    assert dialogue["target_item"] == "gad_q3_excessive_worry"
    assert "क्या यह ज़्यादा दिमाग की लगातार चिंता जैसा लगता है" not in reply
    assert "काम" in reply or "परिवार" in reply or "भविष्य" in reply


def test_hindi_anxiety_narrative_day_reply_is_not_misread_as_frequency():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "काफी चिंता का माहौल है",
        "हां लग रहा है खास करके नींद ना आना",
        "दोनों दोनों समस्याएं हैं",
        "सुबह में तो नहीं रहता पर रात में काफी ज्यादा",
        "आप जैसे मेरा दिन अच्छा नहीं रहा तो आज मुझे यह सब काफी ज्यादा लग रहा था",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    reply = last.json()["assistant_turn"]["text"]
    assert "यह कितनी बार होता है" not in reply


def test_hindi_recent_anxiety_flow_stops_reopening_after_close_point():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "hi",
            "profile": {
                "recent_checkins": [
                    {"topic": "anxiety", "language": "hi", "safety": "none", "completion": 0.6, "summary": "पिछली बार चिंता पर बात हुई थी।"}
                ]
            },
        },
    )
    session_id = start.json()["session_id"]
    turns = [
        "काफी चिंता का माहौल है",
        "हां लग रहा है खास करके नींद ना आना",
        "दोनों दोनों समस्याएं हैं",
        "सुबह में तो नहीं रहता पर रात में काफी ज्यादा",
        "आप जैसे मेरा दिन अच्छा नहीं रहा तो आज मुझे यह सब काफी ज्यादा लग रहा था",
        "साथ में",
        "करती है आज तो काफी ज्यादा चले",
        "साथ में चलते रहता है",
        "दोनों साथ में लगता है",
        "मैं जैसे यह कल रात में मुझे काफी ज्यादा लग रहा था जब मैं परेशान था काम को लेकर के",
        "रात में लगता है",
        "दोनों साथ में",
    ]

    replies = []
    for text in turns:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200
        replies.append(turn.json()["assistant_turn"]["text"])

    continuity_phrase = "अगर यह आपकी हाल की चिंता बातचीत से मिलता-जुलता लग रहा है"
    assert sum(continuity_phrase in reply for reply in replies) <= 1
    assert replies[-2].startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक") or replies[-2].startswith("मेरे पास अब एक संरचित सार")
    assert replies[-1].startswith("मेरे पास अब एक संरचित सार")
    assert "जब चिंता शुरू होती है" not in replies[-1]


def test_short_hindi_anxiety_scope_answer_closes_instead_of_reopening_old_loop():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "काफी चिंता का माहौल है",
        "हां लग रहा है खास करके नींद ना आना",
        "दोनों दोनों समस्याएं हैं",
        "सुबह में तो नहीं रहता पर रात में काफी ज्यादा",
        "मैं काम को लेकर बहुत सोचता रहता हूँ",
        "कई बातों में फैल जाती है",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    reply = last.json()["assistant_turn"]["text"]
    assert reply.startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक")


def test_hinglish_scope_answer_closes_instead_of_reopening_old_loop():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    script = [
        "Mind bahut overloaded lag raha hai aur raat ko switch off nahi hota.",
        "Body bhi tense lagti hai aur neend disturb ho jaati hai.",
        "Kaam aur future dono ko lekar hota hai.",
        "Kai cheezon mein spread ho jaata hai.",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    reply = last.json()["assistant_turn"]["text"]
    assert reply.startswith("Ab mere paas main pattern hold karne ke liye enough detail hai")


def test_english_scope_answer_closes_instead_of_reopening_old_loop():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    script = [
        "I have been feeling restless and my mind will not switch off at night.",
        "Mostly at night, and it happens about four days a week.",
        "It feels like both my body is tense and my thoughts keep going.",
        "Mostly work and future stuff.",
        "It spreads to other things too.",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    reply = last.json()["assistant_turn"]["text"]
    assert reply.startswith("I have enough to hold onto the main pattern now")


def test_hindi_anxiety_loop_break_closes_after_repeated_generic_rotation():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "काफी चिंता का माहौल है",
        "हां लग रहा है खास करके नींद ना आना",
        "दोनों दोनों समस्याएं हैं",
        "सुबह में तो नहीं रहता पर रात में काफी ज्यादा",
        "आप जैसे मेरा दिन अच्छा नहीं रहा तो आज मुझे यह सब काफी ज्यादा लग रहा था",
        "साथ में",
        "करती है आज तो काफी ज्यादा चले",
        "साथ में चलते रहता है",
        "दोनों साथ में लगता है",
        "मैं जैसे यह कल रात में मुझे काफी ज्यादा लग रहा था जब मैं परेशान था काम को लेकर के",
        "रात में लगता है",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    reply = body["assistant_turn"]["text"]

    assert reply.startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक")
