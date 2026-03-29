import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT / ".env.local", override=False)


@dataclass(frozen=True)
class RuntimeConfig:
    model_provider: str
    chat_model: str
    extraction_model: str
    safety_model: Optional[str]
    hf_token: Optional[str]
    hf_timeout: float
    assistant_temperature: float
    assistant_max_tokens: int
    extraction_max_tokens: int
    safety_max_tokens: int
    semantic_safety_model: Optional[str]
    semantic_safety_review_threshold: float
    semantic_safety_urgent_threshold: float

    @property
    def huggingface_enabled(self) -> bool:
        return bool(self.hf_token and self.model_provider == "huggingface")

    @property
    def semantic_safety_enabled(self) -> bool:
        return bool(self.semantic_safety_model)


@lru_cache(maxsize=1)
def get_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        model_provider=os.getenv("MANOVARTA_MODEL_PROVIDER", "huggingface"),
        chat_model=os.getenv("MANOVARTA_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        extraction_model=os.getenv("MANOVARTA_EXTRACTION_MODEL", "CohereLabs/aya-expanse-32b"),
        safety_model=os.getenv("MANOVARTA_SAFETY_MODEL", os.getenv("MANOVARTA_EXTRACTION_MODEL", "CohereLabs/aya-expanse-32b")),
        hf_token=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN"),
        hf_timeout=float(os.getenv("MANOVARTA_HF_TIMEOUT", "30")),
        assistant_temperature=float(os.getenv("MANOVARTA_ASSISTANT_TEMPERATURE", "0.2")),
        assistant_max_tokens=int(os.getenv("MANOVARTA_ASSISTANT_MAX_TOKENS", "180")),
        extraction_max_tokens=int(os.getenv("MANOVARTA_EXTRACTION_MAX_TOKENS", "480")),
        safety_max_tokens=int(os.getenv("MANOVARTA_SAFETY_MAX_TOKENS", "180")),
        semantic_safety_model=os.getenv("MANOVARTA_SEMANTIC_SAFETY_MODEL"),
        semantic_safety_review_threshold=float(os.getenv("MANOVARTA_SEMANTIC_REVIEW_THRESHOLD", "0.64")),
        semantic_safety_urgent_threshold=float(os.getenv("MANOVARTA_SEMANTIC_URGENT_THRESHOLD", "0.72")),
    )
