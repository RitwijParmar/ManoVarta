#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
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

FIELDNAMES = [
    "session_id",
    "language",
    "cohort",
    "target_order",
    "target_primary_domain",
    "target_risk_band",
    "collection_status",
    "audio_status",
    "metadata_status",
    "transcript_status",
    "annotator_a_status",
    "annotator_b_status",
    "adjudication_status",
    "qa_status",
    "audio_file",
    "transcript_file",
    "annotator_a_file",
    "annotator_b_file",
    "adjudicated_label_file",
    "notes",
]

METADATA_FIELDNAMES = [
    "session_id",
    "participant_id",
    "language",
    "age_years",
    "age_band",
    "occupation",
    "living_situation",
    "support_system",
    "consent_recorded",
    "collection_source",
    "audio_file",
    "transcript_file",
    "annotator_a_file",
    "annotator_b_file",
    "adjudicated_label_file",
    "split",
    "notes",
]

TARGET_DOMAIN_SEQUENCE = [
    "mood",
    "anhedonia",
    "sleep",
    "fatigue",
    "worthlessness",
    "focus",
    "anxiety_control",
    "anxiety_scope",
    "trouble_relaxing",
    "restlessness",
    "irritability",
    "fear",
    "mixed",
    "burden",
    "safety",
]

TARGET_RISK_BY_DOMAIN = {
    "mood": "none",
    "anhedonia": "none",
    "sleep": "none",
    "fatigue": "none",
    "worthlessness": "review_candidate",
    "focus": "none",
    "anxiety_control": "none",
    "anxiety_scope": "none",
    "trouble_relaxing": "none",
    "restlessness": "none",
    "irritability": "none",
    "fear": "none",
    "mixed": "none",
    "burden": "review_candidate",
    "safety": "urgent_candidate",
}


def language_bucket(language: str) -> str:
    return language.upper()


def build_session_rows(
    *,
    pilot_per_language: int = 5,
    total_per_language: int = 15,
    languages: tuple[str, ...] = ("en", "hi"),
) -> list[dict[str, str]]:
    if pilot_per_language < 1:
        raise ValueError("pilot_per_language must be at least 1")
    if total_per_language < pilot_per_language:
        raise ValueError("total_per_language must be >= pilot_per_language")

    rows: list[dict[str, str]] = []
    for language in languages:
        lang_bucket = language_bucket(language)
        for idx in range(1, total_per_language + 1):
            session_id = f"MVGOLD-{lang_bucket}-{idx:03d}"
            domain = TARGET_DOMAIN_SEQUENCE[(idx - 1) % len(TARGET_DOMAIN_SEQUENCE)]
            cohort = "pilot" if idx <= pilot_per_language else "expansion"
            rel_audio = Path("data") / "gold" / "audio" / language / f"{session_id}.wav"
            rel_transcript = Path("data") / "gold" / "transcripts" / language / f"{session_id}.json"
            rel_annotator_a = Path("data") / "gold" / "labels" / f"{session_id}.annotator_a.json"
            rel_annotator_b = Path("data") / "gold" / "labels" / f"{session_id}.annotator_b.json"
            rel_adjudicated = Path("data") / "gold" / "labels" / f"{session_id}.adjudicated.json"
            rows.append(
                {
                    "session_id": session_id,
                    "language": language,
                    "cohort": cohort,
                    "target_order": str(idx),
                    "target_primary_domain": domain,
                    "target_risk_band": TARGET_RISK_BY_DOMAIN[domain],
                    "collection_status": "planned",
                    "audio_status": "missing",
                    "metadata_status": "missing",
                    "transcript_status": "missing",
                    "annotator_a_status": "pending",
                    "annotator_b_status": "pending",
                    "adjudication_status": "pending",
                    "qa_status": "pending",
                    "audio_file": rel_audio.as_posix(),
                    "transcript_file": rel_transcript.as_posix(),
                    "annotator_a_file": rel_annotator_a.as_posix(),
                    "annotator_b_file": rel_annotator_b.as_posix(),
                    "adjudicated_label_file": rel_adjudicated.as_posix(),
                    "notes": "",
                }
            )
    return rows


def write_session_registry(rows: list[dict[str, str]], gold_root: Path) -> Path:
    registry_path = gold_root / "session_registry.csv"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return registry_path


def build_collection_plan(rows: list[dict[str, str]]) -> dict:
    pilot_rows = [row for row in rows if row["cohort"] == "pilot"]
    expansion_rows = [row for row in rows if row["cohort"] == "expansion"]
    by_language = Counter(row["language"] for row in rows)
    by_cohort = Counter(row["cohort"] for row in rows)
    return {
        "goal": "Strict-compliance bilingual gold dataset plan",
        "languages": sorted(by_language),
        "total_sessions": len(rows),
        "sessions_per_language": dict(by_language),
        "sessions_per_cohort": dict(by_cohort),
        "pilot_sessions": [row["session_id"] for row in pilot_rows],
        "expansion_sessions": [row["session_id"] for row in expansion_rows],
        "recommended_execution_order": [
            "Collect the 5 English + 5 Hindi pilot sessions first.",
            "Run dual annotation and adjudication on the pilot.",
            "Use validator output to fix process issues before collecting the expansion cohort.",
            "Expand to the full 30-session target only after the pilot workflow is stable.",
        ],
    }


