#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_gold_dataset import annotation_is_human, load_registry, resolve_project_path

DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"
VALUE_BUCKETS = ("0", "1", "2", "3")


def _load_label(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _item_index(payload: dict | None) -> dict[str, dict]:
    if not payload:
        return {}
    items = payload.get("items", [])
    return {item.get("item_id"): item for item in items if isinstance(item, dict) and item.get("item_id")}


def _safe_score(value: object) -> int | None:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0 or numeric > 3:
        return None
    return numeric


def _metric_row_from_pairs(pairs: list[tuple[int, int]]) -> tuple[dict[str, dict[str, int]], dict[str, float | int | None]]:
    matrix = {left: {right: 0 for right in VALUE_BUCKETS} for left in VALUE_BUCKETS}
    for left, right in pairs:
        matrix[str(left)][str(right)] += 1
    n_pairs = sum(sum(row.values()) for row in matrix.values())
    if n_pairs == 0:
        return matrix, {"n_pairs": 0, "exact_agreement_rate": None, "cohen_kappa": None}

    diag = sum(matrix[key][key] for key in VALUE_BUCKETS)
    exact_agreement_rate = diag / n_pairs
    row_marginals = {key: sum(matrix[key].values()) for key in VALUE_BUCKETS}
    col_marginals = {key: sum(matrix[left][key] for left in VALUE_BUCKETS) for key in VALUE_BUCKETS}
    pe = sum((row_marginals[key] * col_marginals[key]) for key in VALUE_BUCKETS) / (n_pairs * n_pairs)
    if abs(1.0 - pe) < 1e-12:
        cohen_kappa = 1.0 if abs(exact_agreement_rate - 1.0) < 1e-12 else 0.0
    else:
        cohen_kappa = (exact_agreement_rate - pe) / (1.0 - pe)
    return matrix, {
        "n_pairs": n_pairs,
        "exact_agreement_rate": round(exact_agreement_rate, 4),
        "cohen_kappa": round(cohen_kappa, 4),
    }


def _collect_item_pairs(row: dict[str, str], *, human_only_metrics: bool) -> tuple[list[tuple[str, int, int]], list[str]]:
    issues: list[str] = []
    annotator_a = _load_label(resolve_project_path(row["annotator_a_file"]))
    annotator_b = _load_label(resolve_project_path(row["annotator_b_file"]))
    if annotator_a is None or annotator_b is None:
        issues.append("missing dual annotation files")
        return [], issues
    if human_only_metrics and (not annotation_is_human(annotator_a) or not annotation_is_human(annotator_b)):
        issues.append("non-human dual annotations skipped for metrics")
        return [], issues
    a_items = _item_index(annotator_a)
    b_items = _item_index(annotator_b)
    pairs: list[tuple[str, int, int]] = []
    for item_id in sorted(set(a_items) | set(b_items)):
        a_val = _safe_score(a_items.get(item_id, {}).get("value"))
        b_val = _safe_score(b_items.get(item_id, {}).get("value"))
        if a_val is None or b_val is None:
            continue
        pairs.append((item_id, a_val, b_val))
    return pairs, issues


def _compare_session(row: dict[str, str]) -> tuple[list[dict[str, str]], list[str]]:
    issues: list[str] = []
    disagreements: list[dict[str, str]] = []
    annotator_a = _load_label(resolve_project_path(row["annotator_a_file"]))
    annotator_b = _load_label(resolve_project_path(row["annotator_b_file"]))
    adjudicated = _load_label(resolve_project_path(row["adjudicated_label_file"]))

    if annotator_a is None or annotator_b is None:
        issues.append("missing dual annotation files")
        return disagreements, issues
    if annotator_a.get("is_placeholder") or annotator_b.get("is_placeholder"):
        issues.append("placeholder dual annotations")
    if adjudicated is None:
        issues.append("missing adjudicated file")
    elif adjudicated.get("is_placeholder"):
        issues.append("placeholder adjudicated file")

    a_items = _item_index(annotator_a)
    b_items = _item_index(annotator_b)
    item_ids = sorted(set(a_items) | set(b_items))
    for item_id in item_ids:
        a_item = a_items.get(item_id, {})
        b_item = b_items.get(item_id, {})
        value_diff = a_item.get("value") != b_item.get("value")
        confidence_diff = a_item.get("confidence") != b_item.get("confidence")
        evidence_diff = (a_item.get("evidence_quote") or "").strip() != (b_item.get("evidence_quote") or "").strip()
        if value_diff or confidence_diff or evidence_diff:
            disagreements.append(
                {
                    "session_id": row["session_id"],
                    "item_id": item_id,
                    "annotator_a_value": str(a_item.get("value")),
                    "annotator_b_value": str(b_item.get("value")),
                    "annotator_a_confidence": str(a_item.get("confidence", "")),
                    "annotator_b_confidence": str(b_item.get("confidence", "")),
                    "annotator_a_evidence": str(a_item.get("evidence_quote", "")),
                    "annotator_b_evidence": str(b_item.get("evidence_quote", "")),
                }
            )

    a_safety = (annotator_a.get("safety") or {}).get("level")
    b_safety = (annotator_b.get("safety") or {}).get("level")
    if a_safety != b_safety:
        disagreements.append(
            {
                "session_id": row["session_id"],
                "item_id": "safety",
                "annotator_a_value": str(a_safety),
                "annotator_b_value": str(b_safety),
                "annotator_a_confidence": "",
                "annotator_b_confidence": "",
                "annotator_a_evidence": str((annotator_a.get("safety") or {}).get("evidence_quote", "")),
                "annotator_b_evidence": str((annotator_b.get("safety") or {}).get("evidence_quote", "")),
            }
        )

    return disagreements, issues


def build_adjudication_summary(rows: list[dict[str, str]], *, human_only_metrics: bool = False) -> dict:
    summary = {
        "total_sessions": len(rows),
        "sessions_with_dual_annotations": 0,
        "sessions_with_open_disagreements": 0,
        "sessions_blocked_by_placeholders": 0,
        "disagreement_rows": [],
        "session_issues": [],
        "metrics_scope": "human_only_dual_annotations" if human_only_metrics else "all_dual_annotations",
        "sessions_used_for_metrics": 0,
        "sessions_skipped_for_metrics_nonhuman": 0,
        "item_agreement_metrics": {},
        "overall_agreement": {"n_pairs": 0, "exact_agreement_rate": None, "cohen_kappa": None},
        "conflict_heatmap": {
            "axes": {
                "rows": "item_id",
                "columns": ["abs_diff_0", "abs_diff_1", "abs_diff_2", "abs_diff_3"],
            },
            "values": {},
        },
    }
    item_pairs: dict[str, list[tuple[int, int]]] = defaultdict(list)
    heatmap: dict[str, dict[str, int]] = defaultdict(
        lambda: {"abs_diff_0": 0, "abs_diff_1": 0, "abs_diff_2": 0, "abs_diff_3": 0}
    )

    for row in rows:
        disagreements, issues = _compare_session(row)
        if "missing dual annotation files" not in issues:
            summary["sessions_with_dual_annotations"] += 1
        if issues:
            summary["session_issues"].append({"session_id": row["session_id"], "issues": issues})
        if any("placeholder" in issue for issue in issues):
            summary["sessions_blocked_by_placeholders"] += 1
        if disagreements:
            summary["sessions_with_open_disagreements"] += 1
            summary["disagreement_rows"].extend(disagreements)
        pairs, metric_issues = _collect_item_pairs(row, human_only_metrics=human_only_metrics)
        if any("non-human dual annotations skipped for metrics" == issue for issue in metric_issues):
            summary["sessions_skipped_for_metrics_nonhuman"] += 1
        if pairs:
            summary["sessions_used_for_metrics"] += 1
        for item_id, a_val, b_val in pairs:
            item_pairs[item_id].append((a_val, b_val))
            abs_diff = abs(a_val - b_val)
            bucket = f"abs_diff_{abs_diff}"
            heatmap[item_id][bucket] += 1

    overall_pairs: list[tuple[int, int]] = []
    for item_id in sorted(item_pairs):
        matrix, metrics = _metric_row_from_pairs(item_pairs[item_id])
        summary["item_agreement_metrics"][item_id] = {
            **metrics,
            "confusion_matrix": matrix,
        }
        summary["conflict_heatmap"]["values"][item_id] = heatmap[item_id]
        overall_pairs.extend(item_pairs[item_id])

    _, overall_metrics = _metric_row_from_pairs(overall_pairs)
    summary["overall_agreement"] = overall_metrics

    return summary


def write_disagreement_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "session_id",
        "item_id",
        "annotator_a_value",
        "annotator_b_value",
        "annotator_a_confidence",
        "annotator_b_confidence",
        "annotator_a_evidence",
        "annotator_b_evidence",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_kappa_csv(item_metrics: dict[str, dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["item_id", "n_pairs", "exact_agreement_rate", "cohen_kappa"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item_id in sorted(item_metrics):
            row = dict(item_metrics[item_id])
            row["item_id"] = item_id
            row.pop("confusion_matrix", None)
            writer.writerow(row)


def write_conflict_heatmap_csv(heatmap: dict[str, dict[str, int]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["item_id", "abs_diff_0", "abs_diff_1", "abs_diff_2", "abs_diff_3"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item_id in sorted(heatmap):
            writer.writerow({"item_id": item_id, **heatmap[item_id]})


def render_markdown(summary: dict) -> str:
    lines = [
        "# Gold Adjudication Status",
        "",
        f"- Total sessions: `{summary['total_sessions']}`",
        f"- Sessions with dual annotations present: `{summary['sessions_with_dual_annotations']}`",
        f"- Sessions with open disagreements: `{summary['sessions_with_open_disagreements']}`",
        f"- Sessions blocked by placeholders: `{summary['sessions_blocked_by_placeholders']}`",
        "",
        "## Agreement Metrics",
        "",
        f"- Metrics scope: `{summary['metrics_scope']}`",
        f"- Sessions used for metrics: `{summary['sessions_used_for_metrics']}`",
        f"- Sessions skipped for non-human labels: `{summary['sessions_skipped_for_metrics_nonhuman']}`",
        f"- Overall pair count: `{summary['overall_agreement']['n_pairs']}`",
        f"- Overall exact agreement: `{summary['overall_agreement']['exact_agreement_rate']}`",
        f"- Overall Cohen's kappa: `{summary['overall_agreement']['cohen_kappa']}`",
        "",
        "### Item-wise Kappa",
        "",
    ]
    if not summary["item_agreement_metrics"]:
        lines.append("- None")
    else:
        lines.append("| Item | Pairs | Exact agreement | Cohen's kappa |")
        lines.append("| --- | ---: | ---: | ---: |")
        for item_id in sorted(summary["item_agreement_metrics"]):
            metrics = summary["item_agreement_metrics"][item_id]
            lines.append(
                f"| {item_id} | {metrics['n_pairs']} | {metrics['exact_agreement_rate']} | {metrics['cohen_kappa']} |"
            )
    lines.extend(
        [
            "",
            "### Conflict Heatmap (Absolute Score Difference)",
            "",
        ]
    )
    heatmap_values = summary["conflict_heatmap"]["values"]
    if not heatmap_values:
        lines.append("- None")
    else:
        lines.append("| Item | diff=0 | diff=1 | diff=2 | diff=3 |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for item_id in sorted(heatmap_values):
            row = heatmap_values[item_id]
            lines.append(
                f"| {item_id} | {row['abs_diff_0']} | {row['abs_diff_1']} | {row['abs_diff_2']} | {row['abs_diff_3']} |"
            )
    lines.extend([
        "",
        "## Session Issues",
        "",
    ])
    if not summary["session_issues"]:
        lines.append("- None")
    else:
        for issue in summary["session_issues"][:20]:
            lines.append(f"- {issue['session_id']}: {', '.join(issue['issues'])}")
        if len(summary["session_issues"]) > 20:
            lines.append(f"- ...and `{len(summary['session_issues']) - 20}` more sessions with issues")
    lines.extend(["", "## Sample Disagreements", ""])
    if not summary["disagreement_rows"]:
        lines.append("- None")
    else:
        for row in summary["disagreement_rows"][:20]:
            lines.append(
                f"- {row['session_id']} {row['item_id']}: "
                f"A=`{row['annotator_a_value']}` vs B=`{row['annotator_b_value']}`"
            )
        if len(summary["disagreement_rows"]) > 20:
            lines.append(f"- ...and `{len(summary['disagreement_rows']) - 20}` more disagreement rows")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a disagreement/adjudication report for the gold dataset.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Gold-data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Directory for generated reports.")
    parser.add_argument(
        "--human-only-metrics",
        action="store_true",
        help="Compute kappa/heatmap only from sessions where annotator A and B labels are human-authored.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root)
    report_dir = Path(args.report_dir)
    rows = load_registry(gold_root / "session_registry.csv")
    summary = build_adjudication_summary(rows, human_only_metrics=args.human_only_metrics)

    adjudication_dir = gold_root / "adjudication"
    report_dir.mkdir(parents=True, exist_ok=True)
    write_disagreement_csv(summary["disagreement_rows"], adjudication_dir / "disagreements.csv")
    write_kappa_csv(summary["item_agreement_metrics"], adjudication_dir / "item_kappa.csv")
    write_conflict_heatmap_csv(summary["conflict_heatmap"]["values"], adjudication_dir / "conflict_heatmap.csv")
    (report_dir / "gold_adjudication_status.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "gold_adjudication_status.md").write_text(
        render_markdown(summary),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
