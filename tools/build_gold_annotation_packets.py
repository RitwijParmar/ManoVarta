#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_gold_dataset import load_metadata, load_registry, resolve_project_path

DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"
DEFAULT_OUTPUT_DIR = DEFAULT_GOLD_ROOT / "packets"

STAGE_TO_OUTPUT_FIELD = {
    "annotator_a": "annotator_a_file",
    "annotator_b": "annotator_b_file",
    "adjudication": "adjudicated_label_file",
}


def transcript_turns_for_markdown(transcript_payload: dict) -> list[str]:
    turns = transcript_payload.get("turns", [])
    if not turns:
        return ["- No turns recorded yet."]
    rendered: list[str] = []
    for turn in turns:
        speaker = turn.get("speaker", "unknown")
        turn_id = turn.get("turn_id", "?")
        text = turn.get("text", "").strip() or "(empty)"
        rendered.append(f"- `{turn_id}` {speaker}: {text}")
    return rendered


def build_stage_packet(
    row: dict[str, str],
    *,
    stage: str,
    metadata_row: dict[str, str] | None,
    transcript_payload: dict | None,
) -> dict:
    return {
        "session_id": row["session_id"],
        "language": row["language"],
        "cohort": row["cohort"],
        "target_primary_domain": row["target_primary_domain"],
        "target_risk_band": row["target_risk_band"],
        "packet_stage": stage,
        "target_output_file": row[STAGE_TO_OUTPUT_FIELD[stage]],
        "related_files": {
            "audio_file": row["audio_file"],
            "transcript_file": row["transcript_file"],
            "annotator_a_file": row["annotator_a_file"],
            "annotator_b_file": row["annotator_b_file"],
            "adjudicated_label_file": row["adjudicated_label_file"],
        },
        "metadata": metadata_row or {},
        "transcript": transcript_payload or {"session_id": row["session_id"], "turns": []},
        "instructions": {
            "annotator_a": "Label independently using the transcript, metadata, and annotation guidelines. Do not inspect annotator B.",
            "annotator_b": "Label independently using the transcript, metadata, and annotation guidelines. Do not inspect annotator A.",
            "adjudication": "Resolve disagreements between annotator A and annotator B, justify the decision, and save one final adjudicated label file.",
        }[stage],
    }


def render_packet_markdown(packet: dict) -> str:
    metadata = packet.get("metadata", {})
    transcript = packet.get("transcript", {})
    lines = [
        f"# {packet['session_id']} {packet['packet_stage']} packet",
        "",
        f"- Language: `{packet['language']}`",
        f"- Cohort: `{packet['cohort']}`",
        f"- Target primary domain: `{packet['target_primary_domain']}`",
        f"- Target risk band: `{packet['target_risk_band']}`",
        f"- Target output file: `{packet['target_output_file']}`",
        "",
        "## Metadata",
        "",
        f"- Participant ID: `{metadata.get('participant_id', '')}`",
        f"- Age years: `{metadata.get('age_years', '')}`",
        f"- Age band: `{metadata.get('age_band', '')}`",
        f"- Occupation: `{metadata.get('occupation', '')}`",
        f"- Living situation: `{metadata.get('living_situation', '')}`",
        f"- Support system: `{metadata.get('support_system', '')}`",
        f"- Consent recorded: `{metadata.get('consent_recorded', '')}`",
        f"- Collection source: `{metadata.get('collection_source', '')}`",
        "",
        "## Instructions",
        "",
        packet["instructions"],
        "",
        "## Transcript",
        "",
    ]
    lines.extend(transcript_turns_for_markdown(transcript))
    lines.append("")
    return "\n".join(lines)


def build_packets(
    rows: list[dict[str, str]],
    *,
    gold_root: Path,
    output_dir: Path,
    stages: tuple[str, ...],
) -> dict[str, int]:
    metadata_index = load_metadata(gold_root / "metadata.csv")
    created = {stage: 0 for stage in stages}

    for row in rows:
        transcript_path = resolve_project_path(row["transcript_file"])
        transcript_payload = None
        if transcript_path.exists():
            transcript_payload = json.loads(transcript_path.read_text(encoding="utf-8"))
        metadata_row = metadata_index.get(row["session_id"])

        for stage in stages:
            packet = build_stage_packet(
                row,
                stage=stage,
                metadata_row=metadata_row,
                transcript_payload=transcript_payload,
            )
            stage_dir = output_dir / stage
            stage_dir.mkdir(parents=True, exist_ok=True)
            json_path = stage_dir / f"{row['session_id']}.{stage}.json"
            md_path = stage_dir / f"{row['session_id']}.{stage}.md"
            json_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            md_path.write_text(render_packet_markdown(packet), encoding="utf-8")
            created[stage] += 1

    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-session gold annotation and adjudication packets.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Gold-data root directory.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Packet output directory.")
    parser.add_argument(
        "--stage",
        default="all",
        choices=("annotator_a", "annotator_b", "adjudication", "all"),
        help="Which packet stage to export.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root)
    output_dir = Path(args.output_dir)
    registry_path = gold_root / "session_registry.csv"
    rows = load_registry(registry_path)
    stages = ("annotator_a", "annotator_b", "adjudication") if args.stage == "all" else (args.stage,)
    created = build_packets(rows, gold_root=gold_root, output_dir=output_dir, stages=stages)
    print(json.dumps(created, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
