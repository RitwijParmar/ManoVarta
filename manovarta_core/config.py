import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT / ".env.local", override=False)

DEFAULT_LOCAL_SAFETY_CHECKPOINTS = (
    Path("outputs") / "local_safety_boost" / "safety-indicbert-best-infer-fp16",
    Path("outputs") / "local_safety_boost" / "safety-indicbert-best",
)


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
    live_llm_turn_threshold: int
    local_safety_checkpoint: Optional[str] = None

    @property
    def huggingface_enabled(self) -> bool:
        return bool(self.hf_token and self.model_provider == "huggingface")

    @property
    def local_inference_enabled(self) -> bool:
        return self.model_provider == "local"

    @property
    def semantic_safety_enabled(self) -> bool:
        return bool(self.semantic_safety_model)


def _is_checkpoint_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    if not (path / "config.json").exists():
        return False
    return (path / "model.safetensors").exists() or (path / "model.safetensors.index.json").exists()


def _download_gcs_checkpoint(uri: str) -> Optional[str]:
    if not uri.startswith("gs://"):
        return None
    try:
        from google.cloud import storage
    except Exception:
        return None

    _, remainder = uri.split("gs://", 1)
    bucket_name, prefix = remainder.split("/", 1)
    prefix = prefix.rstrip("/")
    cache_key = hashlib.sha1(uri.encode("utf-8")).hexdigest()[:12]
    local_root = Path(tempfile.gettempdir()) / "manovarta_local_safety_checkpoint" / cache_key
    marker = local_root / ".ready"
    if _is_checkpoint_dir(local_root) and marker.exists():
        return str(local_root)
    if local_root.exists():
        shutil.rmtree(local_root)
    local_root.mkdir(parents=True, exist_ok=True)

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(client.list_blobs(bucket, prefix=prefix))
    if not blobs:
        return None

    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        relative = Path(blob.name[len(prefix):].lstrip("/"))
        destination = local_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(destination)
    marker.write_text(uri, encoding="utf-8")
    return str(local_root)


def discover_local_safety_checkpoint(project_root: Path = PROJECT_ROOT) -> Optional[str]:
    explicit = os.getenv("MANOVARTA_LOCAL_SAFETY_CHECKPOINT")
    if explicit:
        if str(explicit).startswith("gs://"):
            downloaded = _download_gcs_checkpoint(str(explicit))
            if downloaded and _is_checkpoint_dir(Path(downloaded)):
                return downloaded
            return None
        expanded = Path(explicit).expanduser()
        return str(expanded)

    gcs_uri = os.getenv("MANOVARTA_LOCAL_SAFETY_CHECKPOINT_GCS_URI")
    if gcs_uri:
        downloaded = _download_gcs_checkpoint(gcs_uri)
        if downloaded and _is_checkpoint_dir(Path(downloaded)):
            return downloaded

    for relative_path in DEFAULT_LOCAL_SAFETY_CHECKPOINTS:
        candidate = project_root / relative_path
        if _is_checkpoint_dir(candidate):
            return str(candidate)
    return None


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
        live_llm_turn_threshold=int(os.getenv("MANOVARTA_LIVE_LLM_TURN_THRESHOLD", "2")),
        local_safety_checkpoint=discover_local_safety_checkpoint(),
    )
