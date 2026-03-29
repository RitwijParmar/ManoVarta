from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


PHQ8_TO_MANOVARTA = (
    "phq_q1_anhedonia",
    "phq_q2_low_mood",
    "phq_q3_sleep",
    "phq_q4_fatigue",
    "phq_q5_appetite",
    "phq_q6_worthlessness",
    "phq_q7_concentration",
    "phq_q8_psychomotor",
)

TRANSCRIPT_SUFFIX = "_TRANSCRIPT.csv"
ELLIE_ID_RE = re.compile(r"^[A-Za-z_]+[0-9_]+\s+\((.*)\)$")
ANGLE_NOTE_RE = re.compile(r"\s*<[^>]+>")


def load_daic_conversations(root: Path) -> dict[str, list[dict[str, Any]]]:
    root = resolve_daic_root(root)
    split_metadata = load_daic_split_metadata(root)
    grouped: dict[str, list[dict[str, Any]]] = {"train": [], "dev": [], "test": []}

    for split_name, records in split_metadata.items():
        for session_id, metadata in records.items():
            session_dir = root / f"{session_id}_P"
            transcript_path = session_dir / f"{session_id}{TRANSCRIPT_SUFFIX}"
            if not transcript_path.exists():
                continue
            turns = load_daic_transcript(transcript_path)
            if not turns:
                continue
            grouped[split_name].append(_build_daic_conversation(session_id, split_name, metadata, turns))

    return grouped


def load_daic_split_metadata(root: Path) -> dict[str, dict[str, dict[str, Any]]]:
    root = resolve_daic_root(root)
    return {
        split_name: _load_split_table(_resolve_split_csv(root, split_name), split_name)
        for split_name in ("train", "dev", "test")
    }


def resolve_daic_root(root: Path) -> Path:
    root = Path(root)
    if _has_daic_split_csvs(root):
        return root

    for candidate in _candidate_daic_roots(root):
        if _has_daic_split_csvs(candidate):
            return candidate

    raise FileNotFoundError(
        f"Could not find DAIC-WOZ split CSVs under {root}. "
        "Expected train/dev/test split CSV files somewhere inside the provided root."
    )


def load_daic_transcript(path: Path) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for row in reader:
            if not row:
                continue
            if _looks_like_header(row):
                continue
            if len(row) < 4:
                continue
            speaker = row[2].strip()
            text = _normalize_daic_text("\t".join(row[3:]).strip(), speaker=speaker)
            if not text:
                continue
            turns.append(
                {
                    "turn_id": len(turns) + 1,
                    "speaker": _map_speaker(speaker),
                    "text": text,
                    "language_tag": "en",
                }
            )
    return turns


def _build_daic_conversation(
    session_id: str,
    split_name: str,
    metadata: dict[str, Any],
    turns: list[dict[str, Any]],
) -> dict[str, Any]:
    phq_labels = {
        item_id: value
        for item_id, value in zip(PHQ8_TO_MANOVARTA, metadata.get("phq8_item_values", []))
        if value is not None
    }
    return {
        "conversation_id": f"DAIC-{session_id}",
        "patient_id": f"DAIC-P{session_id}",
        "language": "en",
        "external_split": split_name,
        "conversation_turns": turns,
        "evidence_spans": [],
        "phq9_item_labels": phq_labels,
        "gad7_item_labels": {},
        "safety_flag": {"level": "none", "cues": []},
        "annotator_notes": (
            "DAIC-WOZ auxiliary supervision. PHQ-8 item labels only; "
            "no PHQ-9 item 9 or GAD-7 supervision."
        ),
        "generation_source": "daic_woz_auxiliary",
        "review_status": "external_auxiliary",
        "source_metadata": {
            "session_id": session_id,
            "split": split_name,
            "gender": metadata.get("gender"),
            "phq8_binary": metadata.get("phq8_binary"),
            "phq8_score": metadata.get("phq8_score"),
        },
    }


