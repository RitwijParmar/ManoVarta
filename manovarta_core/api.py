import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from manovarta_core.async_scoring import AsyncScoringStore
from manovarta_core.config import get_runtime_config
from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.engine import RuntimeEngine
from manovarta_core.knowledge import SCREENING_KNOWLEDGE_BASE
from manovarta_core.llm import HuggingFaceExtractor, HuggingFaceResponder, HuggingFaceSafetyAssessor
from manovarta_core.profiles import load_seed_profiles
from manovarta_core.questionnaires import grouped_items
from manovarta_core.reporting import build_rows, build_summary
from manovarta_core.safety_assessors import CompositeSafetyAssessor, LocalSafetyCheckpointAssessor
from manovarta_core.semantic_safety import SemanticSafetyConfig, SemanticSafetyMonitor
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.text import normalize_text
from manovarta_core.schemas import (
    ChatTurnRequest,
    ChatTurnResponse,
    ChatSession,
    AsyncScoreResponse,
    AsyncTranscriptScoreRequest,
    NudgeEvent,
    SessionExportResponse,
    SessionDetailResponse,
    SafetyFlag,
    StartSessionRequest,
    StartSessionResponse,
    SummaryResponse,
    TranscriptScoreRequest,
    Turn,
)
from manovarta_core.sessions import SessionStore
from manovarta_core.voice import detect_voice_runtime, synthesize_speech, transcribe_audio


app = FastAPI(
    title="ManoVarta Runtime",
    version="0.1.0",
    description="Text-first multilingual screening prototype with evidence extraction and safety checks.",
)

WEB_DIR = Path(__file__).resolve().parent / "web"
voice_runtime = detect_voice_runtime()

runtime_config = get_runtime_config()
store = SessionStore()
async_scoring_store = AsyncScoringStore(runtime_config.async_scoring_dir)
planner = DialoguePlanner()
safety_monitor = SafetyMonitor()
semantic_safety_monitor = SemanticSafetyMonitor(
    SemanticSafetyConfig(
        model_name=runtime_config.semantic_safety_model,
        review_threshold=runtime_config.semantic_safety_review_threshold,
        urgent_threshold=runtime_config.semantic_safety_urgent_threshold,
    )
)
scorer = ConversationScorer()
responder = HuggingFaceResponder(runtime_config)
extractor = HuggingFaceExtractor(runtime_config)
local_safety_assessor = LocalSafetyCheckpointAssessor(runtime_config.local_safety_checkpoint)
hf_safety_assessor = None if local_safety_assessor.enabled else HuggingFaceSafetyAssessor(runtime_config)
safety_assessor = CompositeSafetyAssessor(
    [
        local_safety_assessor,
        hf_safety_assessor,
    ]
)
engine = RuntimeEngine(
    scorer=scorer,
    safety_monitor=safety_monitor,
    semantic_safety_monitor=semantic_safety_monitor,
    safety_assessor=safety_assessor,
    extractor=extractor,
)


def _build_live_chat_analysis_stack():
    live_provider = runtime_config.live_chat_extraction_model_provider
    live_model = runtime_config.live_chat_extraction_model or runtime_config.extraction_model
    base_provider = runtime_config.extraction_model_provider
    if live_provider == base_provider and live_model == runtime_config.extraction_model:
        return runtime_config, extractor, engine

    live_config = replace(
        runtime_config,
        extraction_provider=live_provider,
        extraction_model=live_model,
    )
    live_extractor = HuggingFaceExtractor(live_config)
    live_engine = RuntimeEngine(
        scorer=scorer,
        safety_monitor=safety_monitor,
        semantic_safety_monitor=semantic_safety_monitor,
        safety_assessor=safety_assessor,
        extractor=live_extractor,
    )
    return live_config, live_extractor, live_engine


live_chat_runtime_config, live_chat_extractor, live_chat_engine = _build_live_chat_analysis_stack()

if WEB_DIR.exists():
    app.mount("/app-assets", StaticFiles(directory=WEB_DIR), name="app-assets")


