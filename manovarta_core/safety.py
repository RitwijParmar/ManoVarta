from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from manovarta_core.schemas import SafetyFlag, Turn
from manovarta_core.text import contains_phrase, extract_window, normalize_text


URGENT_INTENT_CUES = (
    "kill myself",
    "end my life",
    "want to die",
    "don't want to live",
    "do not want to live",
    "suicidal",
    "suicide",
    "hurt myself",
    "harm myself",
    "cut myself",
    "self harm",
    "overdose",
    "take all the pills",
    "jump off",
    "hang myself",
    "want to disappear forever",
    "i should not wake up",
    "i wish i would not wake up",
    "mar jana chahta",
    "marna chahta",
    "jeena nahi hai",
    "khud ko nuksan",
    "khatam kar doon",
    "sab khatam kar doon",
    "sab khatam kar du",
    "apne aap ko maar",
    "khud ko maar",
    "gayab ho jaun hamesha ke liye",
    "दवाइयाँ एक साथ खा लूँ",
    "सब खत्म कर दूँ",
    "सब खत्म कर दू",
    "खुद को नुकसान",
)

URGENT_INTENT_PATTERNS = (
    r"\bi\s+wish\s+i\s+(?:could\s+)?sleep\s+and\s+not\s+wake\s+up\b",
    r"\bi\s+(?:wish|keep\s+wishing|sometimes\s+think|sometimes\s+feel)\s+(?:that\s+)?i\s+(?:would\s+)?not\s+wake\s+up\b",
    r"\b(?:it|things|life)\s+(?:might|may|would)\s+be\s+easier\s+(?:if\s+)?i\s+(?:did\s+not|didn\s+t|do\s+not|don\s+t|would\s+not|wouldn\s+t)\s+wake\s+up\b",
    r"\b(?:better|easier)\s+(?:if\s+)?i\s+(?:did\s+not|didn\s+t|do\s+not|don\s+t)\s+wake\s+up\b",
    r"\bkaash\s+main\s+(?:subah\s+)?na\s+uthu[nm]?\b",
    r"\b(?:agar|shayad)\s+main\s+(?:subah\s+)?na\s+uthu[nm]?\b",
    r"काश\s+मैं\s+(?:सुबह\s+)?न\s+उठूँ",
    r"अगर\s+मैं\s+(?:सुबह\s+)?न\s+उठूँ",
)

URGENT_METHOD_CUES = (
    "take all the pills",
    "all the pills",
    "all my pills",
    "dawaiyan ek sath kha",
    "दवाइयाँ एक साथ",
    "blade se kaat",
    "fan se latak",
    "train ke aage",
    "bridge se",
    "bridge se kud",
    "poison myself",
    "zeher kha",
)

URGENT_TIME_CUES = (
    "tonight",
    "right now",
    "today",
    "abhi",
    "aaj raat",
    "kal raat",
    "plan",
    "planned",
)

REVIEW_CUES = (
    "no point",
    "hopeless",
    "numb all the time",
    "nothing matters",
    "i wish i could vanish",
    "i want to disappear",
    "i should just disappear",
    "people would be better without me",
    "better off without me around",
    "everyone would have an easier life",
    "easier life without me",
    "i am a burden",
    "no one would notice",
    "i am done with everything",
    "sab bekaar lagta",
    "ummeed nahi lagti",
    "gayab ho jaun",
    "gayab ho jana chahta",
    "bojh lagta hoon",
    "mere bina sab theek hoga",
    "kahin nikal jaun",
    "जहाँ कोई मुझे जानता ही न हो",
    "jeene ka mann nahi",
)

PROTECTIVE_CUES = (
    "not suicidal",
    "i am not suicidal",
    "i will not hurt myself",
    "i won't hurt myself",
    "i do not plan to hurt myself",
    "main khud ko nuksan nahi pahunchana chahta",
    "main aisa kuch nahi karunga",
)


@dataclass(frozen=True)
class CueHit:
    phrase: str
    snippet: str
    recent: bool


