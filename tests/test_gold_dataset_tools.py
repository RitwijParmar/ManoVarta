import json
from datetime import date
from pathlib import Path

from tools.build_gold_annotation_packets import build_packets
from tools.generate_gold_progress_dashboard import build_dashboard
from tools.generate_gold_adjudication_report import build_adjudication_summary
from tools.generate_reviewer_workflow_pack import build_reviewer_workflow_pack
from tools.init_gold_dataset import (
    build_collection_plan,
    build_metadata_rows,
    build_session_rows,
    materialize_starter_files,
    write_metadata_sheet,
    write_collection_plan,
    write_session_registry,
)
from tools.sync_gold_registry_status import sync_registry
from tools.validate_gold_dataset import EXPECTED_ITEM_IDS, load_registry, summarize_gold_dataset


def _rebase_paths(rows: list[dict[str, str]], root: Path) -> list[dict[str, str]]:
    rebased: list[dict[str, str]] = []
    for row in rows:
        updated = dict(row)
        updated["audio_file"] = str(root / f"{row['session_id']}.wav")
        updated["transcript_file"] = str(root / f"{row['session_id']}.transcript.json")
        updated["annotator_a_file"] = str(root / f"{row['session_id']}.annotator_a.json")
        updated["annotator_b_file"] = str(root / f"{row['session_id']}.annotator_b.json")
        updated["adjudicated_label_file"] = str(root / f"{row['session_id']}.adjudicated.json")
        rebased.append(updated)
    return rebased


def test_build_session_rows_creates_pilot_and_expansion_balanced():
    rows = build_session_rows(pilot_per_language=5, total_per_language=30)

    assert len(rows) == 60
    assert sum(1 for row in rows if row["language"] == "en") == 30
    assert sum(1 for row in rows if row["language"] == "hi") == 30
    assert sum(1 for row in rows if row["cohort"] == "pilot") == 10
    assert sum(1 for row in rows if row["cohort"] == "expansion") == 50
    assert rows[0]["session_id"] == "MVGOLD-EN-001"
    assert rows[-1]["session_id"] == "MVGOLD-HI-030"


def test_write_registry_and_plan_round_trip(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = build_session_rows(pilot_per_language=5, total_per_language=30)

    registry_path = write_session_registry(rows, gold_root)
    plan_path = write_collection_plan(build_collection_plan(rows), gold_root)

    loaded_rows = load_registry(registry_path)
    loaded_plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert len(loaded_rows) == 60
    assert loaded_plan["total_sessions"] == 60
    assert len(loaded_plan["pilot_sessions"]) == 10
    assert len(loaded_plan["expansion_sessions"]) == 50


def test_summarize_gold_dataset_reports_missing_artifacts_for_planned_rows(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=2, languages=("en", "hi")),
        tmp_path / "artifacts",
    )
    registry_path = write_session_registry(rows, gold_root)

    summary = summarize_gold_dataset(load_registry(registry_path), gold_root=gold_root)

    assert summary["total_sessions"] == 4
    assert summary["audio_present"] == 0
    assert summary["metadata_rows_present"] == 0
    assert summary["transcripts_present"] == 0
    assert summary["fully_complete"] == 0
    assert len(summary["issues"]) == 4


def test_materialized_stubs_are_present_but_not_counted_complete(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=1, languages=("en", "hi")),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)
    write_metadata_sheet(build_metadata_rows(rows), gold_root)

    created = materialize_starter_files(rows)
    summary = summarize_gold_dataset(load_registry(gold_root / "session_registry.csv"), gold_root=gold_root)

    assert created["transcripts_created"] == 2
    assert created["annotator_a_created"] == 2
    assert created["annotator_b_created"] == 2
    assert created["adjudicated_created"] == 2
    assert summary["metadata_rows_present"] == 2
    assert summary["metadata_placeholders"] == 2
    assert summary["transcripts_present"] == 2
    assert summary["transcript_placeholders"] == 2
    assert summary["label_placeholders"] == 6
    assert summary["fully_complete"] == 0


