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
    "jeene ki ichha khatam",
    "jiine ki ichha khatam",
    "जीने की इच्छा खत्म",
    "जीने का मन खत्म",
    "कुछ समय के लिए गायब हो जाऊँ",
    "काश मैं कुछ समय के लिए गायब हो जाऊँ",
    "बोझ हूँ",
)

REVIEW_PATTERNS = (
    r"\bi\s+wish\s+i\s+could\s+disappear(?:\s+for\s+a\s+while)?\b",
    r"\bi\s+want\s+to\s+disappear(?:\s+for\s+a\s+while)?\b",
    r"\b(?:sometimes\s+)?i\s+(?:feel|think)\s+like\s+not\s+being\s+here\s+would\s+be\s+easier\b",
    r"\bnot\s+being\s+here\s+would\s+be\s+easier\b",
    r"\bi\s+feel\s+like\s+i\s+am\s+(?:such\s+an?\s+|an?\s+extra\s+)?burden\b",
    r"\bthodi\s+der\s+ke\s+liye\s+gayab\s+ho\s+ja(?:u|un|oon)\b",
    r"\bextra\s+burden\s+hoon\b",
    r"\bjee?ne\s+ki\s+ichha\s+khatam\s+ho\s+rah(?:i|a)\b",
    r"जीने\s+की\s+इच्छा\s+खत्म\s+हो\s+रह(?:ी|ा)",
    r"जीने\s+का\s+मन\s+खत्म\s+हो\s+रह(?:ी|ा)",
)

PROTECTIVE_CUES = (
    "not suicidal",
    "i am not suicidal",
    "i will not hurt myself",
    "i won't hurt myself",
    "i do not plan to hurt myself",
    "i do not want to hurt myself",
    "i do not want to hurt myself or do anything to myself",
    "i do not want to do anything to myself",
    "i am not thinking about hurting myself",
    "i am not thinking about harming myself",
    "i have not had thoughts of hurting myself or not wanting to be alive",
    "i have not had thoughts of hurting myself or of not wanting to be alive",
    "main khud ko nuksan nahi pahunchana chahta",
    "main aisa kuch nahi karunga",
    "khud ko nuksan pahunchane ka mann nahi hai",
    "khud ko nuksan pahunchane ka man nahi hai",
    "khud ko नुकसान पहुंचाने का मन नहीं है",
    "khud ko नुकसान पहुंचाने या मरने जैसा कुछ नहीं सोच रहा",
    "khud ko नुकसान पहुंचाने ya marne jaisa kuch nahi soch raha",
    "khud ko नुकसान पहुंचाने ya marne jaisa kuch nahi soch rahi",
    "खुद को नुकसान पहुँचाने जैसा कुछ नहीं सोच रहा",
    "खुद को नुकसान पहुँचाने जैसा कुछ नहीं सोच रही",
    "खुद को नुकसान पहुंचाने जैसा कुछ नहीं सोच रहा",
    "खुद को नुकसान पहुंचाने जैसा कुछ नहीं सोच रही",
    "marne jaisa kuch nahi soch raha",
    "marne jaisa kuch nahi soch rahi",
    "mujhe hurt karne ka plan nahi hai",
    "mujhe harm karne ka plan nahi hai",
    "khud ko hurt karne ka koi plan ya wish nahi hai",
    "khud ko harm karne ka koi plan ya wish nahi hai",
)

