from __future__ import annotations

from collections import defaultdict
import re
from typing import Dict, Iterable, List, Optional, Tuple

from manovarta_core.lexicon import HIGH_INTENSITY_CUES, LOW_INTENSITY_CUES, NEGATION_CUES, RULES, UNCERTAINTY_CUES
from manovarta_core.questionnaires import ITEM_INDEX, all_items
from manovarta_core.schemas import CoveragePlan, EvidenceSpan, ItemScore, ScreeningSnapshot, Turn
from manovarta_core.safety import PROTECTIVE_NEGATION_PATTERNS
from manovarta_core.text import extract_window, normalize_text

GENERIC_MOOD_OPENING_CUES: Tuple[str, ...] = (
    "low aur disconnected feel ho raha hai",
    "low aur disconnected feel ho rahi hai",
    "kaafi time se low aur disconnected feel ho raha hai",
    "kaafi time se low aur disconnected feel ho rahi hai",
    "feel low and disconnected",
    "feeling low and disconnected",
    "feel numb and disconnected",
    "feeling numb and disconnected",
    "numb and disconnected lately",
)

CONTRAST_PRESENT_CUES: Tuple[str, ...] = (
    "but",
    "more like",
    "rather",
    "instead",
    "bas",
    "lekin",
    "par",
    "zyada",
    "ज़्यादा",
    "ज्यादा",
    "mostly",
)

