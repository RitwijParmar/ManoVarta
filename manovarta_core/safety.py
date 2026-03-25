from typing import Iterable, List

from manovarta_core.schemas import SafetyFlag, Turn
from manovarta_core.text import contains_any


URGENT_CUES = (
    "kill myself",
    "end my life",
    "hurt myself",
    "don't want to live",
    "want to disappear forever",
    "mar jana chahta",
    "khatam kar doon",
    "jeena nahi hai",
)

REVIEW_CUES = (
    "no point",
    "hopeless",
    "numb all the time",
    "nothing matters",
    "i wish i could vanish",
    "sab bekaar lagta",
    "ummeed nahi lagti",
    "gayab ho jaun",
    "gayab ho jana chahta",
)


class SafetyMonitor:
    def assess(self, turns: Iterable[Turn]) -> SafetyFlag:
        user_text = " ".join(turn.text for turn in turns if turn.speaker == "user")
        urgent_hits = self._collect_hits(user_text, URGENT_CUES)
        if urgent_hits:
            return SafetyFlag(
                level="urgent",
                cues=urgent_hits,
                rationale="Direct self-harm or suicidal language detected.",
                needs_human_review=True,
            )

        review_hits = self._collect_hits(user_text, REVIEW_CUES)
        if review_hits:
            return SafetyFlag(
                level="review",
                cues=review_hits,
                rationale="Escalation-sensitive language detected.",
                needs_human_review=True,
            )

        return SafetyFlag()

    def _collect_hits(self, text: str, phrases: Iterable[str]) -> List[str]:
        return [phrase for phrase in phrases if contains_any(text, [phrase])]