REVIEW_BUTTON_RE = re.compile(r"\s*<button id=\"architectureButton\".*?</button>", re.DOTALL)
DUPLICATE_TURN_WINDOW_SECONDS = 12
TURN_RECOVERY_MESSAGES = {
    "en": "I lost one step of the thread for a moment. Say that again in one short line, and I’ll keep the next question focused.",
    "hi": "एक पल के लिए बात का धागा छूट गया। वही बात एक छोटी पंक्ति में फिर से कह दीजिए, मैं अगला सवाल साफ़ और केंद्रित रखूँगा।",
    "hinglish": "Ek moment ke liye thread slip ho gaya. Wahi baat ek short line mein dobara bol do, main agla sawaal focused rakhunga.",
}
SUMMARY_RECOVERY_MESSAGES = {
    "en": "A working summary is still being rebuilt after a runtime hiccup.",
    "hi": "रनटाइम रुकावट के बाद कामचलाऊ सार फिर से बनाया जा रहा है।",
    "hinglish": "Runtime hiccup ke baad working summary dobara build ho rahi hai.",
}


def _asset_version() -> str:
    tracked = ["app.css", "app.js", "brand-mark.svg", "favicon.svg", "index.html"]
    stamp = 0
    for name in tracked:
        path = WEB_DIR / name
        if path.exists():
            stamp = max(stamp, path.stat().st_mtime_ns)
    return str(stamp or 1)


def _inject_asset_version(html: str) -> str:
    version = _asset_version()
    replacements = {
        "/app-assets/favicon.svg": f"/app-assets/favicon.svg?v={version}",
        "/app-assets/app.css": f"/app-assets/app.css?v={version}",
        "/app-assets/brand-mark.svg": f"/app-assets/brand-mark.svg?v={version}",
        "/app-assets/app.js": f"/app-assets/app.js?v={version}",
    }
    for source, target in replacements.items():
        html = html.replace(source, target)
    return html


def _safe_rule_safety_flag(turns: list[Turn]) -> SafetyFlag:
    try:
        return safety_monitor.assess(turns)
    except Exception:
        return SafetyFlag(level="none")


def _safe_analyze(turns: list[Turn], language: str, *, use_llm: bool = True):
    active_engine = live_chat_engine if use_llm else engine
    try:
        return active_engine.analyze(turns, language, use_llm=use_llm)
    except Exception:
        try:
            return scorer.analyze(turns, language, _safe_rule_safety_flag(turns))
        except Exception:
            return scorer.analyze(turns, language, SafetyFlag(level="none"))


def _safe_summary(session: ChatSession, snapshot) -> str:
    try:
        return build_summary(session, snapshot)
    except Exception:
        return SUMMARY_RECOVERY_MESSAGES.get(session.language, SUMMARY_RECOVERY_MESSAGES["en"])


def _safe_rows(snapshot) -> list[dict]:
    try:
        return [row.model_dump() for row in build_rows(snapshot)]
    except Exception:
        return []


def _safe_row_models(snapshot) -> list:
    try:
        return build_rows(snapshot)
    except Exception:
        return []


def _render_shell(include_review: bool) -> HTMLResponse:
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    if include_review:
        return HTMLResponse(
            _inject_asset_version(html),
            headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"},
        )

    html = REVIEW_BUTTON_RE.sub("", html, count=1)
    backstage_start = html.find('<section id="backstagePanel"')
    script_start = html.find('<script src="/app-assets/app.js" defer></script>')
    if backstage_start != -1 and script_start != -1:
        html = f"{html[:backstage_start]}    </div>\n\n    {html[script_start:]}"
    return HTMLResponse(
        _inject_asset_version(html),
        headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"},
    )


def _token_set(text: str) -> set[str]:
    return {token for token in normalize_text(text).split() if token}


def _near_duplicate_text(left: str, right: str) -> bool:
    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)
    if not normalized_left or not normalized_right:
        return False
    if normalized_left == normalized_right:
        return True

    shorter, longer = sorted((normalized_left, normalized_right), key=len)
    if len(shorter) >= 18 and shorter in longer:
        return True

    left_tokens = _token_set(normalized_left)
    right_tokens = _token_set(normalized_right)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    return overlap >= 0.82


