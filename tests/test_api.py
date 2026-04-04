from fastapi.testclient import TestClient

from manovarta_core.api import app


client = TestClient(app)


def test_root_serves_browser_demo():
    response = client.get("/")

    assert response.status_code == 200
    assert "ManoVarta Runtime" in response.text
    assert "Start voice" in response.text
    assert "Gamified nudges" in response.text
    assert "Adaptive mirroring" in response.text


def test_runtime_config_reports_huggingface_disabled_by_default():
    response = client.get("/runtime/config")

    assert response.status_code == 200
    body = response.json()
    assert "provider" in body
    assert "chat_model" in body
    assert "huggingface_enabled" in body


def test_demo_bootstrap_exposes_runtime_profiles_and_links():
    response = client.get("/demo/bootstrap")

    assert response.status_code == 200
    body = response.json()
    assert body["health"]["status"] == "ok"
    assert "runtime" in body
    assert body["profiles"]
    assert body["links"]
    assert any(link["href"] == "/docs" for link in body["links"])


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
    assert snapshot["coverage"]["dialogue"]["target_topic"] in {"sleep", "energy", "mood"}
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
    assert (
        "one recent example or one timing detail is enough" in reply.lower()
        or "whichever part feels easier to answer is okay" in reply.lower()
    )
