from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from threading import RLock
from typing import Dict, Optional
from uuid import uuid4

from manovarta_core.schemas import ChatSession, Turn, UserProfileContext


class SessionStore:
    def __init__(self, *, ttl_seconds: int = 1800, max_sessions: int = 200) -> None:
        self._sessions: Dict[str, ChatSession] = {}
        self._locks: Dict[str, RLock] = {}
        self._ttl_seconds = max(300, ttl_seconds)
        self._max_sessions = max(10, max_sessions)

    def create(self, language: str, profile: UserProfileContext | None = None) -> ChatSession:
        self._prune_expired()
        if len(self._sessions) >= self._max_sessions:
            self._evict_oldest()
        now = datetime.now(timezone.utc)
        session = ChatSession(
            session_id=f"mv-{uuid4().hex}",
            language=language,
            profile=profile or UserProfileContext(),
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
            access_token=token_urlsafe(32),
        )
        self._sessions[session.session_id] = session
        self._locks[session.session_id] = RLock()
        return session

    def get(self, session_id: str) -> Optional[ChatSession]:
        self._prune_expired()
        return self._sessions.get(session_id)

    def get_by_access_token(self, access_token: str) -> Optional[ChatSession]:
        self._prune_expired()
        return next((session for session in self._sessions.values() if session.access_token == access_token), None)

    @contextmanager
    def locked(self, session_id: str):
        lock = self._locks.get(session_id)
        if lock is None:
            raise KeyError(session_id)
        lock.acquire()
        try:
            yield self._sessions[session_id]
            self._touch(self._sessions[session_id])
        finally:
            lock.release()

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
        self._touch(session)
        return turn

    def size(self) -> int:
        self._prune_expired()
        return len(self._sessions)

    def _touch(self, session: ChatSession) -> None:
        now = datetime.now(timezone.utc)
        session.updated_at = now
        session.expires_at = now + timedelta(seconds=self._ttl_seconds)

    def _prune_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired_ids = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_at is not None
            and (session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)) <= now
        ]
        for session_id in expired_ids:
            self._sessions.pop(session_id, None)
            self._locks.pop(session_id, None)

    def _evict_oldest(self) -> None:
        if not self._sessions:
            return
        oldest_id = min(
            self._sessions,
            key=lambda session_id: self._sessions[session_id].updated_at,
        )
        self._sessions.pop(oldest_id, None)
        self._locks.pop(oldest_id, None)
