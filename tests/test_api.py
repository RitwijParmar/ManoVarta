from dataclasses import replace
import io

from fastapi.testclient import TestClient

import manovarta_core.api as api_module
from manovarta_core.dialogue import ANXIETY_LOOP_BREAK_PROMPTS, ANXIETY_LOOP_CLOSE_PROMPTS, FINAL_HOLD_MESSAGES, FINAL_HOLD_VARIANTS, FINAL_REST_MESSAGES, POST_CLOSE_CHOOSER_MESSAGES, POST_CLOSE_IDLE_MESSAGES, DialoguePlanner
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


def test_negated_self_harm_sentence_does_not_trigger_urgent_handoff():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Sleep has been messy and I feel worn out most days."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I would not say I want to hurt myself, but I do feel stuck and useless sometimes."},
    )

    assert turn.status_code == 200
    body = turn.json()
    assert body["snapshot"]["safety"]["level"] != "urgent"
    assert "urgent human review" not in body["assistant_turn"]["text"].lower()


def test_under_the_weather_after_anxiety_history_uses_physical_clarifier():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "My mind keeps looping about work and I cannot switch it off at night."},
    )
    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "It is mostly work and future stuff, and my body stays tense too."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I am feeling a little under the weather today."},
    )

    assert turn.status_code == 200
    body = turn.json()
    assert body["assistant_turn"]["text"] == "When you say you are a little under the weather, does it feel more physical, more emotional, or a mix of both today?"
    assert "worry" not in body["assistant_turn"]["text"].lower()


def test_hindi_summary_request_returns_working_summary_via_chat_flow():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "काफी आलस रहता है और किसी काम में मन नहीं लगता।"},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "अब तक जो समझा है उसका summary बता दो।"},
    )

    assert turn.status_code == 200
    body = turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    assert body["assistant_turn"]["text"].count("?") >= 1
    assert dialogue["stage"] in {"clarification", "exploration"}
    assert dialogue["closure_mode"] is True


def test_hinglish_flat_interest_opener_stays_with_mood_not_anxiety():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Jo cheezein pehle achhi lagti thi unmein start karne se pehle hi mann hat jata hai aur sab flat sa lagta hai."},
    )

    assert turn.status_code == 200
    body = turn.json()
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] == "mood"
    assert body["snapshot"]["coverage"]["dialogue"]["target_item"] in {"phq_q1_anhedonia", "phq_q2_low_mood"}
    assert "worry" not in body["assistant_turn"]["text"].lower()
    assert (
        "mann hat jata hai" in body["assistant_turn"]["text"].lower()
        or "feel very little" in body["assistant_turn"]["text"].lower()
        or "sadness" in body["assistant_turn"]["text"].lower()
        or "heavy" in body["assistant_turn"]["text"].lower()
    )


def test_hindi_sleep_opening_starts_with_real_coverage():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "नींद बिगड़ गई है, देर से नींद आती है और सुबह उठकर शरीर टूटा सा लगता है"},
    )

    body = turn.json()
    assert body["snapshot"]["coverage"]["touched_items"] >= 1
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] == "sleep"


def test_hinglish_negated_panic_opening_prefers_mood_over_anxiety():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Panic jaisa exactly nahi hota, zyada flat aur low lagta hai."},
    )

    body = turn.json()
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] == "mood"
    assert "worry" not in body["assistant_turn"]["text"].lower()


def test_english_negated_panic_with_delay_and_guilt_prefers_mood_or_self_view():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "It's not really panic exactly. More like I delay starting things and then feel guilty."},
    )

    body = turn.json()
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] in {"mood", "self_view"}
    assert "worry" not in body["assistant_turn"]["text"].lower()


def test_explicit_anxious_opening_starts_in_anxiety_not_mood():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Hi I am feeling very anxious today"},
    )

    body = turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    reply = body["assistant_turn"]["text"].lower()
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] in {"gad_q1_nervous", "gad_q2_control_worry", "gad_q4_trouble_relaxing"}
    assert "usually enjoy" not in reply
    assert "interest drop" not in reply


def test_hindi_negated_ghabrahat_with_no_desire_to_start_work_prefers_mood():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "घबराहट जैसा नहीं है, ज़्यादा ऐसा है कि कोई काम शुरू करने का मन नहीं करता।"},
    )

    body = turn.json()
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] == "mood"
    assert "चिंता" not in body["assistant_turn"]["text"]


def test_summary_breadth_request_rotates_away_from_repeated_sleep_functioning_lane():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    script = [
        "Sleep has been delayed and I wake up feeling worn out.",
        "By afternoon I drag through the day and meals get delayed too.",
        "When I sit to work I reread the same lines because focus slips.",
        "What else do you still need to know before you summarize?",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] not in {"sleep", "energy", "focus"}
    assert dialogue["target_scene"] != "sleep_functioning"


def test_hindi_mood_self_view_trace_does_not_repeat_same_compare_prompt():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    turns = [
        "नींद का पैटर्न बदल गया है नींद काफी देर से आती है और काफी कम समय के लिए",
        "यह कुछ दिनों से ऐसा ही है नींद कम आती है किसी काम में मन नहीं लगता है",
        "नींद का पैटर्न बदल गया काफी देर से जाता हूं काम में मन नहीं लगता",
        "मन पहले से ही हट जाता है कोई काम करने की इच्छा करती ही नहीं है",
        "मैं कभी कुछ सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है परंतु जब मैं वर्तमान देखता हूं तो उदासी आती है",
        "उदासी और किसी काम से मन हट जाना",
    ]

    final_turn = None
    for text in turns:
        final_turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})

    assert final_turn is not None
    assert final_turn.status_code == 200
    body = final_turn.json()
    reply = body["assistant_turn"]["text"]
    assert "ज़्यादातर दिनों में यह ज़्यादा उदास मन जैसा लगता है" not in reply
    assert "पहले जो चीज़ें अच्छी लगती थीं उनमें दिल कम लगता है" not in reply
    assert (
        "ऊर्जा की कमी" in reply
        or "शरीर भारी" in reply
        or "दिमाग शुरू" in reply
        or "ध्यान" in reply
        or "भूख" in reply
        or "शुरू होने की ताकत" in reply
        or "रफ्तार" in reply
    )
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] in {"energy", "focus"}