def write_collection_plan(plan: dict, gold_root: Path) -> Path:
    plan_path = gold_root / "collection_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return plan_path


def build_metadata_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    metadata_rows: list[dict[str, str]] = []
    for row in rows:
        metadata_rows.append(
            {
                "session_id": row["session_id"],
                "participant_id": f"TBD-{row['session_id']}",
                "language": row["language"],
                "age_years": "",
                "age_band": "",
                "occupation": "",
                "living_situation": "",
                "support_system": "",
                "consent_recorded": "pending",
                "collection_source": "placeholder",
                "audio_file": row["audio_file"],
                "transcript_file": row["transcript_file"],
                "annotator_a_file": row["annotator_a_file"],
                "annotator_b_file": row["annotator_b_file"],
                "adjudicated_label_file": row["adjudicated_label_file"],
                "split": row["cohort"],
                "notes": "Autogenerated placeholder metadata row. Replace with real participant/profile metadata before compliance claims.",
            }
        )
    return metadata_rows


def write_metadata_sheet(metadata_rows: list[dict[str, str]], gold_root: Path, *, overwrite: bool = False) -> Path:
    metadata_path = gold_root / "metadata.csv"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    if metadata_path.exists() and not overwrite:
        return metadata_path
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDNAMES)
        writer.writeheader()
        writer.writerows(metadata_rows)
    return metadata_path


def _transcript_stub(row: dict[str, str]) -> dict:
    return {
        "session_id": row["session_id"],
        "language": row["language"],
        "cohort": row["cohort"],
        "is_placeholder": True,
        "collection_status": "planned",
        "notes": "Replace this stub with a real transcript linked to real audio before claiming gold-data completeness.",
        "profile": {
            "age_years": None,
            "occupation": "",
            "living_situation": "",
            "support_system": "",
        },
        "turns": [],
    }


def _label_stub(row: dict[str, str], annotation_stage: str, annotator_id: str) -> dict:
    return {
        "session_id": row["session_id"],
        "language": row["language"],
        "annotator_id": annotator_id,
        "annotation_stage": annotation_stage,
        "recall_window_days": 14,
        "is_placeholder": True,
        "placeholder_reason": "Autogenerated starter file. Replace with real annotation before evaluation or compliance claims.",
        "items": [
            {
                "item_id": item_id,
                "value": 0,
                "confidence": "low",
                "evidence_quote": "TODO",
                "turn_id": None,
                "speaker": "user",
                "notes": "TODO: replace placeholder value and evidence.",
            }
            for item_id in EXPECTED_ITEM_IDS
        ],
        "safety": {
            "level": "none",
            "evidence_quote": "TODO",
            "notes": "TODO: replace placeholder safety judgment.",
        },
    }


def materialize_starter_files(rows: list[dict[str, str]]) -> dict[str, int]:
    created = {
        "transcripts_created": 0,
        "annotator_a_created": 0,
        "annotator_b_created": 0,
        "adjudicated_created": 0,
    }
    for row in rows:
        transcript_path = resolve_project_path(row["transcript_file"])
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        if not transcript_path.exists():
            transcript_path.write_text(
                json.dumps(_transcript_stub(row), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            created["transcripts_created"] += 1
        row["transcript_status"] = "placeholder"

        annotator_specs = [
            ("annotator_a_file", "annotator_a", "TBD-A", "annotator_a_created", "annotator_a_status"),
            ("annotator_b_file", "annotator_b", "TBD-B", "annotator_b_created", "annotator_b_status"),
            ("adjudicated_label_file", "adjudicated", "TBD-ADJ", "adjudicated_created", "adjudication_status"),
        ]
        for field_name, annotation_stage, annotator_id, counter_key, status_field in annotator_specs:
            label_path = resolve_project_path(row[field_name])
            label_path.parent.mkdir(parents=True, exist_ok=True)
            if not label_path.exists():
                label_path.write_text(
                    json.dumps(_label_stub(row, annotation_stage, annotator_id), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                created[counter_key] += 1
            row[status_field] = "placeholder"
    return created


def resolve_project_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize the bilingual gold-data pilot and expansion plan.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Gold-data root directory.")
    parser.add_argument("--pilot-per-language", type=int, default=5, help="Pilot sessions per language.")
    parser.add_argument(
        "--total-per-language",
        type=int,
        default=30,
        help="Total target sessions per language, including the pilot.",
    )
    parser.add_argument(
        "--materialize-stubs",
        action="store_true",
        help="Create transcript and label starter files for every planned session.",
    )
    parser.add_argument(
        "--refresh-metadata",
        action="store_true",
        help="Rewrite data/gold/metadata.csv from the planned registry, even if it already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root)
    rows = build_session_rows(
        pilot_per_language=args.pilot_per_language,
        total_per_language=args.total_per_language,
    )
    registry_path = write_session_registry(rows, gold_root)
    plan_path = write_collection_plan(build_collection_plan(rows), gold_root)
    metadata_path = write_metadata_sheet(
        build_metadata_rows(rows),
        gold_root,
        overwrite=args.refresh_metadata,
    )
    if args.materialize_stubs:
        created = materialize_starter_files(rows)
        registry_path = write_session_registry(rows, gold_root)
        print(json.dumps(created, indent=2, ensure_ascii=False))
    print(f"wrote {len(rows)} planned sessions to {registry_path}")
    print(f"wrote collection plan to {plan_path}")
    print(f"wrote metadata template to {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