def test_build_gold_annotation_packets_creates_stage_outputs(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=1, languages=("en",)),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)
    write_metadata_sheet(build_metadata_rows(rows), gold_root)
    materialize_starter_files(rows)

    output_dir = tmp_path / "packets"
    created = build_packets(
        load_registry(gold_root / "session_registry.csv"),
        gold_root=gold_root,
        output_dir=output_dir,
        stages=("annotator_a", "adjudication"),
    )

    assert created["annotator_a"] == 1
    assert created["adjudication"] == 1
    assert (output_dir / "annotator_a" / "MVGOLD-EN-001.annotator_a.json").exists()
    assert (output_dir / "annotator_a" / "MVGOLD-EN-001.annotator_a.md").exists()
    assert (output_dir / "adjudication" / "MVGOLD-EN-001.adjudication.json").exists()


def test_build_adjudication_summary_flags_placeholder_annotations(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=1, languages=("en",)),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)
    write_metadata_sheet(build_metadata_rows(rows), gold_root)
    materialize_starter_files(rows)

    summary = build_adjudication_summary(load_registry(gold_root / "session_registry.csv"))

    assert summary["total_sessions"] == 1
    assert summary["sessions_with_dual_annotations"] == 1
    assert summary["sessions_blocked_by_placeholders"] == 1
    assert summary["sessions_with_open_disagreements"] == 0
    assert summary["overall_agreement"]["n_pairs"] == 16
    assert summary["overall_agreement"]["cohen_kappa"] == 1.0


def test_sync_registry_updates_statuses_from_placeholder_assets(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=1, languages=("en",)),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)
    write_metadata_sheet(build_metadata_rows(rows), gold_root)
    materialize_starter_files(rows)

    updated_rows, counts = sync_registry(load_registry(gold_root / "session_registry.csv"), gold_root=gold_root)

    assert counts["rows_updated"] == 1
    assert counts["planned"] == 1
    assert counts["in_progress"] == 0
    assert counts["ready_for_collection"] == 1
    row = updated_rows[0]
    assert row["metadata_status"] == "placeholder"
    assert row["transcript_status"] == "placeholder"
    assert row["annotator_a_status"] == "placeholder"
    assert row["qa_status"] == "ready_for_collection"


