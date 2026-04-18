#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"

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

METADATA_REQUIRED_FIELDS = [
    "session_id",
    "participant_id",
    "language",
    "consent_recorded",
    "collection_source",
]


def annotation_is_human(payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("is_placeholder") is True:
        return False
    annotator_id = str(payload.get("annotator_id", "")).strip().upper()
    provenance = str(payload.get("annotation_provenance", "")).strip().lower()

    if annotator_id.startswith(("AUTO", "TBD", "BOT", "MODEL")):
        return False
    machine_tokens = ("machine", "bootstrap", "synthetic", "heuristic", "auto")
    if any(token in provenance for token in machine_tokens):
        return False
    return True


def load_registry(registry_path: Path) -> list[dict[str, str]]:
    with registry_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_metadata(metadata_path: Path) -> dict[str, dict[str, str]]:
    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["session_id"]: row for row in rows if row.get("session_id")}


def resolve_project_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else PROJECT_ROOT / path


def validate_label_payload(
    payload: dict,
    expected_session_id: str,
    *,
    require_human_annotation: bool = False,
    label_scope: str = "label",
) -> list[str]:
    issues: list[str] = []
    if payload.get("is_placeholder") is True:
        issues.append("placeholder label file not yet finalized")
    if require_human_annotation and not annotation_is_human(payload):
        issues.append(f"{label_scope} is not human-annotated")
    if payload.get("session_id") != expected_session_id:
        issues.append(f"label session_id mismatch: expected {expected_session_id}")
    items = payload.get("items")
    if not isinstance(items, list):
        issues.append("label payload missing items list")
        return issues
    item_ids = [item.get("item_id") for item in items if isinstance(item, dict)]
    missing = [item_id for item_id in EXPECTED_ITEM_IDS if item_id not in item_ids]
    if missing:
        issues.append(f"missing item labels: {', '.join(missing)}")
    for item in items:
        if not isinstance(item, dict):
            issues.append("label item is not an object")
            continue
        value = item.get("value")
        if not isinstance(value, int) or value < 0 or value > 3:
            issues.append(f"invalid value for {item.get('item_id')}: {value}")
        if not item.get("evidence_quote", ""):
            issues.append(f"missing evidence_quote for {item.get('item_id')}")
    safety = payload.get("safety", {})
    if safety.get("level") not in {"none", "review", "urgent"}:
        issues.append(f"invalid safety level: {safety.get('level')}")
    return issues


def validate_metadata_row(row: dict[str, str], expected_session_id: str, expected_language: str) -> list[str]:
    issues: list[str] = []
    for field in METADATA_REQUIRED_FIELDS:
        if not row.get(field):
            issues.append(f"missing metadata field: {field}")
    if row.get("session_id") != expected_session_id:
        issues.append(f"metadata session_id mismatch: expected {expected_session_id}")
    if row.get("language") != expected_language:
        issues.append(f"metadata language mismatch: expected {expected_language}")
    if row.get("collection_source") == "placeholder":
        issues.append("placeholder metadata row not yet finalized")
    if row.get("consent_recorded") == "pending":
        issues.append("metadata consent not yet finalized")
    if not row.get("age_years") and not row.get("age_band"):
        issues.append("metadata missing age_years/age_band")
    if not row.get("occupation"):
        issues.append("metadata missing occupation")
    if not row.get("living_situation"):
        issues.append("metadata missing living_situation")
    return issues


