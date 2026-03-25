from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Speaker = Literal["assistant", "user"]
LanguageCode = Literal["en", "hi", "hinglish"]
SafetyLevel = Literal["none", "review", "urgent"]
ItemStatus = Literal["resolved", "partial", "contradicted", "unresolved"]


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


class SafetyFlag(BaseModel):
    level: SafetyLevel = "none"
    cues: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    needs_human_review: bool = False


class ScreeningSnapshot(BaseModel):
    language: LanguageCode
    items: Dict[str, ItemScore]
    evidence_spans: List[EvidenceSpan]
    unresolved_items: List[str]
    totals: Dict[str, Optional[int]]
    safety: SafetyFlag
    mode: Literal["heuristic", "hybrid"] = "heuristic"


class ChatSession(BaseModel):
    session_id: str
    language: LanguageCode
    turns: List[Turn] = Field(default_factory=list)
    asked_items: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StartSessionRequest(BaseModel):
    language: LanguageCode = "en"
    opening_note: Optional[str] = None


class StartSessionResponse(BaseModel):
    session_id: str
    assistant_turn: Turn


class ChatTurnRequest(BaseModel):
    text: str = Field(min_length=1)


class ChatTurnResponse(BaseModel):
    session_id: str
    assistant_turn: Turn
    snapshot: ScreeningSnapshot


class SessionDetailResponse(BaseModel):
    session_id: str
    turns: List[Turn]
    snapshot: ScreeningSnapshot


class TranscriptScoreRequest(BaseModel):
    language: LanguageCode
    turns: List[Turn]


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
    summary: str
    turns: List[Turn]
    snapshot: ScreeningSnapshot
    rows: List[SummaryRow]
