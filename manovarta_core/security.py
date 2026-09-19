from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    """Small process-local guardrail for unauthenticated public Cloud Run routes.

    Cloud Armor or an API gateway should be used for fleet-wide enforcement. This
    guard prevents a single hot instance from becoming an unbounded LLM/voice bill.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = monotonic()
        with self._lock:
            events = self._events[key]
            cutoff = now - window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=max(1, int(window_seconds - (now - events[0])) + 1),
                )
            events.append(now)
            return RateLimitDecision(allowed=True)
