from __future__ import annotations

from typing import Dict, Optional
from uuid import uuid4

from manovarta_core.schemas import ChatSession, Turn, UserProfileContext


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, ChatSession] = {}

    def create(self, language: str, profile: UserProfileContext | None = None) -> ChatSession:
        session = ChatSession(
            session_id=f"mv-{uuid4().hex[:10]}",
            language=language,
            profile=profile or UserProfileContext(),
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def add_turn(self, session_id: str, speaker: str, text: str, language: str, notes: str = None) -> Turn:
        session = self._sessions[session_id]
        turn = Turn(
            turn_id=len(session.turns) + 1,
            speaker=speaker,
            text=text,
            language_tag=language,
            notes=notes,
        )
        session.turns.append(turn)
        return turn

    def size(self) -> int:
        return len(self._sessions)
