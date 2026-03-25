from fastapi import FastAPI, HTTPException

from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.profiles import load_seed_profiles
from manovarta_core.questionnaires import grouped_items
from manovarta_core.reporting import build_summary
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import (
    ChatTurnRequest,
    ChatTurnResponse,
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

store = SessionStore()
planner = DialoguePlanner()
safety_monitor = SafetyMonitor()
scorer = ConversationScorer()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "active_sessions": store.size()}


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
    safety_flag = safety_monitor.assess(session.turns)
    snapshot = scorer.analyze(session.turns, session.language, safety_flag)
    reply_text, asked_item = planner.next_reply(snapshot, session)
    if asked_item and asked_item not in session.asked_items:
        session.asked_items.append(asked_item)
    assistant_turn = store.add_turn(session_id, "assistant", reply_text, session.language)
    return ChatTurnResponse(session_id=session_id, assistant_turn=assistant_turn, snapshot=snapshot)


@app.get("/chat/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str) -> SessionDetailResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    safety_flag = safety_monitor.assess(session.turns)
    snapshot = scorer.analyze(session.turns, session.language, safety_flag)
    return SessionDetailResponse(session_id=session_id, turns=session.turns, snapshot=snapshot)


@app.get("/chat/sessions/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: str) -> SummaryResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    safety_flag = safety_monitor.assess(session.turns)
    snapshot = scorer.analyze(session.turns, session.language, safety_flag)
    return SummaryResponse(session_id=session_id, summary=build_summary(session, snapshot), snapshot=snapshot)


@app.post("/screen/transcript")
def score_transcript(payload: TranscriptScoreRequest) -> dict:
    safety_flag = safety_monitor.assess(payload.turns)
    snapshot = scorer.analyze(payload.turns, payload.language, safety_flag)
    return {"snapshot": snapshot.model_dump()}
