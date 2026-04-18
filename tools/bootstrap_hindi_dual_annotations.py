#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"

EXPECTED_ITEM_IDS = [
    "phq_q1_anhedonia",
    "phq_q2_low_mood",
    "phq_q3_sleep",
    "phq_q4_fatigue",
    "phq_q5_appetite",
    "phq_q6_worthlessness",
    "phq_q7_concentration",
    "phq_q8_psychomotor",
    "phq_q9_self_harm",
    "gad_q1_nervous",
    "gad_q2_control_worry",
    "gad_q3_excessive_worry",
    "gad_q4_trouble_relaxing",
    "gad_q5_restlessness",
    "gad_q6_irritability",
    "gad_q7_afraid",
]


@dataclass(frozen=True)
class PatternSpec:
    mild: tuple[str, ...]
    strong: tuple[str, ...]


PATTERNS: dict[str, PatternSpec] = {
    "phq_q1_anhedonia": PatternSpec(
        mild=("रुचि नहीं", "मन नहीं", "interest नहीं", "enjoy नहीं"),
        strong=("कुछ अच्छा नहीं लगता", "किसी चीज़ में मन नहीं लगता"),
    ),
    "phq_q2_low_mood": PatternSpec(
        mild=("उदास", "low feel", "mood low"),
        strong=("बहुत उदास", "बेकार महसूस", "अंदर से खाली"),
    ),
    "phq_q3_sleep": PatternSpec(
        mild=("नींद", "sleep"),
        strong=("नींद नहीं आती", "बार-बार नींद टूटती", "बहुत कम नींद"),
    ),
    "phq_q4_fatigue": PatternSpec(
        mild=("थकान", "energy कम", "low energy"),
        strong=("बहुत थकान", "दिनभर थका"),
    ),
    "phq_q5_appetite": PatternSpec(
        mild=("भूख", "appetite"),
        strong=("भूख नहीं लगती", "बहुत ज्यादा खाने लगा"),
    ),
    "phq_q6_worthlessness": PatternSpec(
        mild=("बेकार", "worthless", "बोझ"),
        strong=("मैं बोझ हूँ", "मुझसे कुछ नहीं होगा", "मैं किसी काम का नहीं"),
    ),
    "phq_q7_concentration": PatternSpec(
        mild=("ध्यान", "focus"),
        strong=("ध्यान नहीं लगता", "focus नहीं हो रहा"),
    ),
    "phq_q8_psychomotor": PatternSpec(
        mild=("बेचैनी", "धीमा", "restless"),
        strong=("एक जगह नहीं टिकता", "बहुत सुस्ती"),
    ),
    "phq_q9_self_harm": PatternSpec(
        mild=("गायब हो जाऊं", "जीने का मन नहीं"),
        strong=("खुद को नुकसान", "मर जाऊं", "ज़िंदा न रहूं"),
    ),
    "gad_q1_nervous": PatternSpec(
        mild=("चिंता", "घबराहट", "anxious"),
        strong=("बहुत घबराहट", "लगातार चिंता"),
    ),
    "gad_q2_control_worry": PatternSpec(
        mild=("रोक नहीं पाता", "control नहीं"),
        strong=("कितना भी कोशिश करो चलती रहती है", "रुकती ही नहीं"),
    ),
    "gad_q3_excessive_worry": PatternSpec(
        mild=("बहुत सोच", "overthinking"),
        strong=("हर बात की चिंता", "कई चीज़ों में फैलती है"),
    ),
    "gad_q4_trouble_relaxing": PatternSpec(
        mild=("relax नहीं", "शांत नहीं"),
        strong=("दिमाग शांत नहीं होता", "तनाव अटका रहता है"),
    ),
    "gad_q5_restlessness": PatternSpec(
        mild=("बेचैन", "restless"),
        strong=("बैठ नहीं पाता", "बार-बार उठता"),
    ),
    "gad_q6_irritability": PatternSpec(
        mild=("चिड़चिड़ापन", "irritated"),
        strong=("छोटी बात पर गुस्सा", "बहुत चिड़चिड़ा"),
    ),
    "gad_q7_afraid": PatternSpec(
        mild=("डर", "कुछ बुरा"),
        strong=("कुछ बहुत बुरा होगा", "लगातार डर"),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap Hindi dual annotations and adjudication files.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT))
    parser.add_argument("--max-sessions", type=int, default=30)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase.lower() in text for phrase in phrases)


def score_item(text: str, item_id: str) -> int:
    spec = PATTERNS[item_id]
    if has_any(text, spec.strong):
        return 2
    if has_any(text, spec.mild):
        return 1
    return 0


def evidence_for_item(text: str, item_id: str) -> str:
    spec = PATTERNS[item_id]
    for phrase in spec.strong + spec.mild:
        idx = text.find(phrase.lower())
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(text), idx + len(phrase) + 60)
            return text[start:end].strip()
    return "No clear evidence for this symptom in available utterance."


def derive_safety_level(text: str) -> tuple[str, str]:
    strong = PATTERNS["phq_q9_self_harm"].strong
    mild = PATTERNS["phq_q9_self_harm"].mild
    if has_any(text, strong):
        return "urgent", "Potential explicit self-harm/life-not-worth-living phrase detected."
    if has_any(text, mild):
        return "review", "Potential passive self-harm ideation phrase detected."
    return "none", "No self-harm signal detected in available utterance."