def test_hindi_sleep_then_mood_trace_does_not_repeat_generic_sleep_topic_prompt():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "नींद का पैटर्न बदल गया है नींद काफी देर से आती है और काफी कम समय के लिए"},
    )
    second = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "यह कुछ दिनों से ऐसा ही है नींद कम आती है किसी काम में मन नहीं लगता है"},
    )
    third = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "नींद का पैटर्न बदल गया काफी देर से जाता हूं काम में मन नहीं लगता"},
    )

    assert second.status_code == 200
    assert third.status_code == 200
    generic_sleep_topic = "नींद में ज़्यादा दिक्कत सोने की शुरुआत में है, बीच-बीच में उठने में, या ज़रूरत से ज़्यादा नींद आ रही है?"
    assert second.json()["assistant_turn"]["text"] != generic_sleep_topic
    assert third.json()["assistant_turn"]["text"] != generic_sleep_topic
    assert third.json()["snapshot"]["coverage"]["dialogue"]["target_topic"] in {"mood", "energy", "focus"}


def test_english_sleep_followup_yields_to_daytime_functioning_signal():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Sleep has been delayed and I wake up tired most mornings."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Even when I finally sleep, I still drag through the day and skip meals sometimes."},
    )

    assert turn.status_code == 200
    body = turn.json()
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] == "energy"
    assert body["snapshot"]["coverage"]["dialogue"]["target_item"] in {None, "phq_q4_fatigue", "phq_q5_appetite"}
    assert "fall asleep" not in body["assistant_turn"]["text"].lower()
    assert "waking during the night" not in body["assistant_turn"]["text"].lower()


def test_hinglish_sleep_followup_yields_to_daytime_functioning_signal():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Sleep late aati hai aur subah uthkar bhi body heavy lagti hai."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Din bhar energy low rehti hai and meals bhi slip ho jaate hain."},
    )

    assert turn.status_code == 200
    body = turn.json()
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] == "energy"
    assert body["snapshot"]["coverage"]["dialogue"]["target_item"] in {None, "phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration"}
    reply = body["assistant_turn"]["text"].lower()
    assert "sleep start hone" not in reply
    assert "sleep banaye rakhne" not in reply


def test_hinglish_low_energy_downplay_keeps_mixed_trace_out_of_early_anxiety():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Pichhle do hafte se sleep late aati hai aur next day body heavy lagti hai."},
    )
    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Kaam start karne se pehle hi mann hat jata hai aur focus toot jata hai."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Kabhi kabhi future ko lekar worry bhi loop karti hai but zyada low energy jaisa lagta hai."},
    )

    assert turn.status_code == 200
    body = turn.json()
    assert body["snapshot"]["coverage"]["dialogue"]["target_topic"] in {"energy", "focus", "mood"}
    assert "quiet karna" not in body["assistant_turn"]["text"].lower()


def test_hindi_repeat_anhedonia_trace_advances_to_self_view_not_same_low_mood_probe():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    turns = [
        "नीम का पैटर्न बदल गया है नींद काफी देर से आती है और काफी कम समय के लिए",
        "यह कुछ दिनों से ऐसा ही है नींद कम आती है किसी काम में मन नहीं लगता है",
        "नींद का पैटर्न बदल गया काफी देर से जाता हूं काम में मन नहीं लगता",
        "मां पहले से ही है जाता है कोई काम करने की इच्छा करती ही नहीं है",
    ]

    final_turn = None
    for text in turns:
        final_turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})

    assert final_turn is not None
    assert final_turn.status_code == 200
    body = final_turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    reply = body["assistant_turn"]["text"]
    assert dialogue["target_topic"] in {"mood", "self_view"}
    assert dialogue["target_scene"] == "mood_selfview"
    assert dialogue["target_item"] == "phq_q6_worthlessness"
    assert "दिन भर का लगातार भारी मन" not in reply
    assert ("अपने बारे में" in reply) or ("खुद" in reply) or ("बोझ" in reply)


def test_recent_anxiety_history_does_not_anchor_new_opening_or_first_probe():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "en",
            "profile": {
                "recent_checkins": [
                    {"topic": "anxiety", "language": "en", "summary": "Recent anxiety check-in."}
                ]
            },
        },
    )

    assert start.status_code == 200
    opening = start.json()["assistant_turn"]["text"].lower()
    assert "anxiety" not in opening
    assert "check-in" not in opening

    session_id = start.json()["session_id"]
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been feeling flat and low through most days lately."},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"].lower()
    assert "recent anxiety" not in reply
    assert "check-in" not in reply


def test_review_route_serves_hidden_presenter_surface():
    response = client.get("/review")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert 'id="phqTotal"' in response.text
    assert "/app-assets/app.js?v=" in response.text
    assert "Presenter tools" in response.text
    assert "Hidden details for demos, evaluation, and care-team review" in response.text


def test_runtime_config_reports_component_providers_and_async_support():
    response = client.get("/runtime/config")

    assert response.status_code == 200
    body = response.json()
    assert "provider" in body
    assert "chat_provider" in body
    assert "extraction_provider" in body
    assert "safety_provider" in body
    assert "controller_model" in body
    assert "extractor_model" in body
    assert "chat_fallback_model" in body
    assert "live_chat_analysis_model" in body
    assert "vertex_chat_location" in body
    assert "huggingface_enabled" in body
    assert "self_hosted_inference_enabled" in body
    assert "vertex_enabled" in body
    assert "remote_extraction_enabled" in body
    assert "remote_extraction_url_configured" in body
    assert "async_scoring_enabled" in body
    assert "async_scoring_dir" in body


def test_add_turn_skips_prior_analysis_without_nudge(monkeypatch):
    call_count = 0
    original_analyze = api_module.engine.analyze

    def wrapped_analyze(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_analyze(*args, **kwargs)

    monkeypatch.setattr(api_module.engine, "analyze", wrapped_analyze)

    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I feel tired and my sleep has been bad lately."},
    )

    assert turn.status_code == 200
    assert call_count == 1


