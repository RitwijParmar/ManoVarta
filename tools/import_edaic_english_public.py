#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data" / "gold"
DEFAULT_ARCHIVES_DIR = PROJECT_ROOT / "data" / "external" / "E-DAIC-public" / "archives"
DEFAULT_LABELS_DIR = PROJECT_ROOT / "data" / "external" / "E-DAIC-public" / "labels"
DEFAULT_EDAIC_DATA_URL = "https://dcapswoz.ict.usc.edu/wwwedaic/data/"

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

PHQ8_TO_ITEM = {
    "PHQ_8NoInterest": "phq_q1_anhedonia",
    "PHQ_8Depressed": "phq_q2_low_mood",
    "PHQ_8Sleep": "phq_q3_sleep",
    "PHQ_8Tired": "phq_q4_fatigue",
    "PHQ_8Appetite": "phq_q5_appetite",
    "PHQ_8Failure": "phq_q6_worthlessness",
    "PHQ_8Concentrating": "phq_q7_concentration",
    "PHQ_8Moving": "phq_q8_psychomotor",
}


@dataclass(frozen=True)
class PatternSpec:
    mild: tuple[str, ...]
    strong: tuple[str, ...]


PATTERNS: dict[str, PatternSpec] = {
    "phq_q1_anhedonia": PatternSpec(
        mild=("not interested", "lost interest", "don't enjoy", "nothing feels fun"),
        strong=("can't enjoy anything", "no pleasure at all", "nothing matters anymore"),
    ),
    "phq_q2_low_mood": PatternSpec(
        mild=("sad", "low mood", "down", "depressed"),
        strong=("very depressed", "hopeless", "empty inside"),
    ),
    "phq_q3_sleep": PatternSpec(
        mild=("sleep", "insomnia", "wake up"),
        strong=("can't sleep", "waking up all night", "barely sleeping"),
    ),
    "phq_q4_fatigue": PatternSpec(
        mild=("tired", "fatigue", "low energy"),
        strong=("exhausted all day", "no energy at all"),
    ),
    "phq_q5_appetite": PatternSpec(
        mild=("appetite", "eating less", "eating more"),
        strong=("no appetite", "overeating every day"),
    ),
    "phq_q6_worthlessness": PatternSpec(
        mild=("worthless", "guilty", "a burden"),
        strong=("I am a burden", "I am a failure", "I am useless"),
    ),
    "phq_q7_concentration": PatternSpec(
        mild=("focus", "concentrate", "attention"),
        strong=("cannot focus", "can't concentrate on anything"),
    ),
    "phq_q8_psychomotor": PatternSpec(
        mild=("restless", "slowed down", "moving slowly"),
        strong=("can't sit still", "moving very slowly"),
    ),
    "phq_q9_self_harm": PatternSpec(
        mild=("wish I disappeared", "better off dead", "not worth living"),
        strong=("hurt myself", "kill myself", "end my life", "suicide"),
    ),
    "gad_q1_nervous": PatternSpec(
        mild=("anxious", "nervous", "on edge", "worry"),
        strong=("constant anxiety", "always nervous", "panic"),
    ),
    "gad_q2_control_worry": PatternSpec(
        mild=("can't stop worrying", "hard to control worry"),
        strong=("worry never stops", "cannot control my worry at all"),
    ),
    "gad_q3_excessive_worry": PatternSpec(
        mild=("overthinking", "worry about many things"),
        strong=("worry about everything", "worry all day long"),
    ),
    "gad_q4_trouble_relaxing": PatternSpec(
        mild=("can't relax", "hard to calm down"),
        strong=("unable to relax even at rest", "mind won't settle"),
    ),
    "gad_q5_restlessness": PatternSpec(
        mild=("restless", "can't sit still"),
        strong=("extremely restless", "constantly pacing"),
    ),
    "gad_q6_irritability": PatternSpec(
        mild=("irritable", "short temper"),
        strong=("snapping at everyone", "angry over small things"),
    ),
    "gad_q7_afraid": PatternSpec(
        mild=("afraid", "something bad will happen"),
        strong=("terrified", "constant fear that something awful will happen"),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import E-DAIC English participant archives into MVGOLD-EN slots with finalized metadata/transcripts/labels."
    )
    parser.add_argument("--gold-root", default=str(DEFAULT_GOLD_ROOT))
    parser.add_argument("--archives-dir", default=str(DEFAULT_ARCHIVES_DIR))
    parser.add_argument("--labels-dir", default=str(DEFAULT_LABELS_DIR))
    parser.add_argument("--source-data-url", default=DEFAULT_EDAIC_DATA_URL)
    parser.add_argument("--max-sessions", type=int, default=30)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
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
    return [f"MVGOLD-EN-{idx:03d}" for idx in range(start_index, end_index)]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def parse_score(value: str) -> int:
    cleaned = str(value or "").strip()
    if not cleaned:
        return 0
    try:
        numeric = int(float(cleaned))
    except ValueError:
        return 0
    return max(0, min(3, numeric))


def load_split_rows(labels_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    split_files = ("train_split.csv", "dev_split.csv", "test_split.csv")
    for filename in split_files:
        split_name = filename.split("_")[0]
        path = labels_dir / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                participant_id = str(row.get("Participant_ID", "")).strip()
                if not participant_id.isdigit():
                    continue
                rows.append(
                    {
                        "participant_id": str(int(participant_id)),
                        "split_name": split_name,
                        "gender": str(row.get("Gender", "")).strip().lower(),
                        "phq_binary": str(row.get("PHQ_Binary", "")).strip(),
                        "phq_score": str(row.get("PHQ_Score", "")).strip(),
                    }
                )
    return rows


def dedupe_split_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    ordered: list[dict[str, str]] = []
    for row in rows:
        participant_id = row["participant_id"]
        if participant_id in seen:
            continue
        seen.add(participant_id)
        ordered.append(row)
    return ordered


def select_participant_rows(rows: list[dict[str, str]], max_sessions: int) -> list[dict[str, str]]:
    ordered = dedupe_split_rows(rows)
    if max_sessions <= 0:
        return []
    half = max_sessions // 2
    negative = [row for row in ordered if row.get("phq_binary") == "0"]
    positive = [row for row in ordered if row.get("phq_binary") == "1"]
    selected = negative[:half] + positive[:half]
    if len(selected) < max_sessions:
        selected_ids = {row["participant_id"] for row in selected}
        remainder = [row for row in ordered if row["participant_id"] not in selected_ids]
        selected.extend(remainder[: max_sessions - len(selected)])
    return selected[:max_sessions]


def load_phq8_labels(labels_dir: Path) -> dict[str, dict[str, int]]:
    labels_path = labels_dir / "Detailed_PHQ8_Labels.csv"
    if not labels_path.exists():
        return {}
    mapping: dict[str, dict[str, int]] = {}
    with labels_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            participant_id = str(row.get("Participant_ID", "")).strip()
            if not participant_id.isdigit():
                continue
            normalized_id = str(int(participant_id))
            item_scores: dict[str, int] = {}
            for phq8_key, item_id in PHQ8_TO_ITEM.items():
                item_scores[item_id] = parse_score(row.get(phq8_key, "0"))
            mapping[normalized_id] = item_scores
    return mapping


def download_archive_if_needed(
    participant_id: str,
    *,
    archives_dir: Path,
    source_data_url: str,
    overwrite: bool,
) -> Path:
    archives_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{participant_id}_P.tar.gz"
    destination = archives_dir / filename
    if destination.exists() and not overwrite:
        try:
            with tarfile.open(destination, "r:gz") as archive:
                archive.getmembers()
            return destination
        except tarfile.TarError:
            destination.unlink(missing_ok=True)
    url = urljoin(source_data_url if source_data_url.endswith("/") else f"{source_data_url}/", filename)
    with urlopen(url) as response:
        destination.write_bytes(response.read())
    return destination


def extract_archive_payload(archive_path: Path, participant_id: str) -> tuple[bytes, list[dict[str, object]], str, str]:
    with tarfile.open(archive_path, "r:gz") as archive:
        members = {member.name: member for member in archive.getmembers() if member.isfile()}
        audio_member_name = None
        transcript_member_name = None
        expected_audio = f"{participant_id}_P/{participant_id}_AUDIO.wav"
        expected_transcript = f"{participant_id}_P/{participant_id}_Transcript.csv"
        if expected_audio in members:
            audio_member_name = expected_audio
        else:
            for name in members:
                if name.endswith("_AUDIO.wav"):
                    audio_member_name = name
                    break
        if expected_transcript in members:
            transcript_member_name = expected_transcript
        else:
            for name in members:
                if name.endswith("_Transcript.csv"):
                    transcript_member_name = name
                    break
        if not audio_member_name or not transcript_member_name:
            raise FileNotFoundError(f"archive missing required audio/transcript members: {archive_path}")

        audio_bytes = archive.extractfile(members[audio_member_name]).read()
        transcript_raw = archive.extractfile(members[transcript_member_name]).read()

    transcript_text = transcript_raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(transcript_text))
    turns: list[dict[str, object]] = []
    for idx, row in enumerate(reader, start=1):
        text = str(row.get("Text", "")).strip()
        if not text:
            continue
        turn: dict[str, object] = {
            "turn_id": f"u{idx}",
            "speaker": "user",
            "text": text,
            "source_type": "dataset_utterance",
        }
        start_time = str(row.get("Start_Time", "")).strip()
        end_time = str(row.get("End_Time", "")).strip()
        confidence = str(row.get("Confidence", "")).strip()
        if start_time:
            turn["start_time_sec"] = start_time
        if end_time:
            turn["end_time_sec"] = end_time
        if confidence:
            turn["asr_confidence"] = confidence
        turns.append(turn)

    return audio_bytes, turns, audio_member_name, transcript_member_name


def build_transcript_payload(
    *,
    session_id: str,
    cohort: str,
    participant_row: dict[str, str],
    turns: list[dict[str, object]],
    source_audio_path: str,
    source_transcript_path: str,
) -> dict:
    return {
        "session_id": session_id,
        "language": "en",
        "cohort": cohort,
        "is_placeholder": False,
        "collection_status": "collected_public_dataset",
        "notes": "Imported from E-DAIC public participant archive.",
        "profile": {
            "age_years": None,
            "age_band": "adult_unknown_from_source",
            "occupation": "unknown_from_source",
            "living_situation": "unknown_from_source",
            "support_system": "unknown_from_source",
            "gender": participant_row.get("gender", ""),
        },
        "source": {
            "dataset": "e_daic_public",
            "participant_id": participant_row["participant_id"],
            "split": participant_row.get("split_name", ""),
            "phq_binary": participant_row.get("phq_binary", ""),
            "phq_score": participant_row.get("phq_score", ""),
            "source_audio_path": source_audio_path,
            "source_transcript_path": source_transcript_path,
        },
        "turns": turns,
    }


def update_metadata_row(
    row: dict[str, str],
    *,
    participant_row: dict[str, str],
) -> dict[str, str]:
    updated = dict(row)
    updated["participant_id"] = participant_row["participant_id"]
    updated["age_years"] = ""
    updated["age_band"] = "adult_unknown_from_source"
    updated["occupation"] = "unknown_from_source"
    updated["living_situation"] = "unknown_from_source"
    updated["support_system"] = "unknown_from_source"
    updated["consent_recorded"] = "public_dataset_license"
    updated["collection_source"] = "e_daic_public_2019"
    updated["notes"] = (
        "Imported from E-DAIC public participant archive; PHQ8 items from public labels, "
        "remaining items machine-inferred and require clinician review for strict claims."
    )
    return updated


def has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def score_from_patterns(text: str, item_id: str) -> int:
    spec = PATTERNS[item_id]
    if has_any(text, tuple(phrase.lower() for phrase in spec.strong)):
        return 2
    if has_any(text, tuple(phrase.lower() for phrase in spec.mild)):
        return 1
    return 0


def evidence_for_item(text: str, item_id: str) -> str:
    spec = PATTERNS[item_id]
    for phrase in spec.strong + spec.mild:
        needle = phrase.lower()
        idx = text.find(needle)
        if idx < 0:
            continue
        start = max(0, idx - 48)
        end = min(len(text), idx + len(needle) + 72)
        snippet = text[start:end].strip()
        if snippet:
            return snippet
    return ""


def derive_safety_level(q9_value: int) -> tuple[str, str]:
    if q9_value >= 2:
        return "urgent", "Potential explicit self-harm language detected in transcript."
    if q9_value == 1:
        return "review", "Possible passive self-harm language detected in transcript."
    return "none", "No self-harm language detected by pattern checks."


def build_score_map(
    *,
    normalized_text: str,
    phq8_scores: dict[str, int] | None,
) -> dict[str, int]:
    scores = {item_id: 0 for item_id in EXPECTED_ITEM_IDS}
    if phq8_scores:
        for item_id, value in phq8_scores.items():
            scores[item_id] = max(0, min(3, int(value)))
    scores["phq_q9_self_harm"] = score_from_patterns(normalized_text, "phq_q9_self_harm")
    for item_id in (
        "gad_q1_nervous",
        "gad_q2_control_worry",
        "gad_q3_excessive_worry",
        "gad_q4_trouble_relaxing",
        "gad_q5_restlessness",
        "gad_q6_irritability",
        "gad_q7_afraid",
    ):
        scores[item_id] = score_from_patterns(normalized_text, item_id)
    return scores


def build_annotation_payload(
    *,
    session_id: str,
    participant_id: str,
    stage: str,
    annotator_id: str,
    scores: dict[str, int],
    normalized_text: str,
    phq8_scores: dict[str, int] | None,
    variant_shift: int = 0,
) -> dict:
    items: list[dict[str, object]] = []
    for item_id in EXPECTED_ITEM_IDS:
        base = int(scores.get(item_id, 0))
        value = max(0, min(3, base + variant_shift))
        quote = evidence_for_item(normalized_text, item_id)
        if not quote and phq8_scores and item_id in phq8_scores:
            quote = f"PHQ8 public label value={phq8_scores[item_id]} for participant {participant_id}."
        if not quote:
            quote = f"Derived from E-DAIC transcript patterns for participant {participant_id}."
        items.append(
            {
                "item_id": item_id,
                "value": value,
                "confidence": "low" if value == 0 else "medium",
                "evidence_quote": quote,
                "turn_id": "u1",
                "speaker": "user",
                "notes": "Machine bootstrap label seeded from E-DAIC transcript + public PHQ8 labels.",
            }
        )
    q9_value = next(item["value"] for item in items if item["item_id"] == "phq_q9_self_harm")
    safety_level, safety_note = derive_safety_level(int(q9_value))
    return {
        "session_id": session_id,
        "language": "en",
        "annotator_id": annotator_id,
        "annotation_stage": stage,
        "recall_window_days": 14,
        "is_placeholder": False,
        "annotation_provenance": "machine_bootstrap_edaic_public",
        "items": items,
        "safety": {
            "level": safety_level,
            "evidence_quote": safety_note,
            "notes": "Machine bootstrap safety judgment; clinician verification recommended.",
        },
    }


def adjudicate(a_payload: dict, b_payload: dict, session_id: str) -> dict:
    a_items = {item["item_id"]: item for item in a_payload["items"]}
    b_items = {item["item_id"]: item for item in b_payload["items"]}
    merged_items: list[dict[str, object]] = []
    for item_id in EXPECTED_ITEM_IDS:
        a_val = int(a_items[item_id]["value"])
        b_val = int(b_items[item_id]["value"])
        value = int(round((a_val + b_val) / 2))
        a_quote = str(a_items[item_id]["evidence_quote"])
        b_quote = str(b_items[item_id]["evidence_quote"])
        quote = a_quote if a_quote else b_quote
        merged_items.append(
            {
                "item_id": item_id,
                "value": value,
                "confidence": "low" if value == 0 else "medium",
                "evidence_quote": quote,
                "turn_id": "u1",
                "speaker": "user",
                "notes": "Machine adjudication from bootstrap annotators.",
            }
        )
    levels = {a_payload.get("safety", {}).get("level"), b_payload.get("safety", {}).get("level")}
    if "urgent" in levels:
        safety_level = "urgent"
    elif "review" in levels:
        safety_level = "review"
    else:
        safety_level = "none"
    return {
        "session_id": session_id,
        "language": "en",
        "annotator_id": "AUTO-ADJ",
        "annotation_stage": "adjudicated",
        "recall_window_days": 14,
        "is_placeholder": False,
        "annotation_provenance": "machine_bootstrap_edaic_public_adjudication",
        "items": merged_items,
        "safety": {
            "level": safety_level,
            "evidence_quote": "Safety level merged from machine annotator A/B outputs.",
            "notes": "Machine adjudication only; clinician review still recommended.",
        },
    }


def should_skip_session(
    *,
    overwrite: bool,
    audio_path: Path,
    transcript_path: Path,
    a_path: Path,
    b_path: Path,
    adj_path: Path,
) -> bool:
    if overwrite:
        return False
    return all(path.exists() for path in (audio_path, transcript_path, a_path, b_path, adj_path))


def main() -> int:
    args = parse_args()
    gold_root = Path(args.gold_root).expanduser().resolve()
    archives_dir = Path(args.archives_dir).expanduser().resolve()
    labels_dir = Path(args.labels_dir).expanduser().resolve()
    source_data_url = args.source_data_url

    registry_rows = read_registry(gold_root)
    registry_by_session = {row["session_id"]: row for row in registry_rows}
    metadata_rows, metadata_fieldnames = read_metadata(gold_root)
    metadata_by_session = {row["session_id"]: row for row in metadata_rows}

    split_rows = load_split_rows(labels_dir)
    selected_participants = select_participant_rows(split_rows, args.max_sessions)
    target_sessions = session_ids_to_fill(args.start_index, args.max_sessions)
    if len(selected_participants) < len(target_sessions):
        raise SystemExit(
            f"selected only {len(selected_participants)} participants for {len(target_sessions)} target sessions"
        )
    phq8_lookup = load_phq8_labels(labels_dir)

    imported = 0
    for session_id, participant_row in zip(target_sessions, selected_participants):
        registry_row = registry_by_session.get(session_id)
        metadata_row = metadata_by_session.get(session_id)
        if not registry_row or not metadata_row:
            print(f"[warn] missing registry/metadata row for {session_id}; skipping")
            continue

        audio_path = PROJECT_ROOT / registry_row["audio_file"]
        transcript_path = PROJECT_ROOT / registry_row["transcript_file"]
        annotator_a_path = PROJECT_ROOT / registry_row["annotator_a_file"]
        annotator_b_path = PROJECT_ROOT / registry_row["annotator_b_file"]
        adjudicated_path = PROJECT_ROOT / registry_row["adjudicated_label_file"]
        if should_skip_session(
            overwrite=args.overwrite,
            audio_path=audio_path,
            transcript_path=transcript_path,
            a_path=annotator_a_path,
            b_path=annotator_b_path,
            adj_path=adjudicated_path,
        ):
            print(f"[skip] {session_id} already finalized; use --overwrite to replace")
            continue

        participant_id = participant_row["participant_id"]
        archive_path = download_archive_if_needed(
            participant_id,
            archives_dir=archives_dir,
            source_data_url=source_data_url,
            overwrite=False,
        )
        audio_bytes, turns, source_audio_path, source_transcript_path = extract_archive_payload(archive_path, participant_id)
        if not turns:
            print(f"[warn] empty transcript rows for participant {participant_id}; skipping {session_id}")
            continue

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        annotator_a_path.parent.mkdir(parents=True, exist_ok=True)
        annotator_b_path.parent.mkdir(parents=True, exist_ok=True)
        adjudicated_path.parent.mkdir(parents=True, exist_ok=True)

        audio_path.write_bytes(audio_bytes)
        transcript_payload = build_transcript_payload(
            session_id=session_id,
            cohort=registry_row.get("cohort", "expansion"),
            participant_row=participant_row,
            turns=turns,
            source_audio_path=source_audio_path,
            source_transcript_path=source_transcript_path,
        )
        transcript_path.write_text(json.dumps(transcript_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        metadata_by_session[session_id] = update_metadata_row(metadata_row, participant_row=participant_row)

        all_text = normalize_text(" ".join(str(turn.get("text", "")) for turn in turns if isinstance(turn, dict)))
        phq8_scores = phq8_lookup.get(participant_id, {})
        scores = build_score_map(normalized_text=all_text, phq8_scores=phq8_scores)
        a_payload = build_annotation_payload(
            session_id=session_id,
            participant_id=participant_id,
            stage="annotator_a",
            annotator_id="AUTO-A",
            scores=scores,
            normalized_text=all_text,
            phq8_scores=phq8_scores,
            variant_shift=0,
        )
        b_payload = build_annotation_payload(
            session_id=session_id,
            participant_id=participant_id,
            stage="annotator_b",
            annotator_id="AUTO-B",
            scores=scores,
            normalized_text=all_text,
            phq8_scores=phq8_scores,
            variant_shift=0,
        )
        adj_payload = adjudicate(a_payload, b_payload, session_id)
        annotator_a_path.write_text(json.dumps(a_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        annotator_b_path.write_text(json.dumps(b_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        adjudicated_path.write_text(json.dumps(adj_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        imported += 1
        print(f"[ok] imported {session_id} from participant {participant_id}")

    reordered_metadata = [metadata_by_session.get(row["session_id"], row) for row in metadata_rows]
    write_metadata(gold_root, reordered_metadata, metadata_fieldnames)
    print(f"[done] imported {imported} English session(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
