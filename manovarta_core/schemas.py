from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Speaker = Literal["assistant", "user"]
LanguageCode = Literal["en", "hi", "hinglish"]
SafetyLevel = Literal["none", "review", "urgent"]
ItemStatus = Literal["resolved", "partial", "contradicted", "unresolved", "abstained"]
DialogueStage = Literal["rapport", "exploration", "clarification", "safety", "summary"]
DialogueAction = Literal["reflect", "open_question", "symptom_probe", "clarify", "risk_check", "summarize", "handoff"]
TopicStatus = Literal["pending", "probing", "stable", "review", "held_back"]
VerbosityBand = Literal["brief", "balanced", "detailed"]
OpennessBand = Literal["guarded", "cautious", "open"]
DistressTrend = Literal["unclear", "steady", "rising", "easing"]
CodeMixLevel = Literal["low", "medium", "high"]
EmpathyLevel = Literal["moderate", "high"]
SteeringPreference = Literal["guided", "balanced", "user_led"]
ReadinessLevel = Literal["opening", "building", "steady", "ready_to_close"]
FatigueLevel = Literal["low", "medium", "high"]
NudgeOutcome = Literal["unknown", "helpful", "unhelpful"]
AsyncScoreStatus = Literal["pending", "running", "completed", "failed"]
DomainTrack = Literal["phq", "gad", "safety", "rapport"]


class Turn(BaseModel):
    turn_id: int
    speaker: Speaker
    text: str
    language_tag: LanguageCode
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceSpan(BaseModel):
    span_id: str
    questionnaire: Literal["PHQ9", "GAD7"]
    item_id: str
    turn_id: int
    text_span: str
    polarity: Literal["present", "absent", "uncertain"]
    score_hint: int = Field(ge=0, le=3)
    rationale: str


class ItemScore(BaseModel):
    item_id: str
    questionnaire: Literal["PHQ9", "GAD7"]
    value: Optional[int] = Field(default=None, ge=0, le=3)
    status: ItemStatus
    confidence: float = Field(ge=0.0, le=1.0)
    stable: bool = False
    evidence_span_ids: List[str] = Field(default_factory=list)
    contradiction_note: Optional[str] = None
    source: Literal["none", "heuristic", "llm", "hybrid"] = "heuristic"
    review_recommended: bool = False


class SafetyFlag(BaseModel):
    level: SafetyLevel = "none"
    cues: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    needs_human_review: bool = False


class TopicState(BaseModel):
    topic_id: str
    label: str
    item_ids: List[str] = Field(default_factory=list)
    touched: bool = False
    priority: int = 0
    confidence: float = Field(ge=0.0, le=1.0)
    status: TopicStatus = "pending"
    resolved_items: List[str] = Field(default_factory=list)
    unresolved_items: List[str] = Field(default_factory=list)
    review_items: List[str] = Field(default_factory=list)


class UserStyleProfile(BaseModel):
    avg_words_per_turn: float = Field(default=0.0, ge=0.0)
    verbosity: VerbosityBand = "balanced"
    openness: OpennessBand = "cautious"
    code_mix: CodeMixLevel = "low"
    distress_trend: DistressTrend = "unclear"
    empathy_level: EmpathyLevel = "moderate"
    steering_preference: SteeringPreference = "balanced"


class DisclosureMetrics(BaseModel):
    user_turns: int = 0
    touched_items: int = 0
    resolved_items: int = 0
    stable_topics: int = 0
    items_per_user_turn: float = Field(default=0.0, ge=0.0)
    resolved_per_user_turn: float = Field(default=0.0, ge=0.0)
    nudge_effectiveness: float = Field(default=0.0, ge=-1.0, le=1.0)


class DialogueAnalyzerEvidence(BaseModel):
    item: str
    status: Literal["resolved", "partial", "contradicted", "none"] = "none"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    quote_span: str = ""
    polarity: Literal["positive", "negative", "mixed"] = "positive"


class DialogueAnalyzerSafety(BaseModel):
    level: SafetyLevel = "none"
    reason: str = ""


class DialogueAnalyzerResult(BaseModel):
    active_domain: Literal["phq", "gad", "mixed", "safety"] = "mixed"
    domain_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    stay_in_domain: bool = True
    user_intents: List[str] = Field(default_factory=list)
    evidence_updates: List[DialogueAnalyzerEvidence] = Field(default_factory=list)
    scene_candidates: List[str] = Field(default_factory=list)
    blocked_pivots: List[str] = Field(default_factory=list)
    negations: List[str] = Field(default_factory=list)
    safety: DialogueAnalyzerSafety = Field(default_factory=DialogueAnalyzerSafety)