def test_add_turn_returns_recovery_reply_when_planner_raises(monkeypatch):
    original_next_reply = api_module.planner.next_reply

    def broken_next_reply(*args, **kwargs):
        raise RuntimeError("planner exploded")

    monkeypatch.setattr(api_module.planner, "next_reply", broken_next_reply)

    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Sleep has been broken and I feel flat most days."},
    )

    monkeypatch.setattr(api_module.planner, "next_reply", original_next_reply)

    assert turn.status_code == 200
    body = turn.json()
    assert body["assistant_turn"]["text"] == api_module.TURN_RECOVERY_MESSAGES["en"]
    assert body["assistant_turn"]["notes"] == "source:recovery"


def test_add_turn_returns_200_when_summary_builder_raises(monkeypatch):
    original_build_summary = api_module.build_summary

    def broken_build_summary(*args, **kwargs):
        raise RuntimeError("summary exploded")

    monkeypatch.setattr(api_module, "build_summary", broken_build_summary)

    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Sleep has been broken and I feel worn out through most days."},
    )

    monkeypatch.setattr(api_module, "build_summary", original_build_summary)

    assert turn.status_code == 200
    body = turn.json()
    assert body["summary"] == api_module.SUMMARY_RECOVERY_MESSAGES["en"]


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


def test_session_async_score_enqueues_existing_session(tmp_path, monkeypatch):
    monkeypatch.setattr(api_module, "runtime_config", replace(api_module.runtime_config, async_scoring_enabled=True, async_scoring_dir=str(tmp_path)))
    monkeypatch.setattr(api_module, "async_scoring_store", api_module.AsyncScoringStore(tmp_path))

    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]
    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been exhausted and my sleep keeps breaking."},
    )

    response = client.post(f"/chat/sessions/{session_id}/score_async")

    assert response.status_code == 200
    body = response.json()
    assert body["job"]["status"] == "pending"
    assert body["job"]["session_id"] == session_id


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
    assert any(key in dialogue["recommended_nudges"] for key in {"choice", "example", "scale"})
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


def test_under_the_weather_opening_stays_off_recent_anxiety_continuity_and_returns_neutral_clarifier():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "en",
            "profile": {
                "recent_checkins": [
                    {"topic": "anxiety", "language": "en", "safety": "none", "completion": 0.7, "summary": "Recent anxiety check-in."}
                ]
            },
        },
    )
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I am feeling a little under the weather today."},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"].lower()
    dialogue = turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "mood"
    assert dialogue["continuity_note"] == ""
    assert "recent anxiety check-in" not in reply
    assert "worry" not in reply
    assert "physical" in reply and "emotional" in reply


def test_under_the_weather_with_duplicate_word_still_uses_physical_clarifier():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "en",
            "profile": {
                "recent_checkins": [
                    {"topic": "anxiety", "language": "en", "safety": "none", "completion": 0.7, "summary": "Recent anxiety check-in."}
                ]
            },
        },
    )
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "hi I'm feeling a little under the weather weather today"},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"].lower()
    assert "physical" in reply and "emotional" in reply
    assert "recent anxiety check-in" not in reply
    assert "worry" not in reply


def test_keyboard_near_duplicate_retry_reuses_last_assistant_turn():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I am feeling a little under the weather today."},
    )
    second = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I am feeling a little under the weather weather today."},
    )
    exported = client.get(f"/chat/sessions/{session_id}/export")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["assistant_turn"]["text"] == first.json()["assistant_turn"]["text"]
    turns = exported.json()["turns"]
    assert len(turns) == 3


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


def test_remote_live_llm_waits_for_later_turns(monkeypatch):
    config = replace(
        api_module.runtime_config,
        live_chat_llm_analysis_enabled=True,
        live_llm_turn_threshold=1,
        extraction_provider="remote",
    )
    monkeypatch.setattr(api_module, "runtime_config", config)

    session = ChatSession(
        session_id="remote-llm-early",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="Opening", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="Sleep is off.", language_tag="en"),
            Turn(turn_id=3, speaker="assistant", text="Follow-up", language_tag="en"),
            Turn(turn_id=4, speaker="user", text="I feel tired in the afternoon.", language_tag="en"),
        ],
    )

    assert api_module._should_use_live_llm(session) is False


def test_remote_live_llm_samples_periodically_after_threshold(monkeypatch):
    config = replace(
        api_module.runtime_config,
        live_chat_llm_analysis_enabled=True,
        live_llm_turn_threshold=1,
        extraction_provider="remote",
    )
    monkeypatch.setattr(api_module, "runtime_config", config)

    session = ChatSession(
        session_id="remote-llm-later",
        language="en",
        turns=[
            Turn(turn_id=1, speaker="assistant", text="Opening", language_tag="en"),
            Turn(turn_id=2, speaker="user", text="Sleep is patchy.", language_tag="en"),
            Turn(turn_id=3, speaker="assistant", text="Follow-up", language_tag="en"),
            Turn(turn_id=4, speaker="user", text="Low energy too.", language_tag="en"),
            Turn(turn_id=5, speaker="assistant", text="Follow-up", language_tag="en"),
            Turn(turn_id=6, speaker="user", text="Meals get delayed.", language_tag="en"),
            Turn(turn_id=7, speaker="assistant", text="Follow-up", language_tag="en"),
            Turn(turn_id=8, speaker="user", text="Concentration drops later in the day.", language_tag="en"),
        ],
    )

    assert api_module._should_use_live_llm(session) is True

    session.turns.append(Turn(turn_id=9, speaker="assistant", text="Follow-up", language_tag="en"))
    session.turns.append(Turn(turn_id=10, speaker="user", text="Body feels heavy by afternoon.", language_tag="en"))

    assert api_module._should_use_live_llm(session) is False

    session.turns.append(Turn(turn_id=11, speaker="assistant", text="Follow-up", language_tag="en"))
    session.turns.append(Turn(turn_id=12, speaker="user", text="My appetite is off too.", language_tag="en"))

    assert api_module._should_use_live_llm(session) is False

    session.turns.append(Turn(turn_id=13, speaker="assistant", text="Follow-up", language_tag="en"))
    session.turns.append(Turn(turn_id=14, speaker="user", text="It takes longer to get going most mornings.", language_tag="en"))

    assert api_module._should_use_live_llm(session) is True


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