PROTECTIVE_NEGATION_PATTERNS = (
    r"\bi\s+have\s+not\s+had\s+thoughts\s+of\s+(?:hurting|harming)\s+myself\s+or\s+(?:of\s+)?not\s+wanting\s+to\s+be\s+alive\b",
    r"\b(?:do\s+not|don't|dont|did\s+not|didn't|would\s+not|wouldn't|won't|will\s+not|never|not)\b.{0,36}\b(?:hurt\s+myself|harm\s+myself|kill\s+myself|end\s+my\s+life|want\s+to\s+die|suicidal|suicide|not\s+want\s+to\s+live|not\s+be\s+alive)\b",
    r"\bi\s+do\s+not\s+want\s+to\s+(?:hurt\s+myself|harm\s+myself)(?:\s+or\s+do\s+anything\s+to\s+myself)?\b",
    r"\bi\s+am\s+not\s+thinking\s+about\s+(?:hurting|harming)\s+myself\b",
    r"\bi\s+would\s+not\s+say\s+i\s+(?:want|wanted)\s+to\s+(?:hurt\s+myself|harm\s+myself|kill\s+myself|die)\b",
    r"\bmain\s+(?:aisa|yeh)\s+kuch\s+nahi\s+kar(?:unga|ungi|na)\b",
    r"\bmain\s+khud\s+ko\s+nuksan\s+nahi\b",
    r"\bkhud\s+ko\s+nuksan\s+pahunchane\s+ka\s+mann?\s+nahi\s+hai\b",
    r"\bkhud\s+ko\s+nuksan\s+pahunchane(?:\s+ya\s+marne)?\s+jaisa\s+kuch\s+nahi\s+soch\s+rah(?:a|i)\b",
    r"\bmarne\s+jaisa\s+kuch\s+nahi\s+soch\s+rah(?:a|i)\b",
    r"\bmujhe\s+(?:khud\s+ko\s+)?(?:hurt|harm)\s+karne\s+ka\s+plan\s+nahi\s+hai\b",
    r"\bkhud\s+ko\s+(?:hurt|harm)\s+karne\s+ka\s+koi\s+(?:plan|wish)\s+nahi\s+hai\b",
    r"खुद\s+को\s+नुकसान\s+पहुंचाने\s+जैसा\s+कुछ\s+नहीं\s+सोच\s+रह(?:ा|ी)",
    r"खुद\s+को\s+नुकसान\s+पहुँचाने\s+जैसा\s+कुछ\s+नहीं\s+सोच\s+रह(?:ा|ी)",
    r"खुद\s+को\s+नुकसान\s+पहुंचाने\s+का\s+मन\s+नहीं\s+है",
    r"खुद\s+को\s+नुकसान\s+पहुंचाने\s+या\s+मरने\s+जैसा\s+कुछ\s+नहीं\s+सोच\s+रह(?:ा|ी)",
    r"मुझे\s+(?:खुद\s+को\s+)?(?:हर्ट|हार्म)\s+करने\s+का\s+प्लान\s+नहीं\s+है",
    r"नहीं.{0,64}खुद\s+को\s+hurt",
    r"खुद\s+को\s+hurt.{0,64}नहीं",
    r"ज़िंदा\s+न\s+रहने.{0,64}नहीं",
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
        urgent_hits = self._filter_negated_hits(urgent_hits)
        method_hits = self._collect_hits(all_text, recent_text, URGENT_METHOD_CUES)
        time_hits = self._collect_hits(all_text, recent_text, URGENT_TIME_CUES)
        review_hits = self._dedupe_hits(
            self._collect_hits(all_text, recent_text, REVIEW_CUES)
            + self._collect_pattern_hits(all_text, recent_text, REVIEW_PATTERNS)
        )
        review_hits = self._filter_negated_hits(review_hits)
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

    def _filter_negated_hits(self, hits: Sequence[CueHit]) -> List[CueHit]:
        return [hit for hit in hits if not self._hit_is_negated(hit)]

    def _hit_is_negated(self, hit: CueHit) -> bool:
        normalized = normalize_text(hit.snippet or hit.phrase)
        if not normalized:
            return False
        if any(cue in normalized for cue in (normalize_text(cue) for cue in PROTECTIVE_CUES)):
            return True
        direct_negated_patterns = (
            ("khud ko nuksan", ("nahi soch", "plan nahi", "wish nahi", "mann nahi", "man nahi")),
            ("hurt myself", ("do not", "dont", "don't", "not", "no plan", "no wish")),
            ("harm myself", ("do not", "dont", "don't", "not", "no plan", "no wish")),
            ("kill myself", ("do not", "dont", "don't", "not")),
            ("marne", ("nahi soch",)),
        )
        for cue, negations in direct_negated_patterns:
            if cue in normalized and any(negation in normalized for negation in negations):
                return True
        return any(re.search(pattern, normalized) for pattern in PROTECTIVE_NEGATION_PATTERNS)

    def _build_flag(self, level: str, hits: Sequence[CueHit], rationale: str) -> SafetyFlag:
        cues = list(dict.fromkeys(hit.snippet or hit.phrase for hit in hits))
        return SafetyFlag(
            level=level,
            cues=cues,
            rationale=rationale,
            needs_human_review=level in {"review", "urgent"},
        )
