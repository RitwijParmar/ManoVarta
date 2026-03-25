from fastapi.testclient import TestClient

from manovarta_core.api import app


client = TestClient(app)


def test_runtime_config_reports_huggingface_disabled_by_default():
    response = client.get("/runtime/config")

    assert response.status_code == 200
    body = response.json()
    assert "provider" in body
    assert "chat_model" in body
    assert "huggingface_enabled" in body


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
    assert "hurting yourself" not in reply
    assert "not wanting to be alive" not in reply


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
    assert "Session" in body["summary"]
