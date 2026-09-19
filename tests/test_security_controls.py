from dataclasses import replace

from fastapi.testclient import TestClient

import manovarta_core.api as api_module


def test_session_cookie_is_httponly_and_required_for_session_export():
    owner = TestClient(api_module.app)
    start = owner.post("/chat/sessions", json={"language": "en"})

    assert start.status_code == 200
    assert "httponly" in start.headers["set-cookie"].lower()
    session_id = start.json()["session_id"]

    assert owner.get(f"/chat/sessions/{session_id}/export").status_code == 200
    stranger = TestClient(api_module.app)
    assert stranger.get(f"/chat/sessions/{session_id}/export").status_code == 403


def test_urgent_turn_uses_fixed_handoff_protocol_and_blocks_response_editor():
    client = TestClient(api_module.app)
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    response = client.post(
        f"/chat/sessions/{session_id}/turns",
        json={"text": "I am thinking about taking all my pills tonight."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_run"]["outcome"] == "urgent_handoff"
    assert any(
        handoff["agent"] == "Response Editor" and handoff["status"] == "blocked"
        for handoff in body["agent_run"]["handoffs"]
    )
    assert "988" in body["assistant_turn"]["text"]
    assert "14416" in body["assistant_turn"]["text"]


def test_production_operator_routes_require_secret_header(monkeypatch):
    production_config = replace(
        api_module.runtime_config,
        environment="production",
        internal_api_key="operator-secret",
    )
    monkeypatch.setattr(api_module, "runtime_config", production_config)
    client = TestClient(api_module.app)

    assert client.get("/runtime/config").status_code == 404
    assert client.get("/runtime/config", headers={"x-manovarta-admin-key": "wrong"}).status_code == 404
    assert client.get("/review").status_code == 404
    allowed = client.get("/runtime/config", headers={"x-manovarta-admin-key": "operator-secret"})
    assert allowed.status_code == 200
    assert "vertex_project" not in allowed.json()
    assert "local_safety_checkpoint_path" not in allowed.json()


def test_turn_payload_has_a_hard_upper_bound():
    client = TestClient(api_module.app)
    start = client.post("/chat/sessions", json={"language": "en"})
    session_id = start.json()["session_id"]

    response = client.post(f"/chat/sessions/{session_id}/turns", json={"text": "x" * 4001})

    assert response.status_code == 422
