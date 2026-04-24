from dataclasses import replace

from fastapi.testclient import TestClient

import manovarta_core.api as api_module
from manovarta_core.async_scoring import AsyncScoringStore
from manovarta_core.schemas import AsyncTranscriptScoreRequest, Turn


client = TestClient(api_module.app)


def test_async_scoring_store_round_trips_payload_and_result(tmp_path):
    store = AsyncScoringStore(tmp_path)
    payload = AsyncTranscriptScoreRequest(
        language="en",
        turns=[Turn(turn_id=1, speaker="user", text="I feel tired.", language_tag="en")],
        label="nightly-check",
        session_id="mv-demo",
        use_llm=True,
    )

    job = store.enqueue(payload)
    loaded = store.get(job.request_id)

    assert loaded.job.status == "pending"
    assert loaded.job.turn_count == 1
    assert store.load_payload(job.request_id).label == "nightly-check"

    store.mark_running(job.request_id)
    store.mark_completed(job.request_id, {"mode": "hybrid"})
    completed = store.get(job.request_id)

    assert completed.job.status == "completed"
    assert completed.result == {"mode": "hybrid"}


def test_api_enqueues_async_transcript_score(tmp_path, monkeypatch):
    monkeypatch.setattr(api_module, "runtime_config", replace(api_module.runtime_config, async_scoring_enabled=True, async_scoring_dir=str(tmp_path)))
    monkeypatch.setattr(api_module, "async_scoring_store", AsyncScoringStore(tmp_path))

    response = client.post(
        "/screen/transcript/async",
        json={
            "language": "en",
            "turns": [{"turn_id": 1, "speaker": "user", "text": "I feel tired.", "language_tag": "en"}],
            "label": "api-test",
            "use_llm": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job"]["status"] == "pending"
    request_id = body["job"]["request_id"]

    poll = client.get(f"/screen/requests/{request_id}")
    assert poll.status_code == 200
    assert poll.json()["job"]["label"] == "api-test"