def test_english_sleep_followup_acknowledges_frequency_answer():
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
    assert dialogue["target_topic"] == "sleep"
    assert dialogue["target_item"] == "phq_q3_sleep"
    assert "how often it happens" in reply
    assert "hard to start" in reply or "hard to stay in" in reply or "wake up too early" in reply


def test_soft_disappearance_language_triggers_first_turn_safety_check_in_english():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been feeling low and sometimes I wish I could disappear for a while."},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"]
    snapshot = turn.json()["snapshot"]
    dialogue = snapshot["coverage"]["dialogue"]
    assert snapshot["safety"]["level"] == "review"
    assert dialogue["target_topic"] == "safety"
    assert dialogue["target_item"] == "phq_q9_self_harm"
    assert "safety matters" in reply


def test_soft_disappearance_language_triggers_first_turn_safety_check_in_hindi():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "कभी कभी लगता है काश मैं कुछ समय के लिए गायब हो जाऊँ।"},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"]
    snapshot = turn.json()["snapshot"]
    dialogue = snapshot["coverage"]["dialogue"]
    assert snapshot["safety"]["level"] == "review"
    assert dialogue["target_topic"] == "safety"
    assert dialogue["target_item"] == "phq_q9_self_harm"
    assert "सुरक्षा" in reply or "नुकसान" in reply


def test_hindi_heavy_burden_opening_moves_to_self_view_not_generic_anxiety():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पिछले दो हफ़्तों से मन बहुत भारी रहता है और कई बार लगता है कि मैं सबके लिए बोझ हूँ।"},
    )

    assert turn.status_code == 200
    reply = turn.json()["assistant_turn"]["text"]
    dialogue = turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "self_view"
    assert dialogue["target_item"] == "phq_q6_worthlessness"
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


def test_hindi_sleep_choice_after_anxiety_chooser_pivots_to_sleep():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "थोड़ी चिंता लग रही है"},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "हां यह नींद की दिक्कत लग रही है"},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"]
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "sleep"
    assert dialogue["target_item"] == "phq_q3_sleep"
    assert "नींद" in reply
    assert "दिमाग को शांत" not in reply


def test_hindi_sleep_followup_relax_answer_bridges_back_to_anxiety():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    for text in [
        "थोड़ी चिंता लग रही है",
        "हां यह नींद की दिक्कत लग रही है",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "दिमाग को शांत करना"},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"]
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] == "gad_q4_trouble_relaxing"
    assert "दिमाग और शरीर" in reply or "तनाव" in reply or "शांत" in reply


def test_english_sleep_followup_relax_answer_bridges_back_to_anxiety():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I feel a little anxious.",
        "Yeah, it feels more like a sleep problem.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Quieting my mind."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] == "gad_q4_trouble_relaxing"
    assert "quiet your thoughts" in reply or "relax your body" in reply or "both" in reply
    assert "fall asleep" not in reply


def test_hinglish_sleep_followup_relax_answer_bridges_back_to_anxiety():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    for text in [
        "Thodi anxiety lag rahi hai.",
        "Haan yeh sleep issue jaisa lag raha hai.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Mind ko quiet karna."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] == "gad_q4_trouble_relaxing"
    assert "thoughts ko quiet" in reply or "body relax" in reply or "dono" in reply
    assert "sleep disturb" not in reply


def test_hinglish_worry_domain_detail_advances_to_scope_question():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    script = [
        "Mind overloaded rehta hai aur raat ko switch off nahi hota.",
        "Week mein 4-5 din zyada hota hai.",
        "Body tense bhi rehti hai aur thoughts bhi chalte rehte hain.",
        "Mostly work aur future ko lekar hota hai.",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})

    assert last is not None and last.status_code == 200
    reply = last.json()["assistant_turn"]["text"]
    dialogue = last.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "gad_q3_excessive_worry"
    assert "spread" in reply.lower() or "main baat" in reply.lower()


def test_anhedonia_semantic_answer_advances_to_low_mood_instead_of_repeating():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I have been feeling numb and disconnected lately."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Things I used to enjoy feel flat, and even when I do them I mostly go through the motions now."},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"]
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q2_low_mood"
    assert "interest drop before you start" not in reply


def test_anhedonia_followup_does_not_bounce_back_after_low_mood_probe():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I have been feeling numb and disconnected lately.",
        "Things I used to enjoy feel flat.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Even when I do them, I do not get much from them and I mostly go through the motions now."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"]
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q2_low_mood"
    assert "interest drop before you start" not in reply
    assert (
        "steady heavy mood" in reply.lower()
        or "emotional numbness" in reply.lower()
        or "going through the motions" in reply.lower()
        or "emotionally flat underneath" in reply.lower()
    )


def test_hinglish_flat_answer_advances_off_repeated_anhedonia_probe():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    first_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Kaafi time se low aur disconnected feel ho raha hai."},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Jo cheezein pehle achhi lagti thi ab flat lagti hain."},
    )

    assert second_turn.status_code == 200
    reply = second_turn.json()["assistant_turn"]["text"].lower()
    dialogue = second_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q2_low_mood"
    assert "mann hat jata hai" not in reply


def test_split_turn_anhedonia_detail_still_stays_off_the_old_repeat_probe():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I have been feeling numb and disconnected lately.",
        "Things I used to enjoy feel flat.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Even when I do them, I do not get much from them."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"]
    dialogue = third_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q2_low_mood"
    assert "interest drop before you start" not in reply

    fourth_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I mostly go through the motions now."},
    )

    assert fourth_turn.status_code == 200
    reply = fourth_turn.json()["assistant_turn"]["text"]
    dialogue = fourth_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q2_low_mood"
    assert "steady heavy mood" not in reply.lower()
    assert "small moments still cut through" in reply.lower() or "going through the motions" in reply.lower()


