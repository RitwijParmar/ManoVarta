from __future__ import annotations

from typing import Dict, List


SCREENING_KNOWLEDGE_BASE: Dict[str, object] = {
    "questionnaires": {
        "PHQ9": {
            "purpose": "Tracks depressive symptom burden through open-ended conversation evidence.",
            "domains": [
                "interest and pleasure",
                "low mood",
                "sleep",
                "energy",
                "appetite",
                "self-worth",
                "concentration",
                "psychomotor change",
                "self-harm thoughts",
            ],
        },
        "GAD7": {
            "purpose": "Tracks anxiety and worry burden through open-ended conversation evidence.",
            "domains": [
                "nervousness",
                "control of worry",
                "excessive worry",
                "relaxation difficulty",
                "restlessness",
                "irritability",
                "fear that something awful will happen",
            ],
        },
    },
    "domains": {
        "mood": {
            "description": "Low mood, hopelessness, or loss of interest that changes daily functioning.",
            "look_for": [
                "sadness or emptiness",
                "loss of enjoyment",
                "social withdrawal",
                "loss of motivation",
            ],
            "gentle_follow_up": "Ask what changed, how often it happens, and what daily activities are harder now.",
        },
        "sleep": {
            "description": "Trouble falling asleep, staying asleep, waking early, or sleeping more than usual.",
            "look_for": [
                "late sleep onset",
                "night waking",
                "restless sleep",
                "oversleeping",
            ],
            "gentle_follow_up": "Clarify whether the issue is starting sleep, staying asleep, or sleeping too much.",
        },
        "energy": {
            "description": "Fatigue, low energy, or appetite change that affects routine.",
            "look_for": [
                "daytime fatigue",
                "reduced stamina",
                "missed meals",
                "increased eating",
            ],
            "gentle_follow_up": "Ask how energy or appetite changes show up during a normal day.",
        },
        "anxiety": {
            "description": "Persistent worry, tension, restlessness, irritability, or fear of negative outcomes.",
            "look_for": [
                "mind racing",
                "body tension",
                "restlessness",
                "irritability",
            ],
            "gentle_follow_up": "Clarify whether the worry feels mental, physical, or both, and when it spikes.",
        },
        "self_view": {
            "description": "Guilt, shame, self-blame, or feeling like a burden.",
            "look_for": [
                "self-criticism",
                "worthlessness",
                "burden language",
                "failure beliefs",
            ],
            "gentle_follow_up": "Ask what their inner voice says when things feel heavy.",
        },
        "focus": {
            "description": "Concentration trouble, slowed functioning, pacing, or agitation.",
            "look_for": [
                "mind drifting",
                "difficulty concentrating",
                "slowed action",
                "pacing and restlessness",
            ],
            "gentle_follow_up": "Ask how work, study, or routine tasks feel different now.",
        },
        "safety": {
            "description": "Thoughts of self-harm, wishing to disappear, or not wanting to be alive.",
            "look_for": [
                "direct self-harm language",
                "suicidal intent",
                "disappearance language",
                "burden language with escalation",
            ],
            "gentle_follow_up": "Pause normal screening and ask one short direct safety question only when needed.",
        },
    },
    "risk_policy": {
        "review": [
            "indirect disappearance language",
            "being a burden",
            "wanting everything to stop",
            "ambiguous self-harm references",
        ],
        "urgent": [
            "direct self-harm intent",
            "suicide method or timing",
            "not wanting to be alive with immediacy",
        ],
    },
    "sources": [
        {
            "label": "NIMH generalized anxiety disorder overview",
            "url": "https://www.nimh.nih.gov/health/publications/generalized-anxiety-disorder-gad",
        },
        {
            "label": "NIMH warning signs of suicide",
            "url": "https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide",
        },
    ],
}


def knowledge_summary_for_topic(topic: str) -> str:
    topic_data = SCREENING_KNOWLEDGE_BASE["domains"].get(topic)
    if not topic_data:
        return "Keep the follow-up brief, concrete, and tied to daily impact."
    look_for = ", ".join(topic_data["look_for"][:3])
    return f"{topic_data['description']} Look for: {look_for}. {topic_data['gentle_follow_up']}"


def profile_summary(profile: object) -> str:
    if profile is None:
        return "No user profile context provided."

    bits: List[str] = []
    preferred_name = getattr(profile, "preferred_name", None)
    if preferred_name:
        bits.append(f"name={preferred_name}")
    age = getattr(profile, "age", None)
    if age:
        bits.append(f"age={age}")
    occupation = getattr(profile, "occupation", None)
    if occupation:
        bits.append(f"occupation={occupation}")
    living_situation = getattr(profile, "living_situation", None)
    if living_situation:
        bits.append(f"living_situation={living_situation}")
    support_system = getattr(profile, "support_system", None)
    if support_system:
        bits.append(f"support_system={support_system}")
    context_note = getattr(profile, "context_note", None)
    if context_note:
        bits.append(f"context_note={context_note}")
    return ", ".join(bits) if bits else "No user profile context provided."