def _collapse_adjacent_duplicate_tokens(text: str) -> str:
    tokens = normalize_text(text).split()
    collapsed: list[str] = []
    for token in tokens:
        if collapsed and collapsed[-1] == token:
            continue
        collapsed.append(token)
    return " ".join(collapsed)


def _recent_duplicate_retry(session: ChatSession, incoming_text: str, *, from_voice: bool = False) -> Optional[Turn]:
    if len(session.turns) < 2:
        return None
    last_turn = session.turns[-1]
    previous_turn = session.turns[-2]
    if last_turn.speaker != "assistant" or previous_turn.speaker != "user":
        return None
    age_seconds = (datetime.utcnow() - last_turn.created_at).total_seconds()
    if age_seconds > DUPLICATE_TURN_WINDOW_SECONDS:
        return None
    normalized_previous = normalize_text(previous_turn.text)
    normalized_incoming = normalize_text(incoming_text)
    if not normalized_previous or not normalized_incoming:
        return None
    if normalized_previous == normalized_incoming:
        return last_turn
    if not from_voice and _collapse_adjacent_duplicate_tokens(previous_turn.text) == _collapse_adjacent_duplicate_tokens(incoming_text):
        return last_turn
    if from_voice and _near_duplicate_text(previous_turn.text, incoming_text):
        return last_turn
    return None


def _should_use_live_llm(session: ChatSession) -> bool:
    user_turns = sum(1 for turn in session.turns if turn.speaker == "user")
    if runtime_config.live_chat_llm_analysis_enabled:
        if not live_chat_extractor.enabled:
            return False
        threshold = max(runtime_config.live_llm_turn_threshold, 1)
        if user_turns < threshold:
            return False
        if runtime_config.live_chat_extraction_model_provider == "remote":
            return (user_turns - threshold) % 3 == 0
        return True
    if not session.turns:
        return False
    # Elevated-risk turns should return immediately from the runtime safety stack
    # instead of paying extractor latency.
    return False


@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    return _render_shell(include_review=False)


@app.get("/review", include_in_schema=False)
def review() -> Response:
    review_path = WEB_DIR / "review.html"
    if review_path.exists():
        return FileResponse(review_path)
    return _render_shell(include_review=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "active_sessions": store.size()}


@app.get("/runtime/config")
def runtime_settings() -> dict:
    return {
        "provider": runtime_config.model_provider,
        "chat_provider": runtime_config.chat_model_provider,
        "extraction_provider": runtime_config.extraction_model_provider,
        "safety_provider": runtime_config.safety_model_provider,
        "controller_model": runtime_config.chat_model,
        "extractor_model": runtime_config.extraction_model,
        "chat_model": runtime_config.chat_model,
        "chat_fallback_model": runtime_config.resolved_chat_fallback_model,
        "live_chat_analysis_model": runtime_config.resolved_live_chat_analysis_model,
        "live_chat_analysis_fallback_model": runtime_config.resolved_live_chat_analysis_fallback_model,
        "extraction_model": runtime_config.extraction_model,
        "safety_model": runtime_config.safety_model,
        "huggingface_enabled": runtime_config.huggingface_enabled,
        "self_hosted_inference_enabled": runtime_config.local_inference_enabled,
        "vertex_enabled": runtime_config.vertex_enabled,
        "vertex_project": runtime_config.vertex_project,
        "vertex_location": runtime_config.vertex_location,
        "vertex_chat_location": runtime_config.resolved_vertex_chat_location,
        "vertex_chat_fallback_location": runtime_config.resolved_vertex_chat_fallback_location,
        "vertex_live_chat_analysis_location": runtime_config.resolved_vertex_live_chat_analysis_location,
        "vertex_live_chat_analysis_fallback_location": runtime_config.resolved_vertex_live_chat_analysis_fallback_location,
        "remote_extraction_enabled": bool(runtime_config.remote_extraction_url),
        "remote_extraction_url_configured": bool(runtime_config.remote_extraction_url),
        "live_chat_extraction_provider": live_chat_runtime_config.extraction_model_provider,
        "live_chat_extraction_model": live_chat_runtime_config.extraction_model,
        "semantic_safety_enabled": runtime_config.semantic_safety_enabled,
        "semantic_safety_model": runtime_config.semantic_safety_model,
        "hybrid_safety_enabled": bool(runtime_config.local_safety_checkpoint),
        "local_safety_checkpoint_enabled": bool(runtime_config.local_safety_checkpoint),
        "local_safety_checkpoint_path": runtime_config.local_safety_checkpoint,
        "remote_safety_fallback_enabled": bool(hf_safety_assessor and hf_safety_assessor.enabled),
        "live_chat_llm_analysis_enabled": runtime_config.live_chat_llm_analysis_enabled,
        "async_scoring_enabled": runtime_config.async_scoring_enabled,
        "async_scoring_dir": runtime_config.async_scoring_dir,
        "cloud_voice_enabled": voice_runtime.enabled,
        "speech_to_text_enabled": voice_runtime.speech_to_text,
        "text_to_speech_enabled": voice_runtime.text_to_speech,
    }