class DialoguePlan(BaseModel):
    stage: DialogueStage = "rapport"
    next_action: DialogueAction = "open_question"
    current_topic: str = "rapport"
    target_topic: str = "rapport"
    active_domain: DomainTrack = "rapport"
    domain_locked: bool = False
    target_item: Optional[str] = None
    target_scene: Optional[str] = None
    scene_item_ids: List[str] = Field(default_factory=list)
    closure_mode: bool = False
    rationale: str = ""
    user_turns: int = 0
    low_confidence_topics: List[str] = Field(default_factory=list)
    covered_topics: List[str] = Field(default_factory=list)
    held_back_items: List[str] = Field(default_factory=list)
    transition_hint: str = ""
    user_style: UserStyleProfile = Field(default_factory=UserStyleProfile)
    disclosure: DisclosureMetrics = Field(default_factory=DisclosureMetrics)
    readiness: ReadinessLevel = "opening"
    fatigue: FatigueLevel = "low"
    coverage_debt: List[str] = Field(default_factory=list)
    continue_intent: bool = False
    reopen_signal: bool = False
    summary_ready: bool = False
    reflective_anchor: str = ""
    continuity_note: str = ""
    recommended_nudges: List[str] = Field(default_factory=list)
    phq_queue: List[str] = Field(default_factory=list)
    gad_queue: List[str] = Field(default_factory=list)
    blocked_items: List[str] = Field(default_factory=list)
    recent_scenes: List[str] = Field(default_factory=list)
    recent_items: List[str] = Field(default_factory=list)


class CoveragePlan(BaseModel):
    total_items: int
    touched_items: int
    resolved_items: List[str] = Field(default_factory=list)
    partial_items: List[str] = Field(default_factory=list)
    contradicted_items: List[str] = Field(default_factory=list)
    abstained_items: List[str] = Field(default_factory=list)
    unresolved_items: List[str] = Field(default_factory=list)
    review_items: List[str] = Field(default_factory=list)
    next_items: List[str] = Field(default_factory=list)
    completion_ratio: float = Field(ge=0.0, le=1.0)
    review_required: bool = False
    topic_states: List[TopicState] = Field(default_factory=list)
    dialogue: DialoguePlan = Field(default_factory=DialoguePlan)


class ScreeningSnapshot(BaseModel):
    language: LanguageCode
    items: Dict[str, ItemScore]
    evidence_spans: List[EvidenceSpan]
    unresolved_items: List[str]
    totals: Dict[str, Optional[int]]
    safety: SafetyFlag
    coverage: CoveragePlan
    mode: Literal["heuristic", "hybrid"] = "heuristic"


class UserProfileContext(BaseModel):
    preferred_name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=1, le=120)
    occupation: Optional[str] = None
    living_situation: Optional[str] = None
    support_system: Optional[str] = None
    context_note: Optional[str] = None
    recent_checkins: List[Dict[str, object]] = Field(default_factory=list)


class NudgeEvent(BaseModel):
    nudge_id: str
    strategy: str
    title: Optional[str] = None
    turn_id: Optional[int] = None
    words_added: int = 0
    evidence_gain: int = 0
    resolved_gain: int = 0
    outcome: NudgeOutcome = "unknown"


class ChatSession(BaseModel):
    session_id: str
    language: LanguageCode
    profile: UserProfileContext = Field(default_factory=UserProfileContext)
    turns: List[Turn] = Field(default_factory=list)
    asked_items: List[str] = Field(default_factory=list)
    domain_history: List[DomainTrack] = Field(default_factory=list)
    scene_history: List[str] = Field(default_factory=list)
    blocked_items: List[str] = Field(default_factory=list)
    nudge_events: List[NudgeEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StartSessionRequest(BaseModel):
    language: LanguageCode = "en"
    opening_note: Optional[str] = None
    profile: UserProfileContext = Field(default_factory=UserProfileContext)


class StartSessionResponse(BaseModel):
    session_id: str
    assistant_turn: Turn


class ChatTurnRequest(BaseModel):
    text: str = Field(min_length=1)
    nudge_id: Optional[str] = None
    nudge_strategy: Optional[str] = None
    nudge_title: Optional[str] = None
    from_voice: bool = False


class ChatTurnResponse(BaseModel):
    session_id: str
    assistant_turn: Turn
    snapshot: ScreeningSnapshot
    summary: Optional[str] = None
    rows: List[dict] = Field(default_factory=list)


class SessionDetailResponse(BaseModel):
    session_id: str
    profile: UserProfileContext = Field(default_factory=UserProfileContext)
    turns: List[Turn]
    snapshot: ScreeningSnapshot


class TranscriptScoreRequest(BaseModel):
    language: LanguageCode
    turns: List[Turn]


class AsyncTranscriptScoreRequest(TranscriptScoreRequest):
    label: Optional[str] = None
    session_id: Optional[str] = None
    use_llm: bool = True


class AsyncScoreJob(BaseModel):
    request_id: str
    status: AsyncScoreStatus = "pending"
    language: LanguageCode
    turn_count: int = 0
    use_llm: bool = True
    label: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class AsyncScoreResponse(BaseModel):
    job: AsyncScoreJob
    result: Optional[dict] = None


class SummaryResponse(BaseModel):
    session_id: str
    summary: str
    snapshot: ScreeningSnapshot


class SummaryRow(BaseModel):
    item_id: str
    questionnaire: Literal["PHQ9", "GAD7"]
    label: str
    value: Optional[int]
    status: ItemStatus
    confidence: float
    source: Literal["none", "heuristic", "llm", "hybrid"]
    evidence_quotes: List[str] = Field(default_factory=list)


class SessionExportResponse(BaseModel):
    session_id: str
    language: LanguageCode
    profile: UserProfileContext = Field(default_factory=UserProfileContext)
    summary: str
    turns: List[Turn]
    snapshot: ScreeningSnapshot
    rows: List[SummaryRow]