def _resolve_split_csv(root: Path, split_name: str) -> Path:
    candidates = (
        root / f"{split_name}_split_Depression_AVEC2017.csv",
        root / f"{split_name}_split.csv",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find DAIC-WOZ split CSV for {split_name} under {root}")


def _candidate_daic_roots(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for pattern in ("train_split_Depression_AVEC2017.csv", "train_split.csv"):
        for match in sorted(root.rglob(pattern)):
            parent = match.parent
            if parent not in candidates:
                candidates.append(parent)
    return candidates


def _has_daic_split_csvs(root: Path) -> bool:
    return all(
        any(
            (root / filename).exists()
            for filename in (f"{split_name}_split_Depression_AVEC2017.csv", f"{split_name}_split.csv")
        )
        for split_name in ("train", "dev", "test")
    )


def _load_split_table(path: Path, split_name: str) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing header row in {path}")

        has_full_label_layout = len(reader.fieldnames) >= 12
        session_field = _pick_field(
            reader.fieldnames,
            preferred=("participant_id", "participantid", "session_id", "sessionid"),
            fallback_index=0,
        )
        gender_field = _pick_field(
            reader.fieldnames,
            preferred=("gender",),
            fallback_index=3,
            optional=True,
            allow_positional=has_full_label_layout,
        )
        binary_field = _pick_field(
            reader.fieldnames,
            preferred=("phq8_binary", "phq8binary", "binary"),
            fallback_index=1,
            optional=True,
            allow_positional=has_full_label_layout,
        )
        score_field = _pick_field(
            reader.fieldnames,
            preferred=("phq8_score", "phq8score", "score"),
            fallback_index=2,
            optional=True,
            allow_positional=has_full_label_layout,
        )
        item_fields = _pick_phq_item_fields(reader.fieldnames, session_field, gender_field, binary_field, score_field)

        records: dict[str, dict[str, Any]] = {}
        for row in reader:
            session_id = str(row.get(session_field, "")).strip()
            if not session_id:
                continue
            records[session_id] = {
                "split": split_name,
                "gender": row.get(gender_field, "").strip() if gender_field else None,
                "phq8_binary": _coerce_int(row.get(binary_field)) if binary_field else None,
                "phq8_score": _coerce_int(row.get(score_field)) if score_field else None,
                "phq8_item_values": [_coerce_int(row.get(field)) for field in item_fields],
            }
        return records


def _pick_field(
    fieldnames: list[str],
    preferred: tuple[str, ...],
    fallback_index: int,
    optional: bool = False,
    allow_positional: bool = True,
) -> str | None:
    normalized = {_normalize_header(name): name for name in fieldnames}
    for key in preferred:
        if key in normalized:
            return normalized[key]
    if optional and fallback_index >= len(fieldnames):
        return None
    if allow_positional and fallback_index < len(fieldnames):
        return fieldnames[fallback_index]
    if optional:
        return None
    raise ValueError(f"Unable to resolve required field from header: {fieldnames}")


def _pick_phq_item_fields(
    fieldnames: list[str],
    session_field: str,
    gender_field: str | None,
    binary_field: str | None,
    score_field: str | None,
) -> list[str]:
    normalized = {_normalize_header(name): name for name in fieldnames}
    direct_matches: list[str] = []
    for idx in range(1, 9):
        for key in (f"q{idx}", f"phq8q{idx}", f"phq{idx}", f"phq8item{idx}", f"question{idx}"):
            if key in normalized:
                direct_matches.append(normalized[key])
                break
    if len(direct_matches) == 8:
        return direct_matches

    excluded = {session_field}
    if gender_field:
        excluded.add(gender_field)
    if binary_field:
        excluded.add(binary_field)
    if score_field:
        excluded.add(score_field)
    remaining = [field for field in fieldnames if field not in excluded]
    return remaining[:8] if len(remaining) >= 8 else []


def _map_speaker(speaker: str) -> str:
    return "assistant" if speaker.strip().lower() == "ellie" else "user"


def _normalize_daic_text(text: str, speaker: str) -> str:
    cleaned = text.strip().strip('"').replace("\ufeff", "")
    if not cleaned or cleaned.lower() == "scrubbed_entry":
        return ""
    if speaker.strip().lower() == "ellie":
        match = ELLIE_ID_RE.match(cleaned)
        if match:
            cleaned = match.group(1).strip()
    cleaned = ANGLE_NOTE_RE.sub("", cleaned)
    return " ".join(cleaned.split())


def _looks_like_header(row: list[str]) -> bool:
    first = row[0].strip().lower()
    third = row[2].strip().lower() if len(row) > 2 else ""
    return first in {"start_time", "start", "begin"} or third == "speaker"


def _normalize_header(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum() or ch == "_")


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None
