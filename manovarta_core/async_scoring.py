from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4

from manovarta_core.schemas import AsyncScoreJob, AsyncScoreResponse, AsyncTranscriptScoreRequest


class AsyncScoringStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.requests_dir = self.root / "requests"
        self.results_dir = self.root / "results"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, payload: AsyncTranscriptScoreRequest) -> AsyncScoreJob:
        request_id = f"score-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        job = AsyncScoreJob(
            request_id=request_id,
            status="pending",
            language=payload.language,
            turn_count=len(payload.turns),
            use_llm=payload.use_llm,
            label=payload.label,
            session_id=payload.session_id,
            created_at=now,
            updated_at=now,
        )
        envelope = {
            "job": job.model_dump(mode="json"),
            "payload": payload.model_dump(mode="json"),
        }
        self._request_path(request_id).write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return job

    def get(self, request_id: str) -> AsyncScoreResponse:
        envelope = self._load_request_envelope(request_id)
        if envelope is None:
            raise FileNotFoundError(request_id)
        result = self._load_result(request_id)
        return AsyncScoreResponse(
            job=AsyncScoreJob.model_validate(envelope["job"]),
            result=result,
        )

    def list_pending(self) -> list[AsyncScoreJob]:
        jobs: list[AsyncScoreJob] = []
        for path in sorted(self.requests_dir.glob("*.json")):
            envelope = json.loads(path.read_text(encoding="utf-8"))
            job = AsyncScoreJob.model_validate(envelope["job"])
            if job.status == "pending":
                jobs.append(job)
        return jobs

    def load_payload(self, request_id: str) -> AsyncTranscriptScoreRequest:
        envelope = self._load_request_envelope(request_id)
        if envelope is None:
            raise FileNotFoundError(request_id)
        return AsyncTranscriptScoreRequest.model_validate(envelope["payload"])

    def mark_running(self, request_id: str) -> AsyncScoreJob:
        return self._update_job(request_id, status="running", error=None)

    def mark_completed(self, request_id: str, result: dict) -> AsyncScoreJob:
        result_path = self._result_path(request_id)
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._update_job(request_id, status="completed", error=None)

    def mark_failed(self, request_id: str, error: str) -> AsyncScoreJob:
        return self._update_job(request_id, status="failed", error=error)

    def iter_pending_ids(self) -> Iterable[str]:
        for job in self.list_pending():
            yield job.request_id

    def _update_job(self, request_id: str, **updates) -> AsyncScoreJob:
        envelope = self._load_request_envelope(request_id)
        if envelope is None:
            raise FileNotFoundError(request_id)
        job = AsyncScoreJob.model_validate(envelope["job"])
        merged = job.model_copy(
            update={
                **updates,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        envelope["job"] = merged.model_dump(mode="json")
        self._request_path(request_id).write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return merged

    def _load_request_envelope(self, request_id: str) -> Optional[dict]:
        path = self._request_path(request_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_result(self, request_id: str) -> Optional[dict]:
        path = self._result_path(request_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _request_path(self, request_id: str) -> Path:
        return self.requests_dir / f"{request_id}.json"

    def _result_path(self, request_id: str) -> Path:
        return self.results_dir / f"{request_id}.json"
