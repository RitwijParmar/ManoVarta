from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from manovarta_core.schemas import SafetyFlag, Turn


REVIEW_PROTOTYPES = [
    "I wish I could disappear for a while.",
    "Sab bekaar lag raha hai aur gayab ho jana hai.",
    "Nothing feels worth it and I want to vanish.",
]

URGENT_PROTOTYPES = [
    "I want to kill myself.",
    "Mujhe jeena nahi hai aur khud ko nuksan pahunchana hai.",
    "I am planning to hurt myself tonight.",
]


@dataclass(frozen=True)
class SemanticSafetyConfig:
    model_name: Optional[str] = None
    review_threshold: float = 0.64
    urgent_threshold: float = 0.72


class SemanticSafetyMonitor:
    def __init__(self, config: SemanticSafetyConfig) -> None:
        self.config = config
        self._backend = None
        self._review_vectors = None
        self._urgent_vectors = None

    @property
    def enabled(self) -> bool:
        return bool(self.config.model_name)

    def assess(self, turns: Iterable[Turn]) -> SafetyFlag:
        if not self.enabled:
            return SafetyFlag()

        user_text = "\n".join(turn.text for turn in turns if turn.speaker == "user").strip()
        if not user_text:
            return SafetyFlag()

        if self._backend is None:
            self._load_backend()
        if self._backend is None:
            return SafetyFlag()

        torch, tokenizer, model = self._backend
        conversation_vector = self._encode_texts(torch, tokenizer, model, [user_text])[0]
        review_score = torch.max(self._review_vectors @ conversation_vector).item()
        urgent_score = torch.max(self._urgent_vectors @ conversation_vector).item()

        if urgent_score >= self.config.urgent_threshold:
            return SafetyFlag(
                level="urgent",
                cues=[f"semantic:{self.config.model_name}", f"urgent_score:{urgent_score:.3f}"],
                rationale="Semantic encoder flagged urgent self-harm similarity.",
                needs_human_review=True,
            )
        if review_score >= self.config.review_threshold:
            return SafetyFlag(
                level="review",
                cues=[f"semantic:{self.config.model_name}", f"review_score:{review_score:.3f}"],
                rationale="Semantic encoder flagged review-level disappearance or hopelessness similarity.",
                needs_human_review=True,
            )
        return SafetyFlag()

    def _load_backend(self) -> None:
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError:  # pragma: no cover
            self._backend = None
            return

        try:
            tokenizer = AutoTokenizer.from_pretrained(self.config.model_name, trust_remote_code=True)
            model = AutoModel.from_pretrained(self.config.model_name, trust_remote_code=True)
        except OSError:  # pragma: no cover
            self._backend = None
            return
        model.eval()
        self._backend = (torch, tokenizer, model)
        self._review_vectors = self._encode_texts(torch, tokenizer, model, REVIEW_PROTOTYPES)
        self._urgent_vectors = self._encode_texts(torch, tokenizer, model, URGENT_PROTOTYPES)

    def _encode_texts(self, torch, tokenizer, model, texts):
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = model(**encoded, output_hidden_states=True)
        hidden = getattr(outputs, "last_hidden_state", None)
        if hidden is None:
            hidden = outputs.hidden_states[-1]
        mask = encoded["attention_mask"].unsqueeze(-1)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        return torch.nn.functional.normalize(pooled, p=2, dim=1)
