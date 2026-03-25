from __future__ import annotations

from typing import Optional, Tuple

from manovarta_core.config import RuntimeConfig
from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.schemas import ChatSession, ScreeningSnapshot

try:
    from huggingface_hub import InferenceClient
except ImportError:  # pragma: no cover
    InferenceClient = None


class HuggingFaceResponder:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._client = None
        if self.config.huggingface_enabled and InferenceClient is not None:
            self._client = InferenceClient(
                provider="hf-inference",
                api_key=self.config.hf_token,
                timeout=self.config.hf_timeout,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def compose_reply(
        self,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        target_item: Optional[str],
        fallback_text: str,
    ) -> Tuple[str, str]:
        if not self.enabled or snapshot.safety.level == "urgent":
            return fallback_text, "template"

        try:
            messages = self._build_messages(session, snapshot, target_item, fallback_text)
            output = self._client.chat_completion(
                model=self.config.chat_model,
                messages=messages,
                temperature=self.config.assistant_temperature,
                max_tokens=self.config.assistant_max_tokens,
            )
            content = output.choices[0].message.content.strip()
        except Exception:
            return fallback_text, "template"

        cleaned = self._clean_content(content, fallback_text)
        if not cleaned:
            return fallback_text, "template"
        return cleaned, "huggingface"

    def _build_messages(
        self,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        target_item: Optional[str],
        fallback_text: str,
    ):
        focus_label = ITEM_INDEX[target_item].label if target_item else "general follow-up"
        transcript = "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in session.turns[-8:]
        )
        unresolved = ", ".join(snapshot.unresolved_items[:6]) or "none"
        safety = snapshot.safety.level

        system_prompt = (
            "You are ManoVarta, a multilingual mental health screening assistant. "
            "You are not a therapist and you do not diagnose. "
            "Write one concise follow-up question or one brief closing message. "
            "Stay in the user's language. Use at most two sentences. "
            "Do not mention PHQ-9 or GAD-7. "
            "If safety is urgent, do not continue screening."
        )
        user_prompt = (
            f"Language: {session.language}\n"
            f"Safety level: {safety}\n"
            f"Target focus: {focus_label}\n"
            f"Unresolved items: {unresolved}\n"
            f"Fallback text: {fallback_text}\n"
            f"Recent transcript:\n{transcript}\n\n"
            "Draft the next assistant turn."
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _clean_content(self, content: str, fallback_text: str) -> Optional[str]:
        cleaned = content.strip().strip('"')
        if not cleaned:
            return None
        if "diagnos" in cleaned.lower() or "therap" in cleaned.lower():
            return fallback_text
        return cleaned
