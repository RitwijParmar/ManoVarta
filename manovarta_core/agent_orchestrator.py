"""Bounded multi-agent orchestration for ManoVarta's clinical-support workflow.

These roles are deliberately narrow: they exchange typed evidence and never post
to a health record, diagnose, or decide that an urgent safety signal can be ignored.
"""

from __future__ import annotations

from uuid import uuid4

from manovarta_core.schemas import AgentHandoff, AgentRun, ScreeningSnapshot


class ScreeningAgentOrchestrator:
    """Builds an auditable handoff trace from the controller's bounded stages."""

    def record(self, snapshot: ScreeningSnapshot, *, response_source: str) -> AgentRun:
        safety_level = snapshot.safety.level
        safety_status = "handoff_required" if safety_level == "urgent" else "completed"
        outcome = "urgent_handoff" if safety_level == "urgent" else "review" if safety_level == "review" else "continue"
        if snapshot.analysis_status == "degraded" and outcome == "continue":
            outcome = "degraded"

        handoffs = [
            AgentHandoff(
                agent="Safety Guardian",
                status=safety_status,
                artifact=f"safety={safety_level}",
                authority_boundary="Rules and independent safety signals can pause the workflow; no model may clear an urgent signal.",
            ),
            AgentHandoff(
                agent="Evidence Analyst",
                status="degraded" if snapshot.analysis_status == "degraded" else "completed",
                artifact=f"evidence_spans={len(snapshot.evidence_spans)}; mode={snapshot.mode}",
                authority_boundary="Produces item-level evidence only; it cannot diagnose or assign final clinical meaning.",
            ),
            AgentHandoff(
                agent="Dialogue Supervisor",
                status="blocked" if safety_level == "urgent" else "completed",
                artifact=f"next_action={snapshot.coverage.dialogue.next_action}",
                authority_boundary="Chooses a bounded next question from the controller; it cannot override the Safety Guardian.",
            ),
            AgentHandoff(
                agent="Response Editor",
                status="blocked" if safety_level == "urgent" else "completed",
                artifact=f"source={response_source}",
                authority_boundary="May phrase an approved response only; urgent paths use the fixed crisis protocol instead of free-form generation.",
            ),
        ]
        return AgentRun(run_id=f"agent-run-{uuid4().hex[:12]}", outcome=outcome, handoffs=handoffs)


AGENTIC_ARCHITECTURE = {
    "controller": "ScreeningAgentOrchestrator",
    "roles": [
        "Safety Guardian: independent escalation gate",
        "Evidence Analyst: evidence-bound PHQ-9/GAD-7 extraction",
        "Dialogue Supervisor: constrained next-step selection",
        "Response Editor: bounded multilingual phrasing",
    ],
    "prohibited_actions": [
        "diagnosis",
        "treatment recommendation",
        "EHR writeback",
        "clearing an urgent safety signal",
    ],
}