def test_hindi_flat_functioning_answer_uses_functional_impact_prompt():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    for text in [
        "पिछले कुछ समय से मन बहुत भारी और कटा-कटा लगता है।",
        "जो चीज़ें पहले अच्छी लगती थीं अब उनमें मन नहीं लगता।",
        "कर भी लेता हूँ तो बहुत कम महसूस होता है।",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    fourth_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "ज़्यादातर बस काम निपटाता रहता हूँ।"},
    )

    assert fourth_turn.status_code == 200
    reply = fourth_turn.json()["assistant_turn"]["text"]
    dialogue = fourth_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q2_low_mood"
    assert "साधारण काम भी भारी" in reply or "बाहर से काम करते रहते हैं" in reply
    assert "उन कामों की तरफ़ जाते हैं" not in reply


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


def test_english_under_weather_energy_then_appetite_moves_on_to_next_scene():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    script = [
        "I am feeling a little under the weather today.",
        "Mostly physically off, tired, and slower than usual.",
        "Sleep has been patchy and by afternoon I feel heavy and drag through the day.",
        "Meals get delayed too and I lose track of hunger cues.",
        "It is harder to focus on one thing once the afternoon hits.",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    assert last is not None
    body = last.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    reply = body["assistant_turn"]["text"].lower()
    assert dialogue["target_item"] in {"phq_q7_concentration", "phq_q8_psychomotor", "phq_q2_low_mood"}
    assert "changes in appetite" not in reply
    assert "low energy through the day" not in reply


def test_hinglish_low_energy_with_negated_panic_does_not_jump_to_anxiety():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    script = [
        "Sleep thodi messy ho gayi hai aur low energy rehti hai.",
        "Afternoon tak body heavy lagti hai aur routine slip ho jata hai.",
        "Meals bhi delay ho jate hain aur kaam start karna hard lagta hai.",
        "Mind slow start hota hai but panic jaisa nahi hota.",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    assert last is not None
    body = last.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    reply = body["assistant_turn"]["text"].lower()
    assert dialogue["target_topic"] in {"focus", "energy", "mood"}
    assert dialogue["target_item"] != "gad_q2_control_worry"
    assert "worry" not in reply


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


def test_english_anxiety_work_future_detail_gets_contextual_relaxation_bridge():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I do not know what exactly is wrong.",
        "It keeps going even when I try hard to stop it.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Lately when I start any work I get more anxious about the future."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    assert "work or future worry gets going" in reply
    assert "whichever part feels easier to answer is okay" not in reply


def test_english_long_anxiety_flow_breaks_earlier_and_holds_after_close():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    scripted_turns = [
        "I do not know what exactly is wrong.",
        "It keeps going even when I try hard to stop it.",
        "Lately when I start any work I get more anxious about the future.",
        "It keeps going no matter how much I try.",
        "Mostly it keeps flipping around one same thing and other things disappear.",
        "No not like that.",
    ]

    responses = []
    for text in scripted_turns:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200
        responses.append(turn.json())

    assert responses[3]["assistant_turn"]["text"] == ANXIETY_LOOP_BREAK_PROMPTS["en"]
    assert responses[4]["assistant_turn"]["text"] == ANXIETY_LOOP_CLOSE_PROMPTS["en"]
    assert responses[5]["assistant_turn"]["text"] == POST_CLOSE_CHOOSER_MESSAGES["en"]


def test_hinglish_long_anxiety_flow_breaks_earlier_and_holds_after_close():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    scripted_turns = [
        "Pata nahi kya ho raha hai exactly.",
        "Woh chalta rehta hai chahe kitni bhi koshish karu.",
        "Jab main kaam start karta hoon tab future ko lekar zyada tension hoti hai.",
        "Chalta rehta hai kitni bhi koshish kar lo.",
        "Mostly ek hi baat repeat hoti rehti hai aur baaki sab side ho jata hai.",
        "Nahi aisa kuch nahi.",
    ]

    responses = []
    for text in scripted_turns:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200
        responses.append(turn.json())

    assert responses[3]["assistant_turn"]["text"] == ANXIETY_LOOP_BREAK_PROMPTS["hinglish"]
    assert responses[4]["assistant_turn"]["text"] == ANXIETY_LOOP_CLOSE_PROMPTS["hinglish"]
    assert responses[5]["assistant_turn"]["text"] == POST_CLOSE_CHOOSER_MESSAGES["hinglish"]


def test_hinglish_anxiety_work_future_detail_gets_contextual_relaxation_bridge():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    for text in [
        "Pata nahi exactly kya wrong hai.",
        "Woh chalta rehta hai chahe kitni koshish karun.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Kaam start karte hi future ko lekar anxiety badh jaati hai."},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"].lower()
    assert "work ya future wali worry pakad leti hai" in reply
    assert "jo part answer karna easier lage" not in reply


def test_hinglish_flat_workday_detail_stays_on_mood_or_focus_instead_of_drifting_to_anxiety():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    for text in [
        "Kaafi time se low aur disconnected feel ho raha hai.",
        "Jo cheezein pehle achhi lagti thi ab flat lagti hain.",
        "Kar bhi leta hoon but unse kuch feel nahi hota.",
        "Mostly bas motions mein chalta rehta hoon.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    fifth_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Work days par aur flat lagta hai."},
    )

    assert fifth_turn.status_code == 200
    reply = fifth_turn.json()["assistant_turn"]["text"].lower()
    dialogue = fifth_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] in {"mood", "focus"}
    assert dialogue["target_item"] in {"phq_q2_low_mood", "phq_q7_concentration"}
    assert "worry" not in reply


def test_hindi_anxiety_work_future_detail_gets_contextual_relaxation_bridge():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    for text in [
        "पता नहीं क्या असर पड़ता है।",
        "वह चलती रहती है कितना भी प्रयास करो।",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    third_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "फिलहाल जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर।"},
    )

    assert third_turn.status_code == 200
    reply = third_turn.json()["assistant_turn"]["text"]
    assert "काम या भविष्य की चिंता पकड़ लेती है" in reply
    assert "एक हाल का उदाहरण" not in reply


