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
    live_chat_llm_analysis_enabled: bool = False
    live_llm_turn_threshold: int = 2
    live_chat_extraction_provider: str = ""
    live_chat_extraction_model: Optional[str] = None
    local_safety_checkpoint: Optional[str] = None
    local_load_in_4bit: bool = False
    local_chat_adapter: Optional[str] = None
    local_extraction_adapter: Optional[str] = None
    local_safety_adapter: Optional[str] = None
    chat_provider: str = ""
    extraction_provider: str = ""
    safety_provider: str = ""
    vertex_project: Optional[str] = None
    vertex_location: str = "us-central1"
    chat_fallback_model: Optional[str] = None
    live_chat_reply_model: Optional[str] = None
    live_chat_reply_fallback_model: Optional[str] = None
    live_chat_analysis_model: Optional[str] = None
    live_chat_analysis_fallback_model: Optional[str] = None
    live_chat_reply_timeout: float = 20.0
    live_chat_analysis_timeout: float = 12.0
    live_chat_reply_thinking_budget: int = 0
    live_chat_analysis_thinking_budget: int = 0
    vertex_chat_location: Optional[str] = None
    vertex_chat_fallback_location: Optional[str] = None
    vertex_live_chat_analysis_location: Optional[str] = None
    vertex_live_chat_analysis_fallback_location: Optional[str] = None
    remote_extraction_url: Optional[str] = None
    remote_extraction_timeout: float = 120.0
    live_chat_remote_extraction_timeout: float = 25.0
    remote_extraction_hybrid_enabled: bool = True
    async_scoring_enabled: bool = False
    async_scoring_dir: str = str(PROJECT_ROOT / "artifacts" / "async_scoring")
    startup_warmup_enabled: bool = False

    @property
    def huggingface_enabled(self) -> bool:
        return bool(
            self.hf_token
            and any(
                provider == "huggingface"
                for provider in (
                    self.chat_model_provider,
                    self.extraction_model_provider,
                    self.safety_model_provider,
                )
            )
        )

    @property
    def local_inference_enabled(self) -> bool:
        return any(
            provider == "local"
            for provider in (
                self.chat_model_provider,
                self.extraction_model_provider,
                self.safety_model_provider,
            )
        )

    @property
    def vertex_enabled(self) -> bool:
        return any(
            provider == "vertex"
            for provider in (
                self.chat_model_provider,
                self.extraction_model_provider,
                self.safety_model_provider,
            )
        )

    @property
    def chat_model_provider(self) -> str:
        return (self.chat_provider or self.model_provider).strip().lower()

    @property
    def extraction_model_provider(self) -> str:
        return (self.extraction_provider or self.model_provider).strip().lower()

    @property
    def safety_model_provider(self) -> str:
        return (self.safety_provider or self.model_provider).strip().lower()

    @property
    def live_chat_extraction_model_provider(self) -> str:
        return (self.live_chat_extraction_provider or self.extraction_model_provider).strip().lower()

    @property
    def semantic_safety_enabled(self) -> bool:
        return bool(self.semantic_safety_model)

    @property
    def resolved_chat_fallback_model(self) -> Optional[str]:
        fallback = (self.chat_fallback_model or "").strip()
        if not fallback or fallback == self.chat_model:
            return None
        return fallback

    @property
    def resolved_live_chat_analysis_model(self) -> str:
        return (self.live_chat_analysis_model or self.chat_model).strip()

    @property
    def resolved_live_chat_reply_model(self) -> str:
        return (self.live_chat_reply_model or self.chat_model).strip()

    @property
    def resolved_live_chat_reply_fallback_model(self) -> Optional[str]:
        fallback = (self.live_chat_reply_fallback_model or "").strip()
        if not fallback and self.resolved_live_chat_reply_model == self.chat_model.strip():
            fallback = (self.resolved_chat_fallback_model or "").strip()
        if not fallback or fallback == self.resolved_live_chat_reply_model:
            return None
        return fallback

    @property
    def resolved_live_chat_analysis_fallback_model(self) -> Optional[str]:
        fallback = (self.live_chat_analysis_fallback_model or self.resolved_chat_fallback_model or "").strip()
        if not fallback or fallback == self.resolved_live_chat_analysis_model:
            return None
        return fallback

    @property
    def resolved_vertex_chat_location(self) -> str:
        return (self.vertex_chat_location or self.vertex_location).strip()

    @property
    def resolved_vertex_chat_fallback_location(self) -> str:
        return (self.vertex_chat_fallback_location or self.resolved_vertex_chat_location).strip()

    @property
    def resolved_vertex_live_chat_analysis_location(self) -> str:
        return (self.vertex_live_chat_analysis_location or self.resolved_vertex_chat_location).strip()

    @property
    def resolved_vertex_live_chat_analysis_fallback_location(self) -> str:
        return (self.vertex_live_chat_analysis_fallback_location or self.resolved_vertex_chat_fallback_location).strip()


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
    startup_warmup_default = "true" if os.getenv("K_SERVICE") else "false"
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
        live_chat_llm_analysis_enabled=os.getenv("MANOVARTA_LIVE_CHAT_LLM_ANALYSIS", "false").strip().lower() in {"1", "true", "yes", "on"},
        live_llm_turn_threshold=int(os.getenv("MANOVARTA_LIVE_LLM_TURN_THRESHOLD", "2")),
        live_chat_extraction_provider=os.getenv("MANOVARTA_LIVE_CHAT_EXTRACTION_PROVIDER", ""),
        live_chat_extraction_model=os.getenv("MANOVARTA_LIVE_CHAT_EXTRACTION_MODEL"),
        local_safety_checkpoint=discover_local_safety_checkpoint(),
        local_load_in_4bit=os.getenv("MANOVARTA_LOCAL_LOAD_IN_4BIT", "false").strip().lower() in {"1", "true", "yes", "on"},
        local_chat_adapter=os.getenv("MANOVARTA_LOCAL_CHAT_ADAPTER"),
        local_extraction_adapter=os.getenv("MANOVARTA_LOCAL_EXTRACTION_ADAPTER"),
        local_safety_adapter=os.getenv("MANOVARTA_LOCAL_SAFETY_ADAPTER"),
        chat_provider=os.getenv("MANOVARTA_CHAT_PROVIDER", ""),
        extraction_provider=os.getenv("MANOVARTA_EXTRACTION_PROVIDER", ""),
        safety_provider=os.getenv("MANOVARTA_SAFETY_PROVIDER", ""),
        vertex_project=os.getenv("MANOVARTA_VERTEX_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT"),
        vertex_location=os.getenv("MANOVARTA_VERTEX_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")),
        chat_fallback_model=os.getenv("MANOVARTA_CHAT_FALLBACK_MODEL"),
        live_chat_reply_model=os.getenv("MANOVARTA_LIVE_CHAT_REPLY_MODEL"),
        live_chat_reply_fallback_model=os.getenv("MANOVARTA_LIVE_CHAT_REPLY_FALLBACK_MODEL"),
        live_chat_analysis_model=os.getenv("MANOVARTA_LIVE_CHAT_ANALYSIS_MODEL"),
        live_chat_analysis_fallback_model=os.getenv("MANOVARTA_LIVE_CHAT_ANALYSIS_FALLBACK_MODEL"),
        live_chat_reply_timeout=float(os.getenv("MANOVARTA_LIVE_CHAT_REPLY_TIMEOUT", "20")),
        live_chat_analysis_timeout=float(os.getenv("MANOVARTA_LIVE_CHAT_ANALYSIS_TIMEOUT", "12")),
        live_chat_reply_thinking_budget=int(os.getenv("MANOVARTA_LIVE_CHAT_REPLY_THINKING_BUDGET", "0")),
        live_chat_analysis_thinking_budget=int(os.getenv("MANOVARTA_LIVE_CHAT_ANALYSIS_THINKING_BUDGET", "0")),
        vertex_chat_location=os.getenv("MANOVARTA_VERTEX_CHAT_LOCATION"),
        vertex_chat_fallback_location=os.getenv("MANOVARTA_VERTEX_CHAT_FALLBACK_LOCATION"),
        vertex_live_chat_analysis_location=os.getenv("MANOVARTA_VERTEX_LIVE_CHAT_ANALYSIS_LOCATION"),
        vertex_live_chat_analysis_fallback_location=os.getenv("MANOVARTA_VERTEX_LIVE_CHAT_ANALYSIS_FALLBACK_LOCATION"),
        remote_extraction_url=os.getenv("MANOVARTA_REMOTE_EXTRACTION_URL"),
        remote_extraction_timeout=float(os.getenv("MANOVARTA_REMOTE_EXTRACTION_TIMEOUT", "120")),
        live_chat_remote_extraction_timeout=float(os.getenv("MANOVARTA_LIVE_CHAT_REMOTE_EXTRACTION_TIMEOUT", "25")),
        remote_extraction_hybrid_enabled=os.getenv("MANOVARTA_REMOTE_EXTRACTION_HYBRID", "true").strip().lower() in {"1", "true", "yes", "on"},
        async_scoring_enabled=os.getenv("MANOVARTA_ASYNC_SCORING_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
        async_scoring_dir=os.getenv("MANOVARTA_ASYNC_SCORING_DIR", str(PROJECT_ROOT / "artifacts" / "async_scoring")),
        startup_warmup_enabled=os.getenv("MANOVARTA_STARTUP_WARMUP", startup_warmup_default).strip().lower() in {"1", "true", "yes", "on"},
    )
