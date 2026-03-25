from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = PROJECT_ROOT / "data" / "seed"


def load_seed_records(prefix: str, key_name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in sorted(SEED_DIR.glob(f"{prefix}*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload:
            record_id = record[key_name]
            if record_id in seen_ids:
                raise ValueError(f"Duplicate seed record id detected: {record_id}")
            seen_ids.add(record_id)
            records.append(record)
    return records


def load_seed_profiles() -> list[dict[str, Any]]:
    return load_seed_records("patient_profiles", "patient_id")


def load_seed_conversations() -> list[dict[str, Any]]:
    return load_seed_records("conversations", "conversation_id")