@app.get("/demo/bootstrap")
def demo_bootstrap() -> dict:
    profiles = []
    for profile in load_seed_profiles():
        background = profile.get("background_profile", {}) or {}
        symptoms = profile.get("symptom_profile", {}) or {}
        profiles.append(
            {
                "patient_id": profile.get("patient_id"),
                "language": profile.get("language", "en"),
                "age": profile.get("age"),
                "occupation": profile.get("occupation", "participant"),
                "context": background.get("context", ""),
                "depression_level": symptoms.get("depression_level", "unknown"),
                "anxiety_level": symptoms.get("anxiety_level", "unknown"),
                "notes": profile.get("notes", ""),
                "nuance_tags": profile.get("nuance_tags", [])[:4],
            }
        )

    return {
        "health": {"status": "ok", "active_sessions": store.size()},
        "runtime": runtime_settings(),
        "profiles": profiles,
        "links": [
            {"label": "Health", "href": "/health", "description": "Service heartbeat and active session count"},
            {"label": "Runtime config", "href": "/runtime/config", "description": "Active provider and model selection"},
            {"label": "Profiles", "href": "/profiles", "description": "Seed profile presets for demos"},
            {"label": "Questionnaires", "href": "/questionnaires", "description": "PHQ-9 and GAD-7 questionnaire items"},
            {"label": "Knowledge base", "href": "/knowledge/base", "description": "Derived symptom and safety guidance"},
            {"label": "OpenAPI docs", "href": "/docs", "description": "Interactive endpoint explorer"},
        ],
    }


@app.get("/questionnaires")
def questionnaires() -> dict:
    return {
        name: [item.__dict__ for item in items]
        for name, items in grouped_items().items()
    }


@app.get("/knowledge/base")
def knowledge_base() -> dict:
    return SCREENING_KNOWLEDGE_BASE


@app.get("/profiles")
def profiles() -> list:
    return load_seed_profiles()


@app.post("/chat/sessions", response_model=StartSessionResponse)
def start_session(payload: StartSessionRequest) -> StartSessionResponse:
    session = store.create(payload.language, payload.profile)
    opening_text = planner.opening_prompt(payload.language, payload.profile)
    assistant_turn = store.add_turn(session.session_id, "assistant", opening_text, payload.language)
    return StartSessionResponse(session_id=session.session_id, assistant_turn=assistant_turn)