def test_post_close_vague_followup_uses_chooser_in_api_flow():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I do not know what exactly is wrong.",
        "It keeps going even when I try hard to stop it.",
        "Lately when I start any work I get more anxious about the future.",
        "It keeps going no matter how much I try.",
        "Mostly it keeps flipping around one same thing and other things disappear.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    followup = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "No not like that."},
    )

    assert followup.status_code == 200
    assert followup.json()["assistant_turn"]["text"] == POST_CLOSE_CHOOSER_MESSAGES["en"]


def test_low_mood_functional_impact_detail_advances_to_focus_instead_of_repeating():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I have been feeling low and disconnected lately.",
        "Things I used to enjoy feel flat.",
        "Even when I do them, I do not get much from them.",
        "I mostly go through the motions now.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    fifth_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "It is worse on work days and I still get through things but it feels flat."},
    )

    assert fifth_turn.status_code == 200
    reply = fifth_turn.json()["assistant_turn"]["text"].lower()
    dialogue = fifth_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q7_concentration"
    assert "attention slips away" in reply or "coming back to the same line" in reply
    assert "small moments still cut through" not in reply


def test_direct_focus_answer_advances_to_energy_instead_of_repeating_concentration_probe():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I have been feeling low and disconnected lately.",
        "Things I used to enjoy feel flat.",
        "Even when I do them, I do not get much from them.",
        "I mostly go through the motions now.",
        "It is worse on work days and I still get through things but it feels flat.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    sixth_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Then my focus slips and I end up rereading things."},
    )

    assert sixth_turn.status_code == 200
    reply = sixth_turn.json()["assistant_turn"]["text"].lower()
    dialogue = sixth_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "energy drops" in reply or "body feels heavy" in reply
    assert "attention slips away" not in reply


def test_english_day_end_energy_answer_stays_on_fatigue_with_timing_wording():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    for text in [
        "I have been feeling low and disconnected lately.",
        "Things I used to enjoy feel flat.",
        "Even when I do them, I do not get much from them.",
        "I mostly go through the motions now.",
        "It is worse on work days and I still get through things but it feels flat.",
        "Then my focus slips and I end up rereading things.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    seventh_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "By the end of the day I feel drained too."},
    )

    assert seventh_turn.status_code == 200
    reply = seventh_turn.json()["assistant_turn"]["text"].lower()
    dialogue = seventh_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "energy"
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "that timing helps" in reply
    assert "slow-starting mind" in reply or "body heaviness" in reply


def test_hindi_direct_focus_answer_advances_to_energy_instead_of_repeating_concentration_probe():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    for text in [
        "पिछले कुछ समय से मन बहुत भारी और कटा-कटा लगता है।",
        "जो चीज़ें पहले अच्छी लगती थीं अब उनमें मन नहीं लगता।",
        "कर भी लेता हूँ तो बहुत कम महसूस होता है।",
        "ज़्यादातर बस काम निपटाता रहता हूँ।",
        "काम वाले दिनों में यह और सपाट लगता है।",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    sixth_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "फिर ध्यान भी बार-बार टूटता है।"},
    )

    assert sixth_turn.status_code == 200
    reply = sixth_turn.json()["assistant_turn"]["text"]
    dialogue = sixth_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "energy"
    assert dialogue["target_item"] == "phq_q4_fatigue"
    assert "ऊर्जा" in reply or "थकान" in reply or "शरीर भारी" in reply
    assert "ध्यान बार-बार भटक" not in reply


