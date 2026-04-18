#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_gold_dataset import load_registry

DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"


def build_dashboard(rows: list[dict[str, str]]) -> dict:
    by_language = Counter(row["language"] for row in rows)
    by_cohort = Counter(row["cohort"] for row in rows)
    by_collection_status = Counter(row["collection_status"] for row in rows)
    by_qa_status = Counter(row["qa_status"] for row in rows)
    by_domain = Counter(row["target_primary_domain"] for row in rows)

    ready_for_collection = [row["session_id"] for row in rows if row["qa_status"] == "ready_for_collection"]
    ready_for_annotation = [row["session_id"] for row in rows if row["qa_status"] == "ready_for_annotation"]
    ready_for_adjudication = [row["session_id"] for row in rows if row["qa_status"] == "ready_for_adjudication"]
    completed = [row["session_id"] for row in rows if row["qa_status"] == "complete"]

    pilot_priority = [row for row in rows if row["cohort"] == "pilot"][:10]

    return {
        "total_sessions": len(rows),
        "by_language": dict(by_language),
        "by_cohort": dict(by_cohort),
        "by_collection_status": dict(by_collection_status),
        "by_qa_status": dict(by_qa_status),
        "by_domain": dict(by_domain),
        "ready_for_collection": ready_for_collection,
        "ready_for_annotation": ready_for_annotation,
        "ready_for_adjudication": ready_for_adjudication,
        "completed": completed,
        "pilot_priority": [
            {
                "session_id": row["session_id"],
                "language": row["language"],
                "target_primary_domain": row["target_primary_domain"],
                "collection_status": row["collection_status"],
                "qa_status": row["qa_status"],
            }
            for row in pilot_priority
        ],
    }


def render_markdown(dashboard: dict) -> str:
    lines = [
        "# Gold Progress Dashboard",
        "",
        f"- Total sessions: `{dashboard['total_sessions']}`",
        "",
        "## Collection Status",
        "",
    ]
    for key, value in sorted(dashboard["by_collection_status"].items()):
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## QA Status", ""])
    for key, value in sorted(dashboard["by_qa_status"].items()):
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Pilot Priority", ""])
    for row in dashboard["pilot_priority"]:
        lines.append(
            f"- {row['session_id']} ({row['language']}, {row['target_primary_domain']}): "
            f"collection=`{row['collection_status']}`, qa=`{row['qa_status']}`"
        )
    lines.extend(["", "## Ready Queues", ""])
    lines.append(f"- ready_for_collection: `{len(dashboard['ready_for_collection'])}`")
    lines.append(f"- ready_for_annotation: `{len(dashboard['ready_for_annotation'])}`")
    lines.append(f"- ready_for_adjudication: `{len(dashboard['ready_for_adjudication'])}`")
    lines.append(f"- complete: `{len(dashboard['completed'])}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a progress dashboard for the gold-data pipeline.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Gold-data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Directory for generated reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root)
    report_dir = Path(args.report_dir)
    rows = load_registry(gold_root / "session_registry.csv")
    dashboard = build_dashboard(rows)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "gold_progress_dashboard.json").write_text(
        json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "gold_progress_dashboard.md").write_text(
        render_markdown(dashboard),
        encoding="utf-8",
    )
    print(json.dumps(dashboard, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