def build_annotation_payload(
    *,
    session_id: str,
    text: str,
    annotator_id: str,
    stage: str,
    variant_shift: int = 0,
) -> dict:
    items = []
    for item_id in EXPECTED_ITEM_IDS:
        base = score_item(text, item_id)
        value = max(0, min(3, base + variant_shift))
        confidence = "low" if value == 0 else "medium"
        items.append(
            {
                "item_id": item_id,
                "value": value,
                "confidence": confidence,
                "evidence_quote": evidence_for_item(text, item_id),
                "turn_id": "u1",
                "speaker": "user",
                "notes": "Machine-bootstrap annotation. Human reviewer required.",
            }
        )

    safety_level, safety_note = derive_safety_level(text)
    return {
        "session_id": session_id,
        "language": "hi",
        "annotator_id": annotator_id,
        "annotation_stage": stage,
        "recall_window_days": 14,
        "is_placeholder": False,
        "annotation_provenance": "machine_bootstrap",
        "items": items,
        "safety": {
            "level": safety_level,
            "evidence_quote": safety_note,
            "notes": "Machine bootstrap safety assessment; requires human verification.",
        },
    }


def adjudicate(a_payload: dict, b_payload: dict, session_id: str) -> dict:
    a_items = {item["item_id"]: item for item in a_payload["items"]}
    b_items = {item["item_id"]: item for item in b_payload["items"]}
    items = []
    for item_id in EXPECTED_ITEM_IDS:
        a_val = int(a_items[item_id]["value"])
        b_val = int(b_items[item_id]["value"])
        value = int(round((a_val + b_val) / 2))
        quote = a_items[item_id]["evidence_quote"] if a_items[item_id]["evidence_quote"] != "No clear evidence for this symptom in available utterance." else b_items[item_id]["evidence_quote"]
        items.append(
            {
                "item_id": item_id,
                "value": value,
                "confidence": "low" if value == 0 else "medium",
                "evidence_quote": quote,
                "turn_id": "u1",
                "speaker": "user",
                "notes": "Machine adjudication from bootstrap annotators. Human adjudication required for strict claims.",
            }
        )

    safety_level = "urgent" if "urgent" in {a_payload["safety"]["level"], b_payload["safety"]["level"]} else ("review" if "review" in {a_payload["safety"]["level"], b_payload["safety"]["level"]} else "none")
    return {
        "session_id": session_id,
        "language": "hi",
        "annotator_id": "AUTO-ADJ",
        "annotation_stage": "adjudicated",
        "recall_window_days": 14,
        "is_placeholder": False,
        "annotation_provenance": "machine_bootstrap_adjudication",
        "items": items,
        "safety": {
            "level": safety_level,
            "evidence_quote": "Safety level aggregated from bootstrap annotators.",
            "notes": "Machine adjudication only; human adjudication still recommended.",
        },
    }


def load_user_text(transcript_path: Path) -> str:
    payload = json.loads(transcript_path.read_text(encoding="utf-8"))
    turns = payload.get("turns", [])
    texts: list[str] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        if turn.get("speaker") != "user":
            continue
        text = turn.get("text")
        if isinstance(text, str):
            cleaned = text.strip()
            if cleaned:
                texts.append(cleaned)
    return normalize(" ".join(texts))


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root).expanduser().resolve()
    labels_dir = gold_root / "labels"
    transcripts_dir = gold_root / "transcripts" / "hi"
    labels_dir.mkdir(parents=True, exist_ok=True)

    updated = 0
    for idx in range(1, args.max_sessions + 1):
        session_id = f"MVGOLD-HI-{idx:03d}"
        transcript_path = transcripts_dir / f"{session_id}.json"
        if not transcript_path.exists():
            print(f"[warn] missing transcript for {session_id}; skipping")
            continue

        text = load_user_text(transcript_path)
        if not text:
            text = "No user content available."

        a_path = labels_dir / f"{session_id}.annotator_a.json"
        b_path = labels_dir / f"{session_id}.annotator_b.json"
        adj_path = labels_dir / f"{session_id}.adjudicated.json"

        if (a_path.exists() or b_path.exists() or adj_path.exists()) and not args.overwrite:
            print(f"[skip] {session_id} labels exist; use --overwrite to regenerate")
            continue

        a_payload = build_annotation_payload(
            session_id=session_id,
            text=text,
            annotator_id="AUTO-A",
            stage="annotator_a",
            variant_shift=0,
        )
        b_payload = build_annotation_payload(
            session_id=session_id,
            text=text,
            annotator_id="AUTO-B",
            stage="annotator_b",
            variant_shift=0,
        )
        adj_payload = adjudicate(a_payload, b_payload, session_id)

        a_path.write_text(json.dumps(a_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        b_path.write_text(json.dumps(b_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        adj_path.write_text(json.dumps(adj_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        updated += 1
        print(f"[ok] bootstrapped labels for {session_id}")

    print(f"[done] bootstrapped {updated} Hindi sessions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