def test_hinglish_day_end_energy_answer_stays_on_energy_in_long_mood_flow():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    for text in [
        "Kaafi time se low aur disconnected feel ho raha hai.",
        "Jo cheezein pehle achhi lagti thi ab flat lagti hain.",
        "Kar bhi leta hoon but unse kuch feel nahi hota.",
        "Mostly bas motions mein chalta rehta hoon.",
        "Work days par aur flat lagta hai.",
        "Phir focus toot jata hai aur same cheez dobara padhna padta hai.",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    seventh_turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Din ke end tak energy bhi down ho jaati hai."},
    )

    assert seventh_turn.status_code == 200
    reply = seventh_turn.json()["assistant_turn"]["text"].lower()
    dialogue = seventh_turn.json()["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "energy"
    assert dialogue["target_item"] in {"phq_q4_fatigue", "phq_q8_psychomotor"}
    assert (
        "start lene ki energy" in reply
        or "body heavy" in reply
        or "pace ka noticeably slow" in reply
        or "din ke end" in reply
    )
    assert "flat ya heavy feeling" not in reply


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
    assert replies[-2].startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक") or replies[-2].startswith("ठीक है। अभी") or replies[-2].startswith("मैं थोड़ा रुककर")
    assert (
        replies[-1].startswith("ठीक है। अभी")
        or replies[-1].startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक")
        or replies[-1].startswith("अगर आप चाहें")
        or replies[-1] == POST_CLOSE_IDLE_MESSAGES["hi"]
    )
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


def test_hindi_anxiety_domain_detail_does_not_reopen_control_worry_immediately():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "पता नहीं क्या असर पड़ता है",
        "वह चलाते रहती है कितना भी प्रयास करो",
        "हम फिलहाल में जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    reply = body["assistant_turn"]["text"]
    dialogue = body["snapshot"]["coverage"]["dialogue"]

    assert dialogue["target_item"] == "gad_q4_trouble_relaxing"
    assert "जब चिंता शुरू होती है" not in reply
    assert "दिमाग को शांत" in reply or "शरीर को ढीला" in reply or "दोनों" in reply


def test_hindi_garbled_scope_reply_does_not_false_trigger_safety_question():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "पता नहीं क्या असर पड़ता है",
        "वह चलाते रहती है कितना भी प्रयास करो",
        "हम फिलहाल में जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर",
        "चलती रहती है कितना भी कोशिश करो",
        "नहीं ज्यादातर यह एक ही बात पलट की रहती है बाकी चीजों का ध्यान नहीं आता",
        "हां अपमान को यही चल रहा है",
        "नहीं दिमाग को शांत करना शरीर को ढीला करना कोई बड़ी बात नहीं है",
        "लंबे समय तक 18 रहता है",
        "चलती रहती है",
        "कमर्शियल मिल जा रही हो तक रहती है",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    reply = body["assistant_turn"]["text"]
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    safety = body["snapshot"]["safety"]["level"]

    assert safety == "none"
    assert dialogue["target_topic"] != "safety"
    assert "खुद को नुकसान" not in reply
    assert "ज़िंदा न रहने" not in reply


def test_hindi_relax_duration_answer_closes_instead_of_reopening_old_anxiety_items():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "पता नहीं क्या असर पड़ता है",
        "वह चलाते रहती है कितना भी प्रयास करो",
        "हम फिलहाल में जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर",
        "चलती रहती है कितना भी कोशिश करो",
        "नहीं ज्यादातर यह एक ही बात पलट की रहती है बाकी चीजों का ध्यान नहीं आता",
        "हां अपमान को यही चल रहा है",
        "नहीं दिमाग को शांत करना शरीर को ढीला करना कोई बड़ी बात नहीं है",
        "लंबे समय तक 18 रहता है",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    reply = body["assistant_turn"]["text"]

    assert reply in FINAL_HOLD_VARIANTS["hi"]
    assert "जब चिंता शुरू होती है" not in reply


def test_hindi_relax_duration_answer_uses_break_prompt_before_old_loop_reopens():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "पता नहीं क्या असर पड़ता है",
        "वह चलाते रहती है कितना भी प्रयास करो",
        "हम फिलहाल में जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर",
        "चलती रहती है कितना भी कोशिश करो",
        "नहीं ज्यादातर यह एक ही बात पलट की रहती है बाकी चीजों का ध्यान नहीं आता",
        "हां अपमान को यही चल रहा है",
        "नहीं दिमाग को शांत करना शरीर को ढीला करना कोई बड़ी बात नहीं है",
        "लंबे समय तक 18 रहता है",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    reply = last.json()["assistant_turn"]["text"]
    assert reply in FINAL_HOLD_VARIANTS["hi"]
    assert "जब चिंता शुरू होती है" not in reply


def test_hindi_post_close_echo_does_not_cycle_hold_variants():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    for text in [
        "पता नहीं क्या असर पड़ता है",
        "वह चलती रहती है कितना भी प्रयास करो",
        "फिलहाल जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर",
        "चलती रहती है कितना भी कोशिश करो",
        "नहीं ज्यादातर यह एक ही बात पर अटकी रहती है",
    ]:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200

    echoed_summary = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "अब मेरे पास मुख्य पैटर्न पकड़ने लायक काफी जानकारी है यह चिंता कुछ खास समय पर बढ़ती है और तनाव वाले दिनों में ज्यादा लग सकती है अगर कोई बहुत जरूरी बात बाकी ना हो तो मैं इसे अभी कामचलाऊ सार मान सकता हूं"},
    )
    assert echoed_summary.status_code == 200
    assert echoed_summary.json()["assistant_turn"]["text"] == FINAL_REST_MESSAGES["hi"]

    echoed_hold = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "ठीक है अभी के लिए मैं इसे वर्तमान सार मानकर रखता हूं अगर बाद में कोई एक जरूरी बात छूटी लगे तो आप उसे सीधे बता सकते हैं"},
    )
    assert echoed_hold.status_code == 200
    assert echoed_hold.json()["assistant_turn"]["text"] in {FINAL_REST_MESSAGES["hi"], POST_CLOSE_IDLE_MESSAGES["hi"]}


def test_hindi_break_prompt_family_scoped_answer_closes_instead_of_reopening():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "पता नहीं क्या असर पड़ता है",
        "वह चलाते रहती है कितना भी प्रयास करो",
        "हम फिलहाल में जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर",
        "चलती रहती है कितना भी कोशिश करो",
        "नहीं ज्यादातर यह एक ही बात पलट की रहती है बाकी चीजों का ध्यान नहीं आता",
        "हां अपमान को यही चल रहा है",
        "नहीं दिमाग को शांत करना शरीर को ढीला करना कोई बड़ी बात नहीं है",
        "लंबे समय तक 18 रहता है",
        "चलती रहती है",
        "कमर्शियल मिल जा रही हो तक रहती है",
        "नहीं ऐसा कुछ नहीं आता है",
        "कभी नहीं आते हैं",
        "केवल मां की है शरीर से कोई लेना-देना नहीं",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    reply = last.json()["assistant_turn"]["text"]
    assert reply in FINAL_HOLD_VARIANTS["hi"]
    assert "जब आप खुद को शांत" not in reply
    assert "जब चिंता शुरू" not in reply


def test_hindi_close_prompt_followed_by_garbled_detail_stays_on_hold():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "पता नहीं क्या असर पड़ता है",
        "वह चलाते रहती है कितना भी प्रयास करो",
        "हम फिलहाल में जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर",
        "चलती रहती है कितना भी कोशिश करो",
        "नहीं ज्यादातर यह एक ही बात पलट की रहती है बाकी चीजों का ध्यान नहीं आता",
        "हां अपमान को यही चल रहा है",
        "नहीं दिमाग को शांत करना शरीर को ढीला करना कोई बड़ी बात नहीं है",
        "लंबे समय तक 18 रहता है",
        "चलती रहती है",
        "कमर्शियल मिल जा रही हो तक रहती है",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    reply = last.json()["assistant_turn"]["text"]
    assert reply in FINAL_HOLD_VARIANTS["hi"]
    assert "जब चिंता शुरू होती है" not in reply


