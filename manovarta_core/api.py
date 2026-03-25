from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from manovarta_core.config import get_runtime_config
from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.engine import RuntimeEngine
from manovarta_core.llm import HuggingFaceExtractor, HuggingFaceResponder
from manovarta_core.profiles import load_seed_profiles
from manovarta_core.questionnaires import grouped_items
from manovarta_core.reporting import build_rows, build_summary
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import (
    ChatTurnRequest,
    ChatTurnResponse,
    SessionExportResponse,
    SessionDetailResponse,
    StartSessionRequest,
    StartSessionResponse,
    SummaryResponse,
    TranscriptScoreRequest,
)
from manovarta_core.sessions import SessionStore


app = FastAPI(
    title="ManoVarta Runtime",
    version="0.1.0",
    description="Text-first multilingual screening prototype with evidence extraction and safety checks.",
)

WEB_DIR = Path(__file__).resolve().parent / "web"

runtime_config = get_runtime_config()
store = SessionStore()
planner = DialoguePlanner()
safety_monitor = SafetyMonitor()
scorer = ConversationScorer()
responder = HuggingFaceResponder(runtime_config)
extractor = HuggingFaceExtractor(runtime_config)
engine = RuntimeEngine(scorer=scorer, safety_monitor=safety_monitor, extractor=extractor)

if WEB_DIR.exists():
    app.mount("/app-assets", StaticFiles(directory=WEB_DIR), name="app-assets")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "active_sessions": store.size()}


@app.get("/runtime/config")
def runtime_settings() -> dict:
    return {
        "provider": runtime_config.model_provider,
        "chat_model": runtime_config.chat_model,
        "extraction_model": runtime_config.extraction_model,
        "huggingface_enabled": runtime_config.huggingface_enabled,
    }


@app.get("/questionnaires")
def questionnaires() -> dict:
    return {
        name: [item.__dict__ for item in items]
        for name, items in grouped_items().items()
    }


@app.get("/profiles")
def profiles() -> list:
    return load_seed_profiles()


@app.post("/chat/sessions", response_model=StartSessionResponse)
def start_session(payload: StartSessionRequest) -> StartSessionResponse:
    session = store.create(payload.language)
    opening_text = planner.opening_prompt(payload.language)
    assistant_turn = store.add_turn(session.session_id, "assistant", opening_text, payload.language)
    return StartSessionResponse(session_id=session.session_id, assistant_turn=assistant_turn)


@app.post("/chat/sessions/{session_id}/turns", response_model=ChatTurnResponse)
def add_turn(session_id: str, payload: ChatTurnRequest) -> ChatTurnResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    store.add_turn(session_id, "user", payload.text, session.language)
    snapshot = engine.analyze(session.turns, session.language)
    fallback_text, asked_item = planner.next_reply(snapshot, session)
    reply_text, source = responder.compose_reply(session, snapshot, asked_item, fallback_text)
    if asked_item and asked_item not in session.asked_items:
        session.asked_items.append(asked_item)
    assistant_turn = store.add_turn(
        session_id,
        "assistant",
        reply_text,
        session.language,
        notes=f"source:{source}",
    )
    return ChatTurnResponse(session_id=session_id, assistant_turn=assistant_turn, snapshot=snapshot)


@app.get("/chat/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str) -> SessionDetailResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    snapshot = engine.analyze(session.turns, session.language)
    return SessionDetailResponse(session_id=session_id, turns=session.turns, snapshot=snapshot)


@app.get("/chat/sessions/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: str) -> SummaryResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    snapshot = engine.analyze(session.turns, session.language)
    return SummaryResponse(session_id=session_id, summary=build_summary(session, snapshot), snapshot=snapshot)


@app.get("/chat/sessions/{session_id}/export", response_model=SessionExportResponse)
def export_session(session_id: str) -> SessionExportResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    snapshot = engine.analyze(session.turns, session.language)
    return SessionExportResponse(
        session_id=session_id,
        language=session.language,
        summary=build_summary(session, snapshot),
        turns=session.turns,
        snapshot=snapshot,
        rows=build_rows(snapshot),
    )


@app.post("/screen/transcript")
def score_transcript(payload: TranscriptScoreRequest) -> dict:
    snapshot = engine.analyze(payload.turns, payload.language)
    return {"mode": snapshot.mode, "snapshot": snapshot.model_dump()}


@app.post("/screen/transcript/heuristic")
def score_transcript_heuristic(payload: TranscriptScoreRequest) -> dict:
    safety_flag = safety_monitor.assess(payload.turns)
    snapshot = scorer.analyze(payload.turns, payload.language, safety_flag)
    return {"mode": snapshot.mode, "snapshot": snapshot.model_dump()}


@app.post("/screen/transcript/llm")
def score_transcript_with_llm(payload: TranscriptScoreRequest) -> dict:
    if not extractor.enabled:
        raise HTTPException(status_code=503, detail="Hugging Face runtime is not configured.")

    result = extractor.extract(payload.turns, payload.language)
    if result is None:
        raise HTTPException(status_code=502, detail="LLM extraction failed.")
    return {
        "provider": runtime_config.model_provider,
        "model": runtime_config.extraction_model,
        "result": result,
    }