SCENE_COHORTS: Dict[str, Tuple[str, ...]] = {
    "phq_q1_anhedonia": ("phq_q2_low_mood", "phq_q6_worthlessness"),
    "phq_q2_low_mood": ("phq_q1_anhedonia", "phq_q6_worthlessness"),
    "phq_q6_worthlessness": ("phq_q1_anhedonia", "phq_q2_low_mood"),
    "phq_q3_sleep": ("phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"),
    "phq_q4_fatigue": ("phq_q3_sleep", "phq_q5_appetite", "phq_q7_concentration", "phq_q8_psychomotor"),
    "phq_q5_appetite": ("phq_q3_sleep", "phq_q4_fatigue", "phq_q7_concentration", "phq_q8_psychomotor"),
    "phq_q7_concentration": ("phq_q3_sleep", "phq_q4_fatigue", "phq_q5_appetite", "phq_q8_psychomotor"),
    "phq_q8_psychomotor": ("phq_q3_sleep", "phq_q4_fatigue", "phq_q5_appetite", "phq_q7_concentration"),
    "gad_q1_nervous": ("gad_q2_control_worry", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"),
    "gad_q2_control_worry": ("gad_q1_nervous", "gad_q3_excessive_worry", "gad_q4_trouble_relaxing"),
    "gad_q3_excessive_worry": ("gad_q1_nervous", "gad_q2_control_worry", "gad_q7_afraid"),
    "gad_q4_trouble_relaxing": ("gad_q1_nervous", "gad_q2_control_worry", "gad_q5_restlessness"),
    "gad_q5_restlessness": ("gad_q4_trouble_relaxing", "gad_q6_irritability", "gad_q7_afraid"),
    "gad_q6_irritability": ("gad_q4_trouble_relaxing", "gad_q5_restlessness", "gad_q7_afraid"),
    "gad_q7_afraid": ("gad_q3_excessive_worry", "gad_q5_restlessness", "gad_q6_irritability"),
}

SLEEP_PROMPT_MARKERS: Tuple[str, ...] = (
    "so ne ki shuruat",
    "सोने की शुरुआत",
    "सोने में परेशानी",
    "नींद आने में मुश्किल",
    "sleep mostly been hard to start",
    "hard to fall asleep",
    "sleeping more than usual",
    "ज़रूरत से ज़्यादा सो",
    "जरूरत से ज्यादा सो",
    "ज़्यादा सो रहे",
)
SLEEP_FREQUENCY_PROMPT_MARKERS: Tuple[str, ...] = (
    "हर रोज़",
    "हर रोज",
    "हफ्ते में",
    "week",
    "nights a week",
    "every day",
    "almost every day",
)
FOCUS_PROMPT_MARKERS: Tuple[str, ...] = (
    "ध्यान लगाने",
    "ध्यान",
    "फोकस",
    "focus",
    "concentrat",
)
FATIGUE_PROMPT_MARKERS: Tuple[str, ...] = (
    "थकान",
    "ऊर्जा की कमी",
    "कमज़ोरी",
    "कमजोरी",
    "low energy",
    "fatigue",
    "heavyness",
    "body heavy",
)
NERVOUS_PROMPT_MARKERS: Tuple[str, ...] = (
    "घबराया हुआ",
    "घबराए हुए",
    "नर्वस",
    "nervous",
    "घबराहट",
)
CONTROL_WORRY_PROMPT_MARKERS: Tuple[str, ...] = (
    "कंट्रोल",
    "काबू",
    "रोक पाते",
    "रोक पाती",
    "control",
    "stop worrying",
    "बस में",
)
EXCESSIVE_WORRY_PROMPT_MARKERS: Tuple[str, ...] = (
    "ज़रूरत से ज़्यादा चिंता",
    "जरूरत से ज्यादा चिंता",
    "excessive worry",
    "कई छोटी-बड़ी बातें",
    "छोटी-बड़ी बातें",
    "कई छोटी बड़ी बातें",
    "future",
    "भविष्य",
    "रोज़मर्रा",
    "रोजमर्रा",
)
RELAX_PROMPT_MARKERS: Tuple[str, ...] = (
    "रिलैक्स",
    "आराम नहीं दे",
    "आराम नहीं दे पा",
    "शांत होकर बैठ",
    "relax",
    "calm down",
    "switch off",
)
APPETITE_PROMPT_MARKERS: Tuple[str, ...] = (
    "भूख",
    "खा पा रहे",
    "खाना",
    "meals",
    "appetite",
)
PSYCHOMOTOR_PROMPT_MARKERS: Tuple[str, ...] = (
    "धीरे चलने",
    "धीरे बोलने",
    "रफ्तार",
    "बेचैन",
    "छटपटाहट",
    "restless",
    "restlessness",
)
MOOD_PROMPT_MARKERS: Tuple[str, ...] = (
    "उदासी",
    "low mood",
    "mood",
    "कमी या बोझ",
    "बोझ",
    "worthless",
)
ANHEDONIA_PROMPT_MARKERS: Tuple[str, ...] = (
    "दिलचस्पी कम",
    "शुरू करने की हिम्मत",
    "मन नहीं",
    "interest",
    "start them",
)
YES_NO_AFFIRMATIONS: Tuple[str, ...] = (
    "haan",
    "हाँ",
    "हां",
    "haan ji",
    "yes",
    "yep",
    "हो रही",
    "होता है",
    "होती है",
    "हो रहा है",
    "हो रहा",
    "हो रही है",
    "मुश्किल होती",
    "दोनों",
    "भटक जाता",
    "काफी ज्यादा",
    "रहता हूं",
    "रहती हूं",
    "रहता है",
    "रहती है",
    "रोज बनी है",
    "रोज बनी रही",
    "हमेशा",
)
FREQUENT_SEVERITY_MARKERS: Tuple[str, ...] = (
    "हर रोज",
    "हर रोज़",
    "रोज",
    "every day",
    "daily",
    "almost every day",
    "कई घंटे",
    "आधे दिन",
    "half day",
    "most days",
)
NEGATING_RESPONSE_MARKERS: Tuple[str, ...] = (
    "नहीं",
    "nahin",
    "nahi",
    "not really",
    "no",
    "none",
)
INABILITY_AFFIRMATION_MARKERS: Tuple[str, ...] = (
    "नहीं हो पाती",
    "नहीं हो पाता",
    "नहीं कर पाता",
    "नहीं कर पाती",
    "नहीं दे पाता",
    "नहीं दे पाती",
    "नहीं रहती",
    "काबू में नहीं",
    "बस में नहीं",
    "नहीं टिकता",
    "नहीं टिकती",
    "not able to",
    "cannot",
    "can't",
    "hard to",
)


class ConversationScorer:
    def analyze(self, turns: Iterable[Turn], language: str, safety_flag) -> ScreeningSnapshot:
        turn_list = list(turns)
        evidence_spans = self._collect_evidence(turn_list)
        items = self._build_item_scores(evidence_spans)
        coverage = self.build_coverage(items)
        unresolved_items = coverage.unresolved_items + coverage.partial_items + coverage.contradicted_items + coverage.abstained_items
        totals = self._build_totals(items)
        return ScreeningSnapshot(
            language=language,
            items=items,
            evidence_spans=evidence_spans,
            unresolved_items=unresolved_items,
            totals=totals,
            safety=safety_flag,
            coverage=coverage,
        )

    def _collect_evidence(self, turns: List[Turn]) -> List[EvidenceSpan]:
        spans: List[EvidenceSpan] = []
        seen_keys = set()
        user_turns = [turn for turn in turns if turn.speaker == "user"]
        for turn in user_turns:
            normalized = normalize_text(turn.text)
            for rule in RULES:
                phrase = self._match_phrase(normalized, rule.phrases)
                if not phrase:
                    continue
                local_window = self._local_window(normalized, phrase)
                span_key = (turn.turn_id, rule.item_id, phrase)
                if span_key in seen_keys:
                    continue
                seen_keys.add(span_key)
                polarity = self._resolve_polarity(normalized, phrase, local_window)
                if rule.item_id == "phq_q9_self_harm" and self._is_protective_self_harm_denial(normalized):
                    polarity = "absent"
                score_hint = self._resolve_score(rule.score_hint, local_window, polarity)
                spans.append(
                    EvidenceSpan(
                        span_id=f"EV-{turn.turn_id}-{len(spans) + 1}",
                        questionnaire=rule.questionnaire,
                        item_id=rule.item_id,
                        turn_id=turn.turn_id,
                        text_span=extract_window(turn.text, phrase),
                        polarity=polarity,
                        score_hint=score_hint,
                        rationale=rule.rationale,
                    )
                )
        spans.extend(self._collect_contextual_evidence(turns, seen_keys))
        return spans

    def _collect_contextual_evidence(self, turns: List[Turn], seen_keys: set[tuple]) -> List[EvidenceSpan]:
        spans: List[EvidenceSpan] = []
        for index, turn in enumerate(turns):
            if turn.speaker != "user":
                continue
            prev_assistant = self._previous_assistant_question(turns, index)
            if prev_assistant is None:
                continue
            answer = normalize_text(turn.text)
            question = normalize_text(prev_assistant.text)
            if not self._is_contextual_affirmation(answer):
                continue

            def add(item_id: str, score_hint: int, rationale: str) -> None:
                span_key = (turn.turn_id, item_id, "contextual")
                if span_key in seen_keys:
                    return
                seen_keys.add(span_key)
                spans.append(
                    EvidenceSpan(
                        span_id=f"EV-{turn.turn_id}-CTX-{len(spans) + 1}",
                        questionnaire=ITEM_INDEX[item_id].questionnaire,
                        item_id=item_id,
                        turn_id=turn.turn_id,
                        text_span=turn.text,
                        polarity="present",
                        score_hint=score_hint,
                        rationale=rationale,
                    )
                )

            if self._contains_any(question, SLEEP_PROMPT_MARKERS):
                add(
                    "phq_q3_sleep",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of a direct sleep-pattern question.",
                )
            if self._contains_any(question, SLEEP_FREQUENCY_PROMPT_MARKERS):
                add(
                    "phq_q3_sleep",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of sleep frequency.",
                )
            if self._contains_any(question, FOCUS_PROMPT_MARKERS):
                add(
                    "phq_q7_concentration",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of a concentration question.",
                )
            if self._contains_any(question, FATIGUE_PROMPT_MARKERS):
                add(
                    "phq_q4_fatigue",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of fatigue or low-energy follow-up.",
                )
            if self._contains_any(question, NERVOUS_PROMPT_MARKERS):
                add(
                    "gad_q1_nervous",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of nervousness or feeling on edge.",
                )
            if self._contains_any(question, CONTROL_WORRY_PROMPT_MARKERS):
                add(
                    "gad_q2_control_worry",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of difficulty controlling worry.",
                )
            if self._contains_any(question, EXCESSIVE_WORRY_PROMPT_MARKERS):
                add(
                    "gad_q3_excessive_worry",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of excessive or wide-scope worry.",
                )
            if self._contains_any(question, RELAX_PROMPT_MARKERS):
                add(
                    "gad_q4_trouble_relaxing",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of not being able to relax or settle.",
                )
            if self._contains_any(question, APPETITE_PROMPT_MARKERS):
                add(
                    "phq_q5_appetite",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of appetite or eating-pattern change.",
                )
            if self._contains_any(question, PSYCHOMOTOR_PROMPT_MARKERS):
                severity = self._contextual_support_value(answer, default=2)
                add(
                    "phq_q8_psychomotor",
                    severity,
                    "Short answer interpreted in the context of slowed or keyed-up body pace.",
                )
                if self._contains_any(question, ("बेचैन", "छटपटाहट", "restless", "restlessness")):
                    add(
                        "gad_q5_restlessness",
                        severity,
                        "Short answer interpreted in the context of restlessness or agitation.",
                    )
            if self._contains_any(question, MOOD_PROMPT_MARKERS) and self._contains_any(answer, ("उदासी", "sad", "low", "mood")):
                add(
                    "phq_q2_low_mood",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of low-mood follow-up.",
                )
            if self._contains_any(question, MOOD_PROMPT_MARKERS) and self._contains_any(answer, ("बोझ", "कमी", "worthless", "burden", "guilty")):
                add(
                    "phq_q6_worthlessness",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of self-worth follow-up.",
                )
            if self._contains_any(question, ANHEDONIA_PROMPT_MARKERS):
                add(
                    "phq_q1_anhedonia",
                    self._contextual_support_value(answer, default=2),
                    "Short answer interpreted in the context of interest or getting-started difficulty.",
                )
        return spans

    def _previous_assistant_question(self, turns: List[Turn], user_index: int) -> Optional[Turn]:
        for back_index in range(user_index - 1, -1, -1):
            previous = turns[back_index]
            if previous.speaker != "assistant":
                continue
            if "?" in previous.text:
                return previous
            return None
        return None

    def _contains_any(self, text: str, markers: Tuple[str, ...]) -> bool:
        return any(normalize_text(marker) in text for marker in markers)

    def _is_contextual_affirmation(self, normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if any(re.search(pattern, normalized_text) for pattern in PROTECTIVE_NEGATION_PATTERNS):
            return False
        if self._contains_any(normalized_text, NEGATING_RESPONSE_MARKERS) and not self._contains_any(normalized_text, INABILITY_AFFIRMATION_MARKERS):
            return False
        if self._contains_any(normalized_text, INABILITY_AFFIRMATION_MARKERS):
            return True
        if self._contains_any(normalized_text, YES_NO_AFFIRMATIONS):
            return True
        return len(normalized_text.split()) <= 8

    def _contextual_support_value(self, normalized_text: str, *, default: int = 2) -> int:
        if self._contains_any(normalized_text, FREQUENT_SEVERITY_MARKERS):
            return 3
        if self._contains_any(normalized_text, ("कई", "often", "usually", "both", "दोनों", "अक्सर")):
            return max(default, 2)
        return default

    def _match_phrase(self, normalized_text: str, phrases: Tuple[str, ...]) -> Optional[str]:
        for phrase in phrases:
            normalized_phrase = normalize_text(phrase)
            if normalized_phrase in normalized_text:
                return phrase
        return None

    def _resolve_polarity(self, normalized_text: str, phrase: str, local_window: str) -> str:
        normalized_phrase = normalize_text(phrase)
        index = normalized_text.find(normalized_phrase)
        window = normalized_text[max(0, index - 20):index]
        if "no good reason" in window:
            window = window.replace("no good reason", " ")
        phrase_contains_negation = any(cue in normalized_phrase for cue in NEGATION_CUES)
        if not phrase_contains_negation and self._contains_cue(window, NEGATION_CUES):
            if self._contains_contrastive_present_signal(window, local_window):
                return "present"
            return "absent"
        if any(cue in local_window for cue in UNCERTAINTY_CUES):
            return "uncertain"
        return "present"

    def _is_protective_self_harm_denial(self, normalized_text: str) -> bool:
        return any(re.search(pattern, normalized_text) for pattern in PROTECTIVE_NEGATION_PATTERNS)

    def _contains_cue(self, text: str, cues: Tuple[str, ...]) -> bool:
        padded = f" {text.strip()} "
        for cue in cues:
            normalized_cue = normalize_text(cue).strip()
            if not normalized_cue:
                continue
            if f" {normalized_cue} " in padded:
                return True
        return False

    def _contains_contrastive_present_signal(self, window: str, local_window: str) -> bool:
        combined = f"{window} {local_window}".strip()
        return any(cue in combined for cue in CONTRAST_PRESENT_CUES)

    def _resolve_score(self, base_score: int, local_window: str, polarity: str) -> int:
        if polarity == "absent":
            return 0
        score = base_score
        if any(cue in local_window for cue in HIGH_INTENSITY_CUES):
            score += 1
        if any(cue in local_window for cue in LOW_INTENSITY_CUES):
            score -= 1
        if polarity == "uncertain":
            score -= 1
        return max(0, min(score, 3))

    def _local_window(self, normalized_text: str, phrase: str, radius: int = 14) -> str:
        normalized_phrase = normalize_text(phrase)
        index = normalized_text.find(normalized_phrase)
        if index == -1:
            return normalized_text
        start = max(0, index - radius)
        end = min(len(normalized_text), index + len(normalized_phrase) + radius)
        return normalized_text[start:end]

    def _build_item_scores(self, spans: List[EvidenceSpan]) -> Dict[str, ItemScore]:
        spans_by_item: Dict[str, List[EvidenceSpan]] = defaultdict(list)
        for span in spans:
            spans_by_item[span.item_id].append(span)
        present_turns_by_item: Dict[str, set[int]] = defaultdict(set)
        for span in spans:
            if span.polarity == "present":
                present_turns_by_item[span.item_id].add(span.turn_id)

        scores: Dict[str, ItemScore] = {}
        for item in all_items():
            item_spans = spans_by_item.get(item.item_id, [])
            present = [span for span in item_spans if span.polarity == "present"]
            absent = [span for span in item_spans if span.polarity == "absent"]
            uncertain = [span for span in item_spans if span.polarity == "uncertain"]
            contradiction = bool(present and absent)
            cohort = SCENE_COHORTS.get(item.item_id, ())
            cohort_present_items = [other for other in cohort if present_turns_by_item.get(other)]
            same_turn_support = any(
                present_turns_by_item.get(other, set()) & {span.turn_id for span in present}
                for other in cohort_present_items
            )
            confidence = self._confidence(
                present,
                absent,
                uncertain,
                contradiction,
                related_present_count=len(cohort_present_items),
                same_turn_support=same_turn_support,
            )
            stable = self._is_stable(
                item.item_id,
                present,
                absent,
                uncertain,
                contradiction,
                confidence,
                related_present_count=len(cohort_present_items),
                same_turn_support=same_turn_support,
            )

            if not item_spans:
                value = None
                status = "unresolved"
                note = None
                review_recommended = False
            elif contradiction:
                review_recommended = True
                if confidence < 0.58:
                    value = None
                    status = "abstained"
                    note = "Conflicting evidence remains unresolved. Follow-up or human review is needed before scoring."
                else:
                    value = max((span.score_hint for span in present), default=0)
                    status = "contradicted"
                    note = "Earlier and later turns point in different directions."
            elif present:
                value = max(span.score_hint for span in present)
                status = "resolved" if stable else "partial"
                note = None
                review_recommended = False
            elif absent:
                value = 0
                status = "resolved" if stable else "partial"
                note = None
                review_recommended = False
            else:
                value = max((span.score_hint for span in uncertain), default=None)
                status = "partial"
                note = "Indirect evidence only."
                review_recommended = False

            scores[item.item_id] = ItemScore(
                item_id=item.item_id,
                questionnaire=item.questionnaire,
                value=value,
                status=status,
                confidence=confidence,
                stable=stable,
                evidence_span_ids=[span.span_id for span in item_spans],
                contradiction_note=note,
                review_recommended=review_recommended,
            )
        return scores

    def _is_stable(
        self,
        item_id: str,
        present: List[EvidenceSpan],
        absent: List[EvidenceSpan],
        uncertain: List[EvidenceSpan],
        contradiction: bool,
        confidence: float,
        related_present_count: int = 0,
        same_turn_support: bool = False,
    ) -> bool:
        if contradiction:
            return False
        evidence_count = len(present) + len(absent) + len(uncertain)
        if (
            item_id in {"phq_q1_anhedonia", "phq_q2_low_mood"}
            and present
            and evidence_count == 1
            and related_present_count >= 1
            and same_turn_support
            and any(
                cue in normalize_text(span.text_span)
                for span in present
                for cue in GENERIC_MOOD_OPENING_CUES
            )
        ):
            # One broad "low/flat/disconnected" line can touch both mood items,
            # but it should still invite clarification before we mark either one closed.
            return False
        if item_id == "phq_q3_sleep":
            return confidence >= 0.72 and evidence_count >= 2
        if item_id == "phq_q4_fatigue":
            return confidence >= 0.78
        return confidence >= 0.72

    def build_coverage(self, items: Dict[str, ItemScore], next_items: Optional[List[str]] = None) -> CoveragePlan:
        touched_items = [item_id for item_id, item in items.items() if item.evidence_span_ids]
        resolved_items = [item_id for item_id, item in items.items() if item.status == "resolved"]
        partial_items = [item_id for item_id, item in items.items() if item.status == "partial"]
        contradicted_items = [item_id for item_id, item in items.items() if item.status == "contradicted"]
        abstained_items = [item_id for item_id, item in items.items() if item.status == "abstained"]
        unresolved_items = [item_id for item_id, item in items.items() if item.status == "unresolved"]
        review_items = [
            item_id for item_id, item in items.items() if item.review_recommended or item.status in {"contradicted", "abstained"}
        ]
        completion_ratio = round(len(resolved_items) / max(len(items), 1), 2)
        priority_order = sorted(
            partial_items + contradicted_items + abstained_items + unresolved_items,
            key=lambda item_id: (-ITEM_INDEX[item_id].priority, items[item_id].confidence, item_id),
        )
        return CoveragePlan(
            total_items=len(items),
            touched_items=len(touched_items),
            resolved_items=resolved_items,
            partial_items=partial_items,
            contradicted_items=contradicted_items,
            abstained_items=abstained_items,
            unresolved_items=unresolved_items,
            review_items=review_items,
            next_items=list(next_items or priority_order[:5]),
            completion_ratio=completion_ratio,
            review_required=bool(review_items),
        )

    def _confidence(
        self,
        present: List[EvidenceSpan],
        absent: List[EvidenceSpan],
        uncertain: List[EvidenceSpan],
        contradiction: bool,
        related_present_count: int = 0,
        same_turn_support: bool = False,
    ) -> float:
        total = 0.1
        evidence_count = len(present) + len(absent) + len(uncertain)
        if evidence_count:
            total += 0.35
        total += min(evidence_count - 1, 2) * 0.14 if evidence_count > 1 else 0.0
        if present and max(span.score_hint for span in present) >= 2:
            total += 0.12
        if present and not absent and not uncertain and max(span.score_hint for span in present) >= 2:
            total += 0.16
        if len(present) == 1 and not absent and not uncertain and max(span.score_hint for span in present) >= 2:
            total += 0.1
        if absent and not present:
            total += 0.08
        if absent and not present and not uncertain:
            total += 0.19
        if uncertain:
            total -= 0.08
        if present and related_present_count:
            total += min(related_present_count, 2) * 0.08
        if present and same_turn_support:
            total += 0.2
        if contradiction:
            total -= 0.28
        return round(max(0.0, min(total, 0.95)), 2)

    def _build_totals(self, items: Dict[str, ItemScore]) -> Dict[str, int]:
        totals = {"PHQ9": 0, "GAD7": 0}
        for item in items.values():
            if item.value is None:
                continue
            totals[item.questionnaire] += item.value
        return totals
