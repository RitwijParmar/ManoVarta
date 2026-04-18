#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_gold_dataset import annotation_is_human, load_registry, resolve_project_path

DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"


def _load_label(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _score(value: object) -> int | None:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0 or numeric > 3:
        return None
    return numeric


def _has_disagreement(annotator_a: dict | None, annotator_b: dict | None) -> bool:
    if not isinstance(annotator_a, dict) or not isinstance(annotator_b, dict):
        return False
    a_items = {item.get("item_id"): item for item in annotator_a.get("items", []) if isinstance(item, dict)}
    b_items = {item.get("item_id"): item for item in annotator_b.get("items", []) if isinstance(item, dict)}
    for item_id in set(a_items) | set(b_items):
        a_val = _score(a_items.get(item_id, {}).get("value"))
        b_val = _score(b_items.get(item_id, {}).get("value"))
        if a_val is None or b_val is None:
            continue
        if a_val != b_val:
            return True
    a_safety = (annotator_a.get("safety") or {}).get("level")
    b_safety = (annotator_b.get("safety") or {}).get("level")
    return a_safety != b_safety


def _priority_weight(row: dict[str, str]) -> int:
    band = row.get("target_risk_band", "")
    if band == "urgent_candidate":
        return 0
    if band == "review_candidate":
        return 1
    return 2


def _queue_entry(row: dict[str, str], reason: str) -> dict[str, object]:
    return {
        "session_id": row["session_id"],
        "language": row["language"],
        "cohort": row["cohort"],
        "target_primary_domain": row["target_primary_domain"],
        "target_risk_band": row["target_risk_band"],
        "target_order": int(row.get("target_order", "0") or 0),
        "reason": reason,
        "priority_weight": _priority_weight(row),
    }


def _sort_queue(queue: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        queue,
        key=lambda row: (
            int(row["priority_weight"]),
            int(row["target_order"]),
            str(row["session_id"]),
        ),
    )


def _build_daily_batches(
    queue: list[dict[str, object]],
    *,
    capacity_per_day: int,
    start_date: date,
) -> list[dict[str, object]]:
    if capacity_per_day <= 0:
        return []
    batches: list[dict[str, object]] = []
    for index in range(0, len(queue), capacity_per_day):
        batch = queue[index : index + capacity_per_day]
        batch_date = start_date + timedelta(days=index // capacity_per_day)
        batches.append(
            {
                "date": batch_date.isoformat(),
                "capacity": capacity_per_day,
                "load": len(batch),
                "session_ids": [str(item["session_id"]) for item in batch],
            }
        )
    return batches


def _write_queue_csv(queue: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "session_id",
        "language",
        "cohort",
        "target_primary_domain",
        "target_risk_band",
        "target_order",
        "reason",
        "priority_weight",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(queue)


def build_reviewer_workflow_pack(
    rows: list[dict[str, str]],
    *,
    annotator_a_capacity: int,
    annotator_b_capacity: int,
    adjudicator_capacity: int,
    start_date_value: date,
) -> dict:
    annotator_a_queue: list[dict[str, object]] = []
    annotator_b_queue: list[dict[str, object]] = []
    adjudicator_queue: list[dict[str, object]] = []

    human_a_complete = 0
    human_b_complete = 0
    human_adjudication_complete = 0
    dual_human_ready = 0
    fully_human_complete_sessions = 0
    sessions_with_dual_human_disagreement = 0

    for row in rows:
        annotator_a = _load_label(resolve_project_path(row["annotator_a_file"]))
        annotator_b = _load_label(resolve_project_path(row["annotator_b_file"]))
        adjudicated = _load_label(resolve_project_path(row["adjudicated_label_file"]))

        human_a = annotation_is_human(annotator_a)
        human_b = annotation_is_human(annotator_b)
        human_adj = annotation_is_human(adjudicated)

        human_a_complete += int(human_a)
        human_b_complete += int(human_b)
        human_adjudication_complete += int(human_adj)

        if not human_a:
            annotator_a_queue.append(_queue_entry(row, "missing human annotator A label"))
        if not human_b:
            annotator_b_queue.append(_queue_entry(row, "missing human annotator B label"))

        if human_a and human_b:
            dual_human_ready += 1
            disagreement = _has_disagreement(annotator_a, annotator_b)
            if disagreement:
                sessions_with_dual_human_disagreement += 1
            if not human_adj:
                reason = "missing human adjudication label"
                if disagreement:
                    reason = "dual human labels disagree; adjudication required"
                adjudicator_queue.append(_queue_entry(row, reason))

        if human_a and human_b and human_adj:
            fully_human_complete_sessions += 1

    annotator_a_queue = _sort_queue(annotator_a_queue)
    annotator_b_queue = _sort_queue(annotator_b_queue)
    adjudicator_queue = _sort_queue(adjudicator_queue)

    a_batches = _build_daily_batches(
        annotator_a_queue,
        capacity_per_day=annotator_a_capacity,
        start_date=start_date_value,
    )
    b_batches = _build_daily_batches(
        annotator_b_queue,
        capacity_per_day=annotator_b_capacity,
        start_date=start_date_value,
    )
    adj_batches = _build_daily_batches(
        adjudicator_queue,
        capacity_per_day=adjudicator_capacity,
        start_date=start_date_value,
    )

    total_sessions = len(rows)
    progress_tracker = {
        "total_sessions": total_sessions,
        "human_annotator_a_complete": human_a_complete,
        "human_annotator_b_complete": human_b_complete,
        "human_adjudication_complete": human_adjudication_complete,
        "dual_human_ready_for_adjudication": dual_human_ready,
        "sessions_with_dual_human_disagreement": sessions_with_dual_human_disagreement,
        "fully_human_complete_sessions": fully_human_complete_sessions,
        "annotator_a_remaining": len(annotator_a_queue),
        "annotator_b_remaining": len(annotator_b_queue),
        "adjudicator_remaining": len(adjudicator_queue),
        "human_completion_rate": round((fully_human_complete_sessions / total_sessions), 4) if total_sessions else 0.0,
        "estimated_days_remaining": {
            "annotator_a": len(a_batches),
            "annotator_b": len(b_batches),
            "adjudicator": len(adj_batches),
            "overall_pipeline_days": max([len(a_batches), len(b_batches), len(adj_batches)], default=0),
        },
    }

    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "queues": {
            "annotator_a": annotator_a_queue,
            "annotator_b": annotator_b_queue,
            "adjudicator": adjudicator_queue,
        },
        "daily_batches": {
            "annotator_a": a_batches,
            "annotator_b": b_batches,
            "adjudicator": adj_batches,
        },
        "progress_tracker": progress_tracker,
    }


def render_markdown(pack: dict) -> str:
    tracker = pack["progress_tracker"]
    lines = [
        "# Reviewer Workflow Pack",
        "",
        f"- Generated at: `{pack['generated_at']}`",
        f"- Total sessions: `{tracker['total_sessions']}`",
        f"- Fully human-complete sessions: `{tracker['fully_human_complete_sessions']}`",
        f"- Human completion rate: `{tracker['human_completion_rate']}`",
        "",
        "## Queue Sizes",
        "",
        f"- Annotator A queue: `{len(pack['queues']['annotator_a'])}`",
        f"- Annotator B queue: `{len(pack['queues']['annotator_b'])}`",
        f"- Adjudicator queue: `{len(pack['queues']['adjudicator'])}`",
        "",
        "## Estimated Days Remaining",
        "",
        f"- Annotator A: `{tracker['estimated_days_remaining']['annotator_a']}`",
        f"- Annotator B: `{tracker['estimated_days_remaining']['annotator_b']}`",
        f"- Adjudicator: `{tracker['estimated_days_remaining']['adjudicator']}`",
        f"- Overall pipeline: `{tracker['estimated_days_remaining']['overall_pipeline_days']}`",
        "",
    ]

    for stage in ("annotator_a", "annotator_b", "adjudicator"):
        lines.extend([f"## {stage.replace('_', ' ').title()} Daily Batches", ""])
        batches = pack["daily_batches"][stage]
        if not batches:
            lines.append("- None")
        else:
            for batch in batches:
                lines.append(
                    f"- {batch['date']}: load `{batch['load']}` / capacity `{batch['capacity']}` -> {', '.join(batch['session_ids'])}"
                )
        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate A/B/adjudicator queues with daily batches and progress tracking.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Gold-data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--annotator-a-capacity", type=int, default=8, help="Daily capacity for annotator A.")
    parser.add_argument("--annotator-b-capacity", type=int, default=8, help="Daily capacity for annotator B.")
    parser.add_argument("--adjudicator-capacity", type=int, default=6, help="Daily capacity for adjudicator.")
    parser.add_argument(
        "--start-date",
        default="",
        help="Optional YYYY-MM-DD start date for daily batch planning. Defaults to local today.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = load_registry(gold_root / "session_registry.csv")

    if args.start_date:
        start_date_value = date.fromisoformat(args.start_date)
    else:
        start_date_value = date.today()

    pack = build_reviewer_workflow_pack(
        rows,
        annotator_a_capacity=args.annotator_a_capacity,
        annotator_b_capacity=args.annotator_b_capacity,
        adjudicator_capacity=args.adjudicator_capacity,
        start_date_value=start_date_value,
    )

    (report_dir / "reviewer_workflow_pack.json").write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "reviewer_workflow_pack.md").write_text(render_markdown(pack), encoding="utf-8")

    _write_queue_csv(pack["queues"]["annotator_a"], report_dir / "reviewer_queue_annotator_a.csv")
    _write_queue_csv(pack["queues"]["annotator_b"], report_dir / "reviewer_queue_annotator_b.csv")
    _write_queue_csv(pack["queues"]["adjudicator"], report_dir / "reviewer_queue_adjudicator.csv")

    print(json.dumps(pack, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