def test_sync_registry_can_require_human_labels_for_qa_completion(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=1, languages=("en",)),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)
    _write_finalized_metadata(rows, gold_root)

    row = rows[0]
    Path(row["audio_file"]).parent.mkdir(parents=True, exist_ok=True)
    Path(row["audio_file"]).write_bytes(b"RIFF")
    transcript_payload = {
        "session_id": row["session_id"],
        "language": "en",
        "cohort": row["cohort"],
        "is_placeholder": False,
        "turns": [{"turn_id": "u1", "speaker": "user", "text": "I feel tense."}],
    }
    Path(row["transcript_file"]).write_text(json.dumps(transcript_payload, indent=2) + "\n", encoding="utf-8")

    _write_label(
        Path(row["annotator_a_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-A",
        stage="annotator_a",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row["annotator_b_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-B",
        stage="annotator_b",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row["adjudicated_label_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-ADJ",
        stage="adjudicated",
        provenance="machine_bootstrap_adjudication",
    )

    strict_rows, strict_counts = sync_registry(
        load_registry(gold_root / "session_registry.csv"),
        gold_root=gold_root,
        require_human_labels=True,
    )
    strict_row = strict_rows[0]
    assert strict_row["annotator_a_status"] == "machine"
    assert strict_row["annotator_b_status"] == "machine"
    assert strict_row["adjudication_status"] == "machine"
    assert strict_row["qa_status"] == "ready_for_annotation"
    assert strict_row["collection_status"] == "in_progress"
    assert strict_counts["ready_for_annotation"] == 1

    _write_label(
        Path(row["annotator_a_file"]),
        session_id=row["session_id"],
        annotator_id="R-A1",
        stage="annotator_a",
        provenance="human_dual_annotation",
    )
    _write_label(
        Path(row["annotator_b_file"]),
        session_id=row["session_id"],
        annotator_id="R-B1",
        stage="annotator_b",
        provenance="human_dual_annotation",
    )
    strict_rows, _ = sync_registry(
        load_registry(gold_root / "session_registry.csv"),
        gold_root=gold_root,
        require_human_labels=True,
    )
    strict_row = strict_rows[0]
    assert strict_row["annotator_a_status"] == "finalized"
    assert strict_row["annotator_b_status"] == "finalized"
    assert strict_row["adjudication_status"] == "machine"
    assert strict_row["qa_status"] == "ready_for_adjudication"

    _write_label(
        Path(row["adjudicated_label_file"]),
        session_id=row["session_id"],
        annotator_id="R-ADJ1",
        stage="adjudicated",
        provenance="human_adjudication",
    )
    strict_rows, strict_counts = sync_registry(
        load_registry(gold_root / "session_registry.csv"),
        gold_root=gold_root,
        require_human_labels=True,
    )
    strict_row = strict_rows[0]
    assert strict_row["adjudication_status"] == "finalized"
    assert strict_row["qa_status"] == "complete"
    assert strict_counts["qa_complete"] == 1


def test_build_dashboard_summarizes_registry_states():
    rows = [
        {
            "session_id": "MVGOLD-EN-001",
            "language": "en",
            "cohort": "pilot",
            "target_primary_domain": "mood",
            "collection_status": "in_progress",
            "qa_status": "ready_for_collection",
        },
        {
            "session_id": "MVGOLD-HI-001",
            "language": "hi",
            "cohort": "pilot",
            "target_primary_domain": "sleep",
            "collection_status": "complete",
            "qa_status": "complete",
        },
    ]

    dashboard = build_dashboard(rows)

    assert dashboard["total_sessions"] == 2
    assert dashboard["by_language"] == {"en": 1, "hi": 1}
    assert dashboard["by_collection_status"]["complete"] == 1
    assert dashboard["by_qa_status"]["ready_for_collection"] == 1
    assert dashboard["completed"] == ["MVGOLD-HI-001"]


def _write_label(path: Path, *, session_id: str, annotator_id: str, stage: str, provenance: str) -> None:
    payload = {
        "session_id": session_id,
        "language": "en",
        "annotator_id": annotator_id,
        "annotation_stage": stage,
        "recall_window_days": 14,
        "is_placeholder": False,
        "annotation_provenance": provenance,
        "items": [
            {
                "item_id": item_id,
                "value": 0,
                "confidence": "low",
                "evidence_quote": "no symptom evidence",
                "turn_id": "u1",
                "speaker": "user",
                "notes": "",
            }
            for item_id in EXPECTED_ITEM_IDS
        ],
        "safety": {"level": "none", "evidence_quote": "no safety concern", "notes": ""},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_finalized_metadata(rows: list[dict[str, str]], gold_root: Path) -> None:
    metadata_rows = build_metadata_rows(rows)
    for row in metadata_rows:
        row["participant_id"] = row["session_id"].replace("MVGOLD-", "P-")
        row["age_band"] = "adult"
        row["occupation"] = "worker"
        row["living_situation"] = "family"
        row["support_system"] = "present"
        row["consent_recorded"] = "yes"
        row["collection_source"] = "test_fixture"
        row["notes"] = "finalized test metadata"
    write_metadata_sheet(metadata_rows, gold_root, overwrite=True)


def test_summarize_gold_dataset_can_require_human_labels(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=1, languages=("en",)),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)
    _write_finalized_metadata(rows, gold_root)

    row = rows[0]
    Path(row["audio_file"]).parent.mkdir(parents=True, exist_ok=True)
    Path(row["audio_file"]).write_bytes(b"RIFF")
    transcript_payload = {
        "session_id": row["session_id"],
        "language": "en",
        "cohort": row["cohort"],
        "is_placeholder": False,
        "turns": [{"turn_id": "u1", "speaker": "user", "text": "I feel okay."}],
    }
    Path(row["transcript_file"]).write_text(json.dumps(transcript_payload, indent=2) + "\n", encoding="utf-8")

    _write_label(
        Path(row["annotator_a_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-A",
        stage="annotator_a",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row["annotator_b_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-B",
        stage="annotator_b",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row["adjudicated_label_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-ADJ",
        stage="adjudicated",
        provenance="machine_bootstrap_adjudication",
    )

    summary_default = summarize_gold_dataset(load_registry(gold_root / "session_registry.csv"), gold_root=gold_root)
    assert summary_default["fully_complete"] == 1

    summary_human_required = summarize_gold_dataset(
        load_registry(gold_root / "session_registry.csv"),
        gold_root=gold_root,
        require_human_labels=True,
    )
    assert summary_human_required["fully_complete"] == 0
    assert summary_human_required["sessions_with_human_label_stack"] == 0
    assert summary_human_required["machine_generated_label_files"] == 3
    assert "annotator_a label is not human-annotated" in summary_human_required["issues"][0]["issues"]


def test_build_reviewer_workflow_pack_generates_queues_and_batches(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=2, languages=("en",)),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)

    row_human = rows[0]
    row_machine = rows[1]
    _write_label(
        Path(row_human["annotator_a_file"]),
        session_id=row_human["session_id"],
        annotator_id="R-A1",
        stage="annotator_a",
        provenance="human_dual_annotation",
    )
    _write_label(
        Path(row_human["annotator_b_file"]),
        session_id=row_human["session_id"],
        annotator_id="R-B1",
        stage="annotator_b",
        provenance="human_dual_annotation",
    )
    _write_label(
        Path(row_human["adjudicated_label_file"]),
        session_id=row_human["session_id"],
        annotator_id="R-ADJ1",
        stage="adjudicated",
        provenance="human_adjudication",
    )
    _write_label(
        Path(row_machine["annotator_a_file"]),
        session_id=row_machine["session_id"],
        annotator_id="AUTO-A",
        stage="annotator_a",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row_machine["annotator_b_file"]),
        session_id=row_machine["session_id"],
        annotator_id="AUTO-B",
        stage="annotator_b",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row_machine["adjudicated_label_file"]),
        session_id=row_machine["session_id"],
        annotator_id="AUTO-ADJ",
        stage="adjudicated",
        provenance="machine_bootstrap",
    )

    pack = build_reviewer_workflow_pack(
        load_registry(gold_root / "session_registry.csv"),
        annotator_a_capacity=1,
        annotator_b_capacity=1,
        adjudicator_capacity=1,
        start_date_value=date(2026, 4, 10),
    )

    assert [row["session_id"] for row in pack["queues"]["annotator_a"]] == [row_machine["session_id"]]
    assert [row["session_id"] for row in pack["queues"]["annotator_b"]] == [row_machine["session_id"]]
    assert pack["queues"]["adjudicator"] == []
    assert pack["progress_tracker"]["fully_human_complete_sessions"] == 1
    assert pack["daily_batches"]["annotator_a"][0]["session_ids"] == [row_machine["session_id"]]


def test_build_adjudication_summary_human_only_metrics_skips_machine_annotations(tmp_path: Path):
    gold_root = tmp_path / "gold"
    rows = _rebase_paths(
        build_session_rows(pilot_per_language=1, total_per_language=1, languages=("en",)),
        tmp_path / "artifacts",
    )
    write_session_registry(rows, gold_root)
    row = rows[0]
    _write_label(
        Path(row["annotator_a_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-A",
        stage="annotator_a",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row["annotator_b_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-B",
        stage="annotator_b",
        provenance="machine_bootstrap",
    )
    _write_label(
        Path(row["adjudicated_label_file"]),
        session_id=row["session_id"],
        annotator_id="AUTO-ADJ",
        stage="adjudicated",
        provenance="machine_bootstrap_adjudication",
    )

    summary = build_adjudication_summary(
        load_registry(gold_root / "session_registry.csv"),
        human_only_metrics=True,
    )
    assert summary["sessions_used_for_metrics"] == 0
    assert summary["sessions_skipped_for_metrics_nonhuman"] == 1
