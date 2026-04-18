#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import tarfile
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE = PROJECT_ROOT / "data" / "external" / "IndicVoices" / "v1_Hindi_valid.tgz"
DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import real Hindi samples from IndicVoices v1 valid archive into MVGOLD-HI session slots."
    )
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="Path to v1_Hindi_valid.tgz archive.")
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT), help="Path to data/gold root.")
    parser.add_argument("--max-sessions", type=int, default=30, help="Number of MVGOLD-HI sessions to fill.")
    parser.add_argument("--start-index", type=int, default=1, help="Starting MVGOLD-HI index (1-based).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing transcript/audio/metadata slots.")
    return parser.parse_args()


def read_registry(gold_root: Path) -> list[dict[str, str]]:
    registry_path = gold_root / "session_registry.csv"
    with registry_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_metadata(gold_root: Path) -> tuple[list[dict[str, str]], list[str]]:
    metadata_path = gold_root / "metadata.csv"
    with metadata_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_metadata(gold_root: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    metadata_path = gold_root / "metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def session_ids_to_fill(start_index: int, max_sessions: int) -> list[str]:
    end_index = start_index + max_sessions
    return [f"MVGOLD-HI-{idx:03d}" for idx in range(start_index, end_index)]


def paired_members(archive: tarfile.TarFile) -> list[tuple[tarfile.TarInfo, tarfile.TarInfo]]:
    members = {m.name: m for m in archive.getmembers() if m.isfile()}
    json_names = sorted(name for name in members if name.endswith(".json"))
    pairs: list[tuple[tarfile.TarInfo, tarfile.TarInfo]] = []
    for json_name in json_names:
        wav_name = json_name[:-5] + ".wav"
        json_member = members.get(json_name)
        wav_member = members.get(wav_name)
        if not json_member or not wav_member:
            continue
        pairs.append((json_member, wav_member))
    return pairs


def transcript_payload(
    *,
    session_id: str,
    cohort: str,
    metadata_obj: dict,
    source_json_path: str,
    source_wav_path: str,
) -> dict:
    verbatim = normalize_text_field(metadata_obj.get("verbatim"))
    normalized = normalize_text_field(metadata_obj.get("normalized"))
    prompt = normalize_text_field(metadata_obj.get("prompt"))
    text = verbatim or normalized or prompt
    scenario = str(metadata_obj.get("scenario") or "").strip()

    turns = []
    if text:
        turns.append(
            {
                "turn_id": "u1",
                "speaker": "user",
                "text": text,
                "source_type": "read_or_prompted_utterance",
            }
        )

    return {
        "session_id": session_id,
        "language": "hi",
        "cohort": cohort,
        "is_placeholder": False,
        "collection_status": "collected_public_dataset",
        "notes": "Imported from IndicVoices Hindi valid split.",
        "profile": {
            "age_years": None,
            "age_band": metadata_obj.get("age_group", ""),
            "occupation": metadata_obj.get("occupation", "") or metadata_obj.get("job_type", ""),
            "living_situation": metadata_obj.get("area", ""),
            "support_system": "not_provided_in_source",
            "state": metadata_obj.get("state", ""),
            "district": metadata_obj.get("district", ""),
            "gender": metadata_obj.get("gender", ""),
        },
        "source": {
            "dataset": "indicvoices",
            "split": "Hindi/v1/valid",
            "source_json_path": source_json_path,
            "source_wav_path": source_wav_path,
            "speaker_id": metadata_obj.get("speaker_id", ""),
            "scenario": scenario,
            "task_name": metadata_obj.get("task_name", ""),
        },
        "turns": turns,
    }


def normalize_text_field(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("text", "")).strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    parts.append(cleaned)
                continue
            if isinstance(item, dict):
                cleaned = str(item.get("text", "")).strip()
                if cleaned:
                    parts.append(cleaned)
        return " ".join(parts).strip()
    return str(value).strip()


def update_metadata_row(row: dict[str, str], *, metadata_obj: dict) -> dict[str, str]:
    updated = dict(row)
    updated["participant_id"] = str(metadata_obj.get("speaker_id") or updated.get("participant_id") or "")
    updated["age_years"] = ""
    updated["age_band"] = str(metadata_obj.get("age_group") or "")
    updated["occupation"] = str(metadata_obj.get("occupation") or metadata_obj.get("job_type") or "unknown")
    updated["living_situation"] = str(metadata_obj.get("area") or "not_provided_in_source")
    updated["support_system"] = "not_provided_in_source"
    updated["consent_recorded"] = "public_dataset_license"
    updated["collection_source"] = "indicvoices_hindi_v1_valid_public"
    updated["notes"] = (
        "Imported from IndicVoices Hindi valid split. "
        "PHQ/GAD labels still require dual annotation + adjudication."
    )
    return updated


def main() -> int:
    args = parse_args()
    archive_path = Path(args.archive).expanduser().resolve()
    gold_root = Path(args.gold_root).expanduser().resolve()

    if not archive_path.exists():
        raise SystemExit(f"missing archive: {archive_path}")

    registry_rows = read_registry(gold_root)
    registry_by_session = {row["session_id"]: row for row in registry_rows}
    metadata_rows, metadata_fieldnames = read_metadata(gold_root)
    metadata_by_session = {row["session_id"]: row for row in metadata_rows}

    target_sessions = session_ids_to_fill(args.start_index, args.max_sessions)

    with tarfile.open(archive_path, "r:gz") as archive:
        pairs = paired_members(archive)
        if len(pairs) < len(target_sessions):
            raise SystemExit(
                f"archive has only {len(pairs)} paired samples, but {len(target_sessions)} session slots were requested"
            )

        audio_dir = gold_root / "audio" / "hi"
        transcript_dir = gold_root / "transcripts" / "hi"
        audio_dir.mkdir(parents=True, exist_ok=True)
        transcript_dir.mkdir(parents=True, exist_ok=True)

        imported = 0
        for session_id, (json_member, wav_member) in zip(target_sessions, pairs):
            registry_row = registry_by_session.get(session_id)
            metadata_row = metadata_by_session.get(session_id)
            if not registry_row or not metadata_row:
                print(f"[warn] missing registry/metadata row for {session_id}; skipping")
                continue

            transcript_path = PROJECT_ROOT / registry_row["transcript_file"]
            audio_path = PROJECT_ROOT / registry_row["audio_file"]
            if (transcript_path.exists() or audio_path.exists()) and not args.overwrite:
                print(f"[skip] {session_id} already has artifacts; use --overwrite to replace")
                continue

            metadata_obj = json.load(archive.extractfile(json_member))
            wav_bytes = archive.extractfile(wav_member).read()
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(wav_bytes)
            payload = transcript_payload(
                session_id=session_id,
                cohort=registry_row.get("cohort", "expansion"),
                metadata_obj=metadata_obj,
                source_json_path=json_member.name,
                source_wav_path=wav_member.name,
            )
            transcript_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            metadata_by_session[session_id] = update_metadata_row(metadata_row, metadata_obj=metadata_obj)
            imported += 1
            print(f"[ok] imported {session_id} from {json_member.name}")

    reordered = [metadata_by_session.get(row["session_id"], row) for row in metadata_rows]
    write_metadata(gold_root, reordered, metadata_fieldnames)
    print(f"[done] imported {imported} Hindi session(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
