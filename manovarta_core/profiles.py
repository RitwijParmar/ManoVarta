import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = PROJECT_ROOT / "data" / "seed"


def load_seed_profiles() -> List[Dict[str, Any]]:
    with (SEED_DIR / "patient_profiles.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_seed_conversations() -> List[Dict[str, Any]]:
    with (SEED_DIR / "conversations.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)
