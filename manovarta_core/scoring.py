from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from manovarta_core.lexicon import HIGH_INTENSITY_CUES, LOW_INTENSITY_CUES, NEGATION_CUES, RULES, UNCERTAINTY_CUES
from manovarta_core.questionnaires import ITEM_INDEX, all_items
from manovarta_core.schemas import CoveragePlan, EvidenceSpan, ItemScore, ScreeningSnapshot, Turn
from manovarta_core.text import extract_window, normalize_text


class ConversationScorer:
    def analyze(self, turns: Iterable[Turn], language: str, safety_flag) -> ScreeningSnapshot:
        user_turns = [turn for turn in turns if turn.speaker == "user"]
        evidence_spans = self._collect_evidence(user_turns)
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
        for turn in turns:
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
        return spans

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
        if any(cue in window for cue in NEGATION_CUES):
            return "absent"
        if any(cue in local_window for cue in UNCERTAINTY_CUES):
            return "uncertain"
        return "present"

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

        scores: Dict[str, ItemScore] = {}
        for item in all_items():
            item_spans = spans_by_item.get(item.item_id, [])
            present = [span for span in item_spans if span.polarity == "present"]
            absent = [span for span in item_spans if span.polarity == "absent"]
            uncertain = [span for span in item_spans if span.polarity == "uncertain"]
            contradiction = bool(present and absent)
            confidence = self._confidence(present, absent, uncertain, contradiction)
            stable = confidence >= 0.72 and not contradiction

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
    ) -> float:
        total = 0.1
        evidence_count = len(present) + len(absent) + len(uncertain)
        if evidence_count:
            total += 0.35
        total += min(evidence_count - 1, 2) * 0.14 if evidence_count > 1 else 0.0
        if present and max(span.score_hint for span in present) >= 2:
            total += 0.12
        if absent and not present:
            total += 0.08
        if uncertain:
            total -= 0.08
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