def test_duplicate_voice_retry_reuses_previous_assistant_turn_instead_of_stacking_replies():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    first = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "नींद काफी देर से आती है और किसी काम में मन नहीं लगता है।", "from_voice": True},
    )
    second = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "नींद देर से आती है और किसी काम में मन नहीं लगता है।", "from_voice": True},
    )
    detail = client.get(f"/chat/sessions/{session_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["assistant_turn"]["turn_id"] == first.json()["assistant_turn"]["turn_id"]
    assert len(detail.json()["turns"]) == 3


def test_typed_paraphrase_is_not_treated_as_duplicate_retry():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    first = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "नींद काफी देर से आती है और किसी काम में मन नहीं लगता है।"},
    )
    second = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "नींद देर से आती है और किसी काम में मन नहीं लगता है।"},
    )
    detail = client.get(f"/chat/sessions/{session_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["assistant_turn"]["turn_id"] > first.json()["assistant_turn"]["turn_id"]
    assert len(detail.json()["turns"]) == 5


def test_hinglish_downplayed_worry_stays_with_energy_or_mood_not_anxiety():
    start = client.post("/chat/sessions", json={"language": "hinglish"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Kal se body thodi down lag rahi hai aur neend bhi theek nahi hai."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Worry utni nahi hai, bas thakan aur udasi zyada lagti hai."},
    )

    assert turn.status_code == 200
    body = turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] in {"energy", "mood", "self_view"}
    assert "worry" not in body["assistant_turn"]["text"].lower()


def test_english_work_future_worry_opening_stays_on_anxiety_not_sleep():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "My mind keeps looping about work and the future late at night."},
    )

    assert turn.status_code == 200
    body = turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] in {"gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"}
    assert "sleep" not in body["assistant_turn"]["text"].lower()


def test_english_early_summary_request_keeps_closing_gaps_instead_of_ending():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "My mind keeps looping about work and the future, and it is hard to quiet it."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "If you have enough, please summarize the pattern."},
    )

    assert turn.status_code == 200
    body = turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    assert "working picture so far" not in body["assistant_turn"]["text"].lower()
    assert body["assistant_turn"]["text"].count("?") >= 1
    assert dialogue["stage"] in {"clarification", "exploration"}
    assert dialogue["closure_mode"] is True


def test_english_snappy_anxiety_turn_redirects_to_irritability_instead_of_repeating_fear():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    script = [
        "Sleep has shifted later lately.",
        "The next day I drag through everything.",
        "Lunch just slips and I realize way too late that I skipped it.",
        "Worry is mostly around work and future stuff.",
        "My mind keeps circling old conversations even when I want it to stop.",
        "Body side is there but smaller; evenings I get snappy.",
    ]

    last = None
    for text in script:
        last = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert last.status_code == 200

    body = last.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] in {"gad_q4_trouble_relaxing", "gad_q6_irritability"}
    assert "working picture so far" not in body["assistant_turn"]["text"].lower()
    assert body["assistant_turn"]["text"].count("?") >= 1


def test_physical_clarifier_physical_answer_uses_neutral_bridge_not_mood_or_anxiety():
    start = client.post(
        "/chat/sessions",
        json={
            "language": "en",
            "profile": {
                "recent_checkins": [
                    {"topic": "anxiety", "language": "en", "summary": "Recent anxiety check-in."}
                ]
            },
        },
    )
    session_id = start.json()["session_id"]

    first = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I am feeling a little under the weather today."},
    )
    second = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "It feels more physical than emotional honestly."},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    reply = second.json()["assistant_turn"]["text"].lower()
    assert "sleep" in reply
    assert "energy" in reply
    assert "appetite" in reply
    assert "interest drop" not in reply
    assert "worry starts" not in reply


def test_english_self_judging_phrase_stays_with_self_view_not_sleep():
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Sleep has been taking forever and I wake up tired."},
    )
    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "Even when I sleep, I drag through the day and meals get irregular too."},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I keep judging myself because basic tasks feel harder than they should."},
    )

    assert turn.status_code == 200
    body = turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    reply = body["assistant_turn"]["text"].lower()
    assert dialogue["target_topic"] in {"mood", "self_view"}
    assert dialogue["target_item"] in {None, "phq_q6_worthlessness"}
    assert "sleep" not in reply
    assert "yourself" in reply or "self" in reply


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

    assert reply.startswith("अब मेरे पास मुख्य पैटर्न पकड़ने लायक") or reply.startswith("ठीक है। अभी") or reply.startswith("मैं थोड़ा रुककर")


def test_exact_hindi_sleep_mood_trace_keeps_moving_and_does_not_repeat_same_prompt():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    script = [
        "नीम का पैटर्न बदल गया है नींद काफी देर से आती है और काफी कम समय के लिए",
        "यह कुछ दिनों से ऐसा ही है नींद कम आती है किसी काम में मन नहीं लगता है",
        "नींद का पैटर्न बदल गया काफी देर से जाता हूं काम में मन नहीं लगता",
        "मां पहले से ही है जाता है कोई काम करने की इच्छा करती ही नहीं है",
        "मैं कभी कुछ सकारात्मक रूप से भविष्य के बारे में सोचता हूं तो अच्छा लगता है परंतु जब मैं वर्तमान देखता हूं तो उदासी आती है",
        "उदासी और किसी काम से मन है जाना",
    ]

    replies = []
    for text in script:
        turn = client.post(f"/chat/sessions/{session_id}/turns", json={"text": text})
        assert turn.status_code == 200
        replies.append(turn.json()["assistant_turn"]["text"])

    assert replies[-1] != replies[-2]
    assert "जब यह सपाट या भारी एहसास रहता है" not in replies[-1]
    assert any(token in replies[-1] for token in ("थकान", "ऊर्जा", "शरीर भारी", "दिमाग शुरू"))


def test_hindi_explicit_work_future_worry_switches_out_of_mood_track():
    start = client.post("/chat/sessions", json={"language": "hi"})
    session_id = start.json()["session_id"]

    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "पता नहीं क्या असर पड़ता है"},
    )
    client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "वह चलाते रहती है कितना भी प्रयास करो"},
    )
    turn = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "हम फिलहाल में जब मैं किसी काम को करने जाता हूं तब मुझे ज्यादा चिंता होती है भविष्य को लेकर"},
    )

    assert turn.status_code == 200
    body = turn.json()
    dialogue = body["snapshot"]["coverage"]["dialogue"]
    reply = body["assistant_turn"]["text"]
    assert dialogue["target_topic"] == "anxiety"
    assert dialogue["target_item"] in {"gad_q2_control_worry", "gad_q4_trouble_relaxing"}
    assert (
        "जब चिंता शुरू होती है" in reply
        or "दिमाग को शांत" in reply
        or "शरीर को ढीला" in reply
        or "दोनों" in reply
    )
