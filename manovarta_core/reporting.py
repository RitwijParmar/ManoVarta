from typing import List

from manovarta_core.knowledge import profile_summary
from manovarta_core.questionnaires import GAD7_ITEMS, ITEM_INDEX, PHQ9_ITEMS
from manovarta_core.schemas import ChatSession, DomainResult, ScreeningSnapshot, SummaryRow


def build_summary(session: ChatSession, snapshot: ScreeningSnapshot) -> str:
    resolved_bits: List[str] = []
    unresolved_bits: List[str] = []

    for item_id, item in snapshot.items.items():
        label = ITEM_INDEX[item_id].label
        if item.value is not None and item.status in {"resolved", "partial", "contradicted"}:
            resolved_bits.append(f"{label}={item.value} ({item.status}, {item.confidence:.2f})")
        if item.status != "resolved":
            unresolved_bits.append(label)

    safety_text = snapshot.safety.level
    dialogue = snapshot.coverage.dialogue
    resolved_text = "; ".join(resolved_bits[:8]) or "No stable symptom evidence yet."
    unresolved_text = ", ".join(unresolved_bits[:6]) or "None"
    review_labels = [ITEM_INDEX[item_id].label for item_id in snapshot.coverage.review_items[:4]]
    review_text = ", ".join(review_labels) or "None"
    style = dialogue.user_style
    disclosure = dialogue.disclosure
    profile_text = profile_summary(session.profile)

    return (
        f"Session {session.session_id} in {session.language}. "
        f"Profile context: {profile_text}. "
        f"Observed totals: PHQ-9={snapshot.totals['PHQ9']}, GAD-7={snapshot.totals['GAD7']}. "
        f"Coverage: {snapshot.coverage.touched_items}/{snapshot.coverage.total_items} items touched, "
        f"{len(snapshot.coverage.resolved_items)} resolved, "
        f"{len(snapshot.coverage.abstained_items)} abstained. "
        f"Safety: {safety_text}. "
        f"Dialogue stage: {dialogue.stage}; next action: {dialogue.next_action} on {dialogue.target_topic}. "
        f"User style: {style.verbosity}, {style.openness}, distress trend {style.distress_trend}. "
        f"Disclosure efficiency: {disclosure.items_per_user_turn:.2f} items touched per user turn. "
        f"Mode: {snapshot.mode}. "
        f"Evidence summary: {resolved_text}. "
        f"Follow-up still needed for: {unresolved_text}. "
        f"Human review focus: {review_text}."
    )


def build_rows(snapshot: ScreeningSnapshot) -> List[SummaryRow]:
    span_text = {span.span_id: span.text_span for span in snapshot.evidence_spans}
    rows: List[SummaryRow] = []
    for item_id, item in snapshot.items.items():
        rows.append(
            SummaryRow(
                item_id=item_id,
                questionnaire=item.questionnaire,
                label=ITEM_INDEX[item_id].label,
                value=item.value,
                status=item.status,
                confidence=item.confidence,
                source=item.source,
                evidence_quotes=[span_text[span_id] for span_id in item.evidence_span_ids if span_id in span_text][:3],
            )
        )
    rows.sort(key=lambda row: (row.questionnaire, row.label))
    return rows


def build_domain_results(snapshot: ScreeningSnapshot) -> tuple[DomainResult, DomainResult]:
    return (
        _build_domain_result(snapshot, "phq", PHQ9_ITEMS),
        _build_domain_result(snapshot, "gad", GAD7_ITEMS),
    )


def _build_domain_result(snapshot: ScreeningSnapshot, domain: str, questionnaire_items) -> DomainResult:
    item_ids = [item.item_id for item in questionnaire_items]
    scores = [snapshot.items[item_id] for item_id in item_ids if item_id in snapshot.items]
    resolved_items = [item.item_id for item in scores if item.status == "resolved"]
    remaining_items = [item.item_id for item in scores if item.status != "resolved"]
    denied_items = [item.item_id for item in scores if item.status == "resolved" and item.value == 0]
    review_items = [
        item.item_id
        for item in scores
        if item.review_recommended or item.status in {"contradicted", "abstained"}
    ]
    source_modes = sorted({item.source for item in scores if item.source != "none"})
    completion_ratio = round(len(resolved_items) / max(len(item_ids), 1), 2)
    questionnaire = "PHQ9" if domain == "phq" else "GAD7"
    total_score = snapshot.totals.get(questionnaire, 0) or 0
    return DomainResult(
        domain=domain,
        questionnaire=questionnaire,
        total_score=total_score,
        resolved_items=resolved_items,
        remaining_items=remaining_items,
        denied_items=denied_items,
        review_items=review_items,
        source_modes=source_modes,
        completion_ratio=completion_ratio,
        complete=not remaining_items,
    )