def summarize_gold_dataset(
    rows: list[dict[str, str]],
    *,
    gold_root: Path = DEFAULT_GOLD_ROOT,
    require_human_labels: bool = False,
) -> dict:
    metadata_index = load_metadata(gold_root / "metadata.csv")
    summary = {
        "total_sessions": len(rows),
        "by_language": dict(Counter(row["language"] for row in rows)),
        "by_cohort": dict(Counter(row["cohort"] for row in rows)),
        "audio_present": 0,
        "metadata_rows_present": 0,
        "transcripts_present": 0,
        "annotator_a_present": 0,
        "annotator_b_present": 0,
        "adjudicated_present": 0,
        "human_annotator_a_present": 0,
        "human_annotator_b_present": 0,
        "human_adjudicated_present": 0,
        "sessions_with_human_label_stack": 0,
        "machine_generated_label_files": 0,
        "metadata_placeholders": 0,
        "transcript_placeholders": 0,
        "label_placeholders": 0,
        "require_human_labels": require_human_labels,
        "fully_complete": 0,
        "issues": [],
    }

    for row in rows:
        session_issues: list[str] = []
        metadata_row = metadata_index.get(row["session_id"])
        audio_path = resolve_project_path(row["audio_file"])
        transcript_path = resolve_project_path(row["transcript_file"])
        annotator_a_path = resolve_project_path(row["annotator_a_file"])
        annotator_b_path = resolve_project_path(row["annotator_b_file"])
        adjudicated_path = resolve_project_path(row["adjudicated_label_file"])

        audio_exists = audio_path.exists()
        transcript_exists = transcript_path.exists()
        annotator_a_exists = annotator_a_path.exists()
        annotator_b_exists = annotator_b_path.exists()
        adjudicated_exists = adjudicated_path.exists()

        summary["audio_present"] += int(audio_exists)
        summary["transcripts_present"] += int(transcript_exists)
        summary["annotator_a_present"] += int(annotator_a_exists)
        summary["annotator_b_present"] += int(annotator_b_exists)
        summary["adjudicated_present"] += int(adjudicated_exists)
        summary["metadata_rows_present"] += int(metadata_row is not None)
        is_human_a = False
        is_human_b = False
        is_human_adj = False

        if not audio_exists:
            session_issues.append("missing audio")
        if metadata_row is None:
            session_issues.append("missing metadata row")
        else:
            metadata_issues = validate_metadata_row(metadata_row, row["session_id"], row["language"])
            if "placeholder metadata row not yet finalized" in metadata_issues:
                summary["metadata_placeholders"] += 1
            session_issues.extend(metadata_issues)
        if not transcript_exists:
            session_issues.append("missing transcript")
        else:
            try:
                transcript_payload = json.loads(transcript_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                session_issues.append(f"invalid transcript json: {exc}")
            else:
                if transcript_payload.get("is_placeholder") is True:
                    summary["transcript_placeholders"] += 1
                    session_issues.append("placeholder transcript not yet finalized")
                if transcript_payload.get("session_id") != row["session_id"]:
                    session_issues.append("transcript session_id mismatch")
        if not annotator_a_exists:
            session_issues.append("missing annotator_a labels")
        else:
            try:
                annotator_a_payload = json.loads(annotator_a_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                session_issues.append(f"invalid annotator_a json: {exc}")
            else:
                if annotator_a_payload.get("is_placeholder") is True:
                    summary["label_placeholders"] += 1
                is_human_a = annotation_is_human(annotator_a_payload)
                summary["human_annotator_a_present"] += int(is_human_a)
                if not is_human_a:
                    summary["machine_generated_label_files"] += 1
                if require_human_labels and not is_human_a:
                    session_issues.append("annotator_a label is not human-annotated")
        if not annotator_b_exists:
            session_issues.append("missing annotator_b labels")
        else:
            try:
                annotator_b_payload = json.loads(annotator_b_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                session_issues.append(f"invalid annotator_b json: {exc}")
            else:
                if annotator_b_payload.get("is_placeholder") is True:
                    summary["label_placeholders"] += 1
                is_human_b = annotation_is_human(annotator_b_payload)
                summary["human_annotator_b_present"] += int(is_human_b)
                if not is_human_b:
                    summary["machine_generated_label_files"] += 1
                if require_human_labels and not is_human_b:
                    session_issues.append("annotator_b label is not human-annotated")
        if not adjudicated_exists:
            session_issues.append("missing adjudicated labels")

        if adjudicated_exists:
            try:
                payload = json.loads(adjudicated_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                session_issues.append(f"invalid adjudicated json: {exc}")
            else:
                if payload.get("is_placeholder") is True:
                    summary["label_placeholders"] += 1
                is_human_adj = annotation_is_human(payload)
                summary["human_adjudicated_present"] += int(is_human_adj)
                if not is_human_adj:
                    summary["machine_generated_label_files"] += 1
                session_issues.extend(
                    validate_label_payload(
                        payload,
                        row["session_id"],
                        require_human_annotation=require_human_labels,
                        label_scope="adjudicated label",
                    )
                )

        if is_human_a and is_human_b and is_human_adj:
            summary["sessions_with_human_label_stack"] += 1

        if not session_issues:
            summary["fully_complete"] += 1
        else:
            summary["issues"].append({"session_id": row["session_id"], "issues": session_issues})

    return summary


def render_markdown(summary: dict) -> str:
    lines = [
        "# Gold Dataset Status",
        "",
        f"- Total planned sessions: `{summary['total_sessions']}`",
        f"- Audio present: `{summary['audio_present']}`",
        f"- Metadata rows present: `{summary['metadata_rows_present']}`",
        f"- Transcripts present: `{summary['transcripts_present']}`",
        f"- Annotator A files present: `{summary['annotator_a_present']}`",
        f"- Annotator B files present: `{summary['annotator_b_present']}`",
        f"- Adjudicated files present: `{summary['adjudicated_present']}`",
        f"- Human annotator A files: `{summary['human_annotator_a_present']}`",
        f"- Human annotator B files: `{summary['human_annotator_b_present']}`",
        f"- Human adjudicated files: `{summary['human_adjudicated_present']}`",
        f"- Sessions with full human label stack: `{summary['sessions_with_human_label_stack']}`",
        f"- Machine-generated label files: `{summary['machine_generated_label_files']}`",
        f"- Placeholder metadata rows: `{summary['metadata_placeholders']}`",
        f"- Placeholder transcripts: `{summary['transcript_placeholders']}`",
        f"- Placeholder label files: `{summary['label_placeholders']}`",
        f"- Fully complete sessions: `{summary['fully_complete']}`",
        "",
        "## Planned Coverage",
        "",
    ]
    for language, count in sorted(summary["by_language"].items()):
        lines.append(f"- {language}: `{count}`")
    lines.extend(["", "## Cohorts", ""])
    for cohort, count in sorted(summary["by_cohort"].items()):
        lines.append(f"- {cohort}: `{count}`")
    lines.extend(["", "## Open Issues", ""])
    if not summary["issues"]:
        lines.append("- None")
        return "\n".join(lines) + "\n"
    for issue in summary["issues"][:20]:
        lines.append(f"- {issue['session_id']}: {', '.join(issue['issues'])}")
    if len(summary["issues"]) > 20:
        lines.append(f"- ...and `{len(summary['issues']) - 20}` more sessions with open issues")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate planned and collected gold-data assets.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Gold-data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Directory for status reports.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every planned session is complete.")
    parser.add_argument(
        "--require-human-labels",
        action="store_true",
        help="Treat machine/bootstrap annotations as incomplete and require human annotator A/B/adjudicated labels.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root)
    report_dir = Path(args.report_dir)
    registry_path = gold_root / "session_registry.csv"
    if not registry_path.exists():
        raise SystemExit(f"missing session registry: {registry_path}")
    rows = load_registry(registry_path)
    summary = summarize_gold_dataset(
        rows,
        gold_root=gold_root,
        require_human_labels=args.require_human_labels,
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "gold_dataset_status.json"
    md_path = report_dir / "gold_dataset_status.md"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    if args.strict and summary["fully_complete"] != summary["total_sessions"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