class SafetyMonitor:
    def assess(self, turns: Iterable[Turn]) -> SafetyFlag:
        user_turns = [turn for turn in turns if turn.speaker == "user"]
        if not user_turns:
            return SafetyFlag()

        recent_turns = user_turns[-3:]
        all_text = "\n".join(turn.text for turn in user_turns)
        recent_text = "\n".join(turn.text for turn in recent_turns)

        urgent_hits = self._dedupe_hits(
            self._collect_hits(all_text, recent_text, URGENT_INTENT_CUES)
            + self._collect_pattern_hits(all_text, recent_text, URGENT_INTENT_PATTERNS)
        )
        method_hits = self._collect_hits(all_text, recent_text, URGENT_METHOD_CUES)
        time_hits = self._collect_hits(all_text, recent_text, URGENT_TIME_CUES)
        review_hits = self._collect_hits(all_text, recent_text, REVIEW_CUES)
        protective_hits = self._collect_hits(all_text, recent_text, PROTECTIVE_CUES)

        if urgent_hits:
            direct_hits = [hit for hit in urgent_hits if hit.recent]
            if direct_hits or method_hits or time_hits:
                return self._build_flag(
                    "urgent",
                    direct_hits or urgent_hits[:3],
                    "Direct or recent self-harm language detected.",
                )
            if not protective_hits:
                return self._build_flag(
                    "review",
                    urgent_hits[:3],
                    "Historic or indirect self-harm language detected.",
                )

        if method_hits and (time_hits or review_hits):
            return self._build_flag(
                "urgent",
                (method_hits + time_hits + review_hits)[:4],
                "Method-focused risk language detected with escalation context.",
            )

        if review_hits:
            if len(review_hits) >= 2 or any(hit.recent for hit in review_hits):
                return self._build_flag(
                    "review",
                    review_hits[:4],
                    "Escalation-sensitive hopelessness or disappearance language detected.",
                )

        if method_hits:
            return self._build_flag(
                "review",
                method_hits[:3],
                "Potential self-harm method language detected for review.",
            )

        return SafetyFlag()

    def _collect_hits(self, all_text: str, recent_text: str, phrases: Sequence[str]) -> List[CueHit]:
        hits: List[CueHit] = []
        normalized_all = normalize_text(all_text)
        normalized_recent = normalize_text(recent_text)
        for phrase in phrases:
            normalized_phrase = normalize_text(phrase)
            if not contains_phrase(normalized_all, normalized_phrase, pre_normalized=True):
                continue
            snippet = extract_window(all_text, phrase, radius=40)
            hits.append(
                CueHit(
                    phrase=phrase,
                    snippet=snippet,
                    recent=contains_phrase(normalized_recent, normalized_phrase, pre_normalized=True),
                )
            )
        return hits

    def _collect_pattern_hits(self, all_text: str, recent_text: str, patterns: Sequence[str]) -> List[CueHit]:
        hits: List[CueHit] = []
        normalized_all = normalize_text(all_text)
        normalized_recent = normalize_text(recent_text)
        for pattern in patterns:
            for match in re.finditer(pattern, normalized_all):
                phrase = match.group(0).strip()
                if not phrase:
                    continue
                hits.append(
                    CueHit(
                        phrase=phrase,
                        snippet=phrase,
                        recent=bool(re.search(pattern, normalized_recent)),
                    )
                )
        return hits

    def _dedupe_hits(self, hits: Sequence[CueHit]) -> List[CueHit]:
        deduped: List[CueHit] = []
        seen: set[tuple[str, str, bool]] = set()
        for hit in hits:
            key = (hit.phrase, hit.snippet, hit.recent)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(hit)
        return deduped

    def _build_flag(self, level: str, hits: Sequence[CueHit], rationale: str) -> SafetyFlag:
        cues = list(dict.fromkeys(hit.snippet or hit.phrase for hit in hits))
        return SafetyFlag(
            level=level,
            cues=cues,
            rationale=rationale,
            needs_human_review=level in {"review", "urgent"},
        )
