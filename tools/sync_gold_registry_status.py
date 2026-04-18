#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.init_gold_dataset import FIELDNAMES, write_session_registry
from tools.validate_gold_dataset import annotation_is_human, load_metadata, load_registry, resolve_project_path

DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"


def _artifact_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "present"
    return "placeholder" if payload.get("is_placeholder") else "finalized"


def _label_status(path: Path, *, require_human_labels: bool) -> str:
    if not path.exists():
        return "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "present"
    if payload.get("is_placeholder"):
        return "placeholder"
    if require_human_labels and not annotation_is_human(payload):
        return "machine"
    return "finalized"


def _metadata_status(metadata_row: dict[str, str] | None) -> str:
    if metadata_row is None:
        return "missing"
    if metadata_row.get("collection_source") == "placeholder":
        return "placeholder"
    if metadata_row.get("consent_recorded") in {"", "pending"}:
        return "placeholder"
    if not (metadata_row.get("age_years") or metadata_row.get("age_band")):
        return "placeholder"
    if not metadata_row.get("occupation") or not metadata_row.get("living_situation"):
        return "placeholder"
    return "finalized"


def _collection_status(
    *,
    audio_status: str,
    metadata_status: str,
    transcript_status: str,
    annotator_a_status: str,
    annotator_b_status: str,
    adjudication_status: str,
) -> str:
    statuses = [
        audio_status,
        metadata_status,
        transcript_status,
        annotator_a_status,
        annotator_b_status,
        adjudication_status,
    ]
    if all(status == "finalized" or status == "present" for status in statuses):
        return "complete"
    if any(status in {"finalized", "present"} for status in statuses):
        return "in_progress"
    return "planned"


def _qa_status(
    *,
    audio_status: str,
    metadata_status: str,
    transcript_status: str,
    annotator_a_status: str,
    annotator_b_status: str,
    adjudication_status: str,
) -> str:
    collection_ready = all(status in {"finalized", "present"} for status in [audio_status, metadata_status, transcript_status])
    dual_annotation_ready = all(status == "finalized" for status in [annotator_a_status, annotator_b_status])

    if all(status in {"finalized", "present"} for status in [audio_status, metadata_status, transcript_status, annotator_a_status, annotator_b_status, adjudication_status]):
        return "complete"
    if dual_annotation_ready and adjudication_status != "finalized":
        return "ready_for_adjudication"
    if collection_ready and (annotator_a_status != "finalized" or annotator_b_status != "finalized"):
        return "ready_for_annotation"
    if audio_status != "present" or metadata_status != "finalized" or transcript_status != "finalized":
        return "ready_for_collection"
    return "blocked"


def sync_registry(
    rows: list[dict[str, str]],
    *,
    gold_root: Path,
    require_human_labels: bool = False,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    metadata_index = load_metadata(gold_root / "metadata.csv")
    counts = {
        "rows_updated": 0,
        "planned": 0,
        "in_progress": 0,
        "complete": 0,
        "ready_for_collection": 0,
        "ready_for_annotation": 0,
        "ready_for_adjudication": 0,
        "qa_complete": 0,
    }

    updated_rows: list[dict[str, str]] = []
    for row in rows:
        row = dict(row)
        audio_status = "present" if resolve_project_path(row["audio_file"]).exists() else "missing"
        metadata_status = _metadata_status(metadata_index.get(row["session_id"]))
        transcript_status = _artifact_status(resolve_project_path(row["transcript_file"]))
        annotator_a_status = _label_status(
            resolve_project_path(row["annotator_a_file"]),
            require_human_labels=require_human_labels,
        )
        annotator_b_status = _label_status(
            resolve_project_path(row["annotator_b_file"]),
            require_human_labels=require_human_labels,
        )
        adjudication_status = _label_status(
            resolve_project_path(row["adjudicated_label_file"]),
            require_human_labels=require_human_labels,
        )
        collection_status = _collection_status(
            audio_status=audio_status,
            metadata_status=metadata_status,
            transcript_status=transcript_status,
            annotator_a_status=annotator_a_status,
            annotator_b_status=annotator_b_status,
            adjudication_status=adjudication_status,
        )
        qa_status = _qa_status(
            audio_status=audio_status,
            metadata_status=metadata_status,
            transcript_status=transcript_status,
            annotator_a_status=annotator_a_status,
            annotator_b_status=annotator_b_status,
            adjudication_status=adjudication_status,
        )

        row.update(
            {
                "collection_status": collection_status,
                "audio_status": audio_status,
                "metadata_status": metadata_status,
                "transcript_status": transcript_status,
                "annotator_a_status": annotator_a_status,
                "annotator_b_status": annotator_b_status,
                "adjudication_status": adjudication_status,
                "qa_status": qa_status,
            }
        )
        updated_rows.append(row)
        counts["rows_updated"] += 1
        counts[collection_status] = counts.get(collection_status, 0) + 1
        counts[qa_status] = counts.get(qa_status, 0) + 1
        if qa_status == "complete":
            counts["qa_complete"] += 1

    return updated_rows, counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync session_registry.csv statuses from real gold-data assets.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Gold-data root directory.")
    parser.add_argument(
        "--require-human-labels",
        action="store_true",
        help="Treat machine/bootstrap labels as incomplete for registry QA status.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root)
    rows = load_registry(gold_root / "session_registry.csv")
    updated_rows, counts = sync_registry(
        rows,
        gold_root=gold_root,
        require_human_labels=args.require_human_labels,
    )
    counts["require_human_labels"] = bool(args.require_human_labels)
    write_session_registry(updated_rows, gold_root)
    print(json.dumps(counts, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