@app.post("/chat/sessions/{session_id}/turns", response_model=ChatTurnResponse)
def add_turn(session_id: str, payload: ChatTurnRequest) -> ChatTurnResponse:
    if store.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    with store.locked(session_id) as session:
        duplicate_reply = _recent_duplicate_retry(session, payload.text, from_voice=payload.from_voice)
        if duplicate_reply is not None:
            use_llm = _should_use_live_llm(session)
            snapshot = _safe_analyze(session.turns, session.language, use_llm=use_llm)
            return ChatTurnResponse(
                session_id=session_id,
                assistant_turn=duplicate_reply,
                snapshot=snapshot,
                summary=_safe_summary(session, snapshot),
                rows=_safe_rows(snapshot),
            )

        previous_snapshot = None
        if payload.nudge_id and payload.nudge_strategy:
            prior_use_llm = _should_use_live_llm(session)
            previous_snapshot = _safe_analyze(session.turns, session.language, use_llm=prior_use_llm)
        user_notes = []
        if payload.from_voice:
            user_notes.append("source:voice")
        if payload.nudge_id:
            user_notes.append(f"nudge:{payload.nudge_id}")
        user_turn = store.add_turn(
            session_id,
            "user",
            payload.text,
            session.language,
            notes=" | ".join(user_notes) if user_notes else None,
        )
        use_llm = _should_use_live_llm(session)
        snapshot = _safe_analyze(session.turns, session.language, use_llm=use_llm)
        if payload.nudge_id and payload.nudge_strategy and previous_snapshot is not None:
            evidence_gain = max(snapshot.coverage.touched_items - previous_snapshot.coverage.touched_items, 0)
            resolved_gain = max(len(snapshot.coverage.resolved_items) - len(previous_snapshot.coverage.resolved_items), 0)
            words_added = len(payload.text.split())
            low_burden_strategies = {"choice", "scale", "safety"}
            contextual_strategies = {"compare", "body", "coping", "support"}
            helpful = (
                evidence_gain > 0
                or resolved_gain > 0
                or words_added >= 18
                or (payload.nudge_strategy in low_burden_strategies and words_added >= 6)
                or (payload.nudge_strategy in contextual_strategies and words_added >= 10)
            )
            outcome = "helpful" if helpful else "unhelpful"
            session.nudge_events.append(
                NudgeEvent(
                    nudge_id=payload.nudge_id,
                    strategy=payload.nudge_strategy,
                    title=payload.nudge_title,
                    turn_id=user_turn.turn_id,
                    words_added=words_added,
                    evidence_gain=evidence_gain,
                    resolved_gain=resolved_gain,
                    outcome=outcome,
                )
            )
        try:
            fallback_text, asked_item = planner.next_reply(snapshot, session)
            reply_text, source = responder.compose_reply(session, snapshot, asked_item, fallback_text)
        except Exception:
            fallback_text = TURN_RECOVERY_MESSAGES[session.language]
            asked_item = None
            reply_text, source = fallback_text, "recovery"
        if asked_item:
            session.asked_items.append(asked_item)
        dialogue = snapshot.coverage.dialogue
        if dialogue.active_domain != "rapport":
            session.domain_history.append(dialogue.active_domain)
            session.domain_history = session.domain_history[-12:]
        if dialogue.target_scene:
            session.scene_history.append(dialogue.target_scene)
            session.scene_history = session.scene_history[-8:]
        if dialogue.blocked_items:
            merged_blocked = list(dict.fromkeys([*session.blocked_items, *dialogue.blocked_items]))
            session.blocked_items = merged_blocked[-12:]
        assistant_turn = store.add_turn(
            session_id,
            "assistant",
            reply_text,
            session.language,
            notes=f"source:{source}",
        )
        return ChatTurnResponse(
            session_id=session_id,
            assistant_turn=assistant_turn,
            snapshot=snapshot,
            summary=_safe_summary(session, snapshot),
            rows=_safe_rows(snapshot),
        )


