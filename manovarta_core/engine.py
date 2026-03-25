from __future__ import annotations

from typing import Iterable, Optional

from manovarta_core.llm import HuggingFaceExtractor
from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.semantic_safety import SemanticSafetyMonitor
from manovarta_core.safety import SafetyMonitor
from manovarta_core.schemas import EvidenceSpan, ItemScore, SafetyFlag, ScreeningSnapshot, Turn
from manovarta_core.scoring import ConversationScorer
from manovarta_core.text import normalize_text


SAFETY_RANK = {"none": 0, "review": 1, "urgent": 2}


class RuntimeEngine:
    def __init__(
        self,
        scorer: Optional[ConversationScorer] = None,
        safety_monitor: Optional[SafetyMonitor] = None,
        semantic_safety_monitor: Optional[SemanticSafetyMonitor] = None,
        extractor: Optional[HuggingFaceExtractor] = None,
    ) -> None:
        self.scorer = scorer or ConversationScorer()
        self.safety_monitor = safety_monitor or SafetyMonitor()
        self.semantic_safety_monitor = semantic_safety_monitor
        self.extractor = extractor

    def analyze(self, turns: Iterable[Turn], language: str, use_llm: bool = True) -> ScreeningSnapshot:
        turn_list = list(turns)
        safety_flag = self.safety_monitor.assess(turn_list)
        if self.semantic_safety_monitor is not None:
            safety_flag = self._merge_safety_flags(safety_flag, self.semantic_safety_monitor.assess(turn_list))
        snapshot = self.scorer.analyze(turn_list, language, safety_flag)
        if not use_llm or self.extractor is None or not self.extractor.enabled:
            return snapshot

        llm_result = self.extractor.extract(turn_list, language)
        if not llm_result:
            return snapshot
        return self._merge_snapshot(snapshot, turn_list, llm_result)

    def _merge_snapshot(self, base: ScreeningSnapshot, turns: list[Turn], llm_result: dict) -> ScreeningSnapshot:
        items = {item_id: item.model_copy(deep=True) for item_id, item in base.items.items()}
        evidence_spans = [span.model_copy(deep=True) for span in base.evidence_spans]
        seen_spans = {(span.item_id, span.turn_id, normalize_text(span.text_span)) for span in evidence_spans}
        llm_used = False

        for offset, item_payload in enumerate(llm_result.get("items", []), start=1):
            item_id = item_payload.get("item_id")
            value = item_payload.get("value")
            if item_id not in items or not isinstance(value, int) or value < 0 or value > 3:
                continue

            quote = (item_payload.get("evidence_quote") or "").strip()
            note = (item_payload.get("confidence_note") or "").strip()
            span = self._build_llm_span(base, turns, item_id, value, quote, note, offset)
            span_ids = []
            matched_quote = ""
            if span is not None:
                span_key = (span.item_id, span.turn_id, normalize_text(span.text_span))
                if span_key not in seen_spans:
                    seen_spans.add(span_key)
                    evidence_spans.append(span)
                span_ids.append(span.span_id)
                matched_quote = span.text_span

            items[item_id] = self._merge_item_score(items[item_id], value, span_ids, matched_quote, note)
            llm_used = True

        merged_safety = self._merge_safety(base.safety, llm_result)
        unresolved_items = [
            item_id for item_id, item in items.items() if item.status != "resolved"
        ]
        return ScreeningSnapshot(
            language=base.language,
            items=items,
            evidence_spans=evidence_spans,
            unresolved_items=unresolved_items,
            totals=self._build_totals(items),
            safety=merged_safety,
            mode="hybrid" if llm_used else base.mode,
        )

    def _build_llm_span(
        self,
        snapshot: ScreeningSnapshot,
        turns: list[Turn],
        item_id: str,
        value: int,
        quote: str,
        note: str,
        offset: int,
    ) -> Optional[EvidenceSpan]:
        user_turns = [turn for turn in turns if turn.speaker == "user"]
        if not user_turns:
            return None

        turn = self._match_turn(user_turns, quote) or user_turns[-1]
        span_text = quote or turn.text[:160]
        return EvidenceSpan(
            span_id=f"LLM-{turn.turn_id}-{offset}",
            questionnaire=ITEM_INDEX[item_id].questionnaire,
            item_id=item_id,
            turn_id=turn.turn_id,
            text_span=span_text,
            polarity="present" if value > 0 else "uncertain",
            score_hint=value,
            rationale=note or "LLM-aligned evidence span.",
        )

    def _match_turn(self, turns: list[Turn], quote: str) -> Optional[Turn]:
        normalized_quote = normalize_text(quote)
        if not normalized_quote:
            return None
        for turn in turns:
            normalized_turn = normalize_text(turn.text)
            if normalized_quote in normalized_turn or normalized_turn in normalized_quote:
                return turn
        return None

    def _merge_item_score(
        self,
        base: ItemScore,
        llm_value: int,
        llm_span_ids: list[str],
        matched_quote: str,
        note: str,
    ) -> ItemScore:
        llm_confidence = 0.7
        if matched_quote:
            llm_confidence += 0.1
        if llm_value >= 2:
            llm_confidence += 0.06
        llm_confidence = round(min(llm_confidence, 0.9), 2)

        evidence_ids = list(dict.fromkeys(base.evidence_span_ids + llm_span_ids))
        if base.value is None:
            return base.model_copy(
                update={
                    "value": llm_value,
                    "status": "resolved" if llm_confidence >= 0.78 else "partial",
                    "confidence": max(base.confidence, llm_confidence),
                    "stable": llm_confidence >= 0.82,
                    "evidence_span_ids": evidence_ids,
                    "contradiction_note": note or None,
                    "source": "llm",
                }
            )

        if base.value == llm_value:
            return base.model_copy(
                update={
                    "status": "resolved",
                    "confidence": max(base.confidence, llm_confidence, 0.82),
                    "stable": True,
                    "evidence_span_ids": evidence_ids,
                    "source": "hybrid",
                }
            )

        if abs(base.value - llm_value) <= 1 and not base.stable:
            chosen_value = llm_value if llm_confidence >= base.confidence else base.value
            return base.model_copy(
                update={
                    "value": chosen_value,
                    "status": "partial",
                    "confidence": round(max(base.confidence, llm_confidence) - 0.04, 2),
                    "stable": False,
                    "evidence_span_ids": evidence_ids,
                    "contradiction_note": "Heuristic and LLM differ slightly.",
                    "source": "hybrid",
                }
            )

        return base.model_copy(
            update={
                "value": max(base.value, llm_value),
                "status": "contradicted",
                "confidence": round(max(0.4, min(base.confidence, llm_confidence)), 2),
                "stable": False,
                "evidence_span_ids": evidence_ids,
                "contradiction_note": "Heuristic and LLM disagree; review needed.",
                "source": "hybrid",
            }
        )

    def _merge_safety(self, heuristic: SafetyFlag, llm_result: dict) -> SafetyFlag:
        llm_level = llm_result.get("safety_level", "none")
        if llm_level not in SAFETY_RANK:
            llm_level = "none"
        llm_cues = [str(cue) for cue in llm_result.get("safety_cues", []) if str(cue).strip()]
        dominant_level = heuristic.level if SAFETY_RANK[heuristic.level] >= SAFETY_RANK[llm_level] else llm_level
        cues = list(dict.fromkeys(heuristic.cues + llm_cues))

        if dominant_level == heuristic.level and not llm_cues:
            return heuristic

        rationale_parts = [part for part in [heuristic.rationale, llm_result.get("notes")] if part]
        return SafetyFlag(
            level=dominant_level,
            cues=cues,
            rationale=" ".join(rationale_parts) or heuristic.rationale,
            needs_human_review=dominant_level in {"review", "urgent"},
        )

    def _merge_safety_flags(self, first: SafetyFlag, second: SafetyFlag) -> SafetyFlag:
        dominant_level = first.level if SAFETY_RANK[first.level] >= SAFETY_RANK[second.level] else second.level
        cues = list(dict.fromkeys(first.cues + second.cues))
        rationale_parts = [part for part in [first.rationale, second.rationale] if part]
        return SafetyFlag(
            level=dominant_level,
            cues=cues,
            rationale=" ".join(rationale_parts) or None,
            needs_human_review=dominant_level in {"review", "urgent"},
        )

    def _build_totals(self, items: dict[str, ItemScore]) -> dict[str, int]:
        totals = {"PHQ9": 0, "GAD7": 0}
        for item in items.values():
            if item.value is None:
                continue
            totals[item.questionnaire] += item.value
        return totals
