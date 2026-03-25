from typing import Any, Dict, List

from manovarta_core.seed_data import load_seed_conversations as _load_seed_conversations
from manovarta_core.seed_data import load_seed_profiles as _load_seed_profiles


def load_seed_profiles() -> List[Dict[str, Any]]:
    return _load_seed_profiles()


def load_seed_conversations() -> List[Dict[str, Any]]:
    return _load_seed_conversations()