@app.get("/chat/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str) -> SessionDetailResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    snapshot = _safe_analyze(session.turns, session.language)
    snapshot.coverage = planner.build_plan(snapshot, session)
    return SessionDetailResponse(session_id=session_id, profile=session.profile, turns=session.turns, snapshot=snapshot)


@app.get("/chat/sessions/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: str) -> SummaryResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    snapshot = _safe_analyze(session.turns, session.language)
    snapshot.coverage = planner.build_plan(snapshot, session)
    return SummaryResponse(session_id=session_id, summary=_safe_summary(session, snapshot), snapshot=snapshot)


@app.get("/chat/sessions/{session_id}/export", response_model=SessionExportResponse)
def export_session(session_id: str) -> SessionExportResponse:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    snapshot = _safe_analyze(session.turns, session.language)
    snapshot.coverage = planner.build_plan(snapshot, session)
    return SessionExportResponse(
        session_id=session_id,
        language=session.language,
        profile=session.profile,
        summary=_safe_summary(session, snapshot),
        turns=session.turns,
        snapshot=snapshot,
        rows=_safe_row_models(snapshot),
    )


@app.post("/screen/transcript")
def score_transcript(payload: TranscriptScoreRequest) -> dict:
    snapshot = _safe_analyze(payload.turns, payload.language)
    return {"mode": snapshot.mode, "snapshot": snapshot.model_dump()}


@app.post("/screen/transcript/heuristic")
def score_transcript_heuristic(payload: TranscriptScoreRequest) -> dict:
    safety_flag = _safe_rule_safety_flag(payload.turns)
    snapshot = scorer.analyze(payload.turns, payload.language, safety_flag)
    return {"mode": snapshot.mode, "snapshot": snapshot.model_dump()}


@app.post("/screen/transcript/llm")
def score_transcript_with_llm(payload: TranscriptScoreRequest) -> dict:
    if not extractor.enabled:
        raise HTTPException(status_code=503, detail="Extractor runtime is not configured.")

    result = extractor.extract(payload.turns, payload.language)
    if result is None:
        raise HTTPException(status_code=502, detail="LLM extraction failed.")
    return {
        "provider": runtime_config.extraction_model_provider,
        "model": runtime_config.extraction_model,
        "result": result,
    }


@app.post("/screen/transcript/async", response_model=AsyncScoreResponse)
def enqueue_transcript_score(payload: AsyncTranscriptScoreRequest) -> AsyncScoreResponse:
    if not runtime_config.async_scoring_enabled:
        raise HTTPException(status_code=503, detail="Asynchronous scoring is not configured.")
    job = async_scoring_store.enqueue(payload)
    return AsyncScoreResponse(job=job, result=None)


@app.post("/chat/sessions/{session_id}/score_async", response_model=AsyncScoreResponse)
def enqueue_session_score(session_id: str) -> AsyncScoreResponse:
    if not runtime_config.async_scoring_enabled:
        raise HTTPException(status_code=503, detail="Asynchronous scoring is not configured.")
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    payload = AsyncTranscriptScoreRequest(
        language=session.language,
        turns=session.turns,
        session_id=session_id,
        label="session_async_score",
        use_llm=True,
    )
    job = async_scoring_store.enqueue(payload)
    return AsyncScoreResponse(job=job, result=None)


@app.get("/screen/requests/{request_id}", response_model=AsyncScoreResponse)
def get_async_score(request_id: str) -> AsyncScoreResponse:
    try:
        return async_scoring_store.get(request_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Score request not found.") from exc


@app.post("/voice/transcribe")
async def transcribe_voice(language: str, audio: UploadFile = File(...)) -> dict:
    if not voice_runtime.speech_to_text:
        raise HTTPException(status_code=503, detail="Cloud speech-to-text is not configured.")

    content = await audio.read()
    try:
        transcript = transcribe_audio(content, language=language, mime_type=audio.content_type or "audio/webm")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Voice transcription failed: {exc}") from exc
    return {"language": language, "transcript": transcript}


@app.post("/voice/speak")
def speak_voice(payload: ChatTurnRequest, language: str = "en") -> Response:
    if not voice_runtime.text_to_speech:
        raise HTTPException(status_code=503, detail="Cloud text-to-speech is not configured.")

    try:
        audio_content, media_type = synthesize_speech(payload.text, language=language)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {exc}") from exc
    return Response(content=audio_content, media_type=media_type)
