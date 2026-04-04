from __future__ import annotations

import json
from typing import Optional, Tuple

from manovarta_core.config import RuntimeConfig
from manovarta_core.knowledge import knowledge_summary_for_topic, profile_summary
from manovarta_core.json_utils import normalize_safety_level, parse_extractor_payload, parse_json_object
from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.schemas import ChatSession, SafetyFlag, ScreeningSnapshot, Turn

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
                model=self.config.chat_model,
                token=self.config.hf_token,
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
        dialogue = snapshot.coverage.dialogue
        focus_label = ITEM_INDEX[target_item].label if target_item else "general follow-up"
        transcript = "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in session.turns[-8:]
        )
        unresolved = ", ".join(snapshot.unresolved_items[:6]) or "none"
        safety = snapshot.safety.level
        profile_context = profile_summary(session.profile)
        topic_knowledge = knowledge_summary_for_topic(dialogue.target_topic)

        system_prompt = (
            "You are ManoVarta, a multilingual mental health screening assistant. "
            "You are not a therapist and you do not diagnose. "
            "Write one concise follow-up question or one brief closing message. "
            "Stay in the user's language. Use at most two sentences and prefer one focused question. "
            "Mirror the user's pacing and level of detail without sounding scripted. "
            "If the user is guarded or brief, ask one smaller concrete follow-up and make it clear that a short answer is okay. "
            "If the user is detailed, let them continue in their own words instead of forcing a checklist. "
            "If the user's code-mix is medium or high, mirror it lightly and naturally without caricature or slang overload. "
            "Sound warm, calm, and respectful. "
            "Do not mention PHQ-9 or GAD-7. "
            "If safety is urgent, do not continue screening."
        )
        user_prompt = (
            f"Language: {session.language}\n"
            f"Safety level: {safety}\n"
            f"Dialogue stage: {dialogue.stage}\n"
            f"Next action: {dialogue.next_action}\n"
            f"Current topic: {dialogue.current_topic}\n"
            f"Target topic: {dialogue.target_topic}\n"
            f"Target focus: {focus_label}\n"
            f"Transition hint: {dialogue.transition_hint}\n"
            f"User profile context: {profile_context}\n"
            f"User style: verbosity={dialogue.user_style.verbosity}, openness={dialogue.user_style.openness}, code_mix={dialogue.user_style.code_mix}, distress_trend={dialogue.user_style.distress_trend}, empathy_level={dialogue.user_style.empathy_level}\n"
            f"Disclosure efficiency: items_per_turn={dialogue.disclosure.items_per_user_turn}, resolved_per_turn={dialogue.disclosure.resolved_per_user_turn}\n"
            f"Unresolved items: {unresolved}\n"
            f"Knowledge guidance: {topic_knowledge}\n"
            f"Planner rationale: {dialogue.rationale}\n"
            f"Fallback text: {fallback_text}\n"
            f"Recent transcript:\n{transcript}\n\n"
            "Draft the next assistant turn so it feels natural, empathetic, and aligned with the user's style."
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


class HuggingFaceExtractor:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._client = None
        if self.config.huggingface_enabled and InferenceClient is not None:
            self._client = InferenceClient(
                model=self.config.extraction_model,
                token=self.config.hf_token,
                timeout=self.config.hf_timeout,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def extract(self, turns: list[Turn], language: str) -> Optional[dict]:
        if not self.enabled:
            return None

        transcript = "\n".join(f"{turn.speaker}: {turn.text}" for turn in turns[-12:])
        item_lines = "\n".join(
            f"- {item_id}: {item.label} ({item.focus})"
            for item_id, item in ITEM_INDEX.items()
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You extract questionnaire-aligned evidence from mental health screening transcripts. "
                    "Return strict JSON only. "
                    "Use only the schema requested. "
                    "Do not add markdown fences. "
                    "Be conservative. Do not guess unsupported symptoms. "
                    "Use safety_level exactly as one of: none, review, urgent. "
                    "Never invent alternate labels like high_caution or moderate_risk."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language}\n"
                    "Use these item ids and meanings:\n"
                    f"{item_lines}\n\n"
                    "Scoring rubric:\n"
                    "- 0 = not supported or denied\n"
                    "- 1 = mild, vague, or occasional support\n"
                    "- 2 = clear support or repeated mention\n"
                    "- 3 = severe, near-daily, or strongly impairing support\n\n"
                    "Return JSON with keys: items, safety_level.\n"
                    "items must be a list of objects with item_id and value only.\n"
                    "Only include items with value 1, 2, or 3.\n"
                    "safety_level must be one of: none, review, urgent.\n"
                    "Use safety_level review for indirect disappearance language and urgent for direct self-harm intent.\n"
                    f"Clinical guidance summary:\n{knowledge_summary_for_topic('mood')}\n{knowledge_summary_for_topic('anxiety')}\n{knowledge_summary_for_topic('safety')}\n\n"
                    f"Transcript:\n{transcript}"
                ),
            },
        ]

        try:
            output = self._client.chat_completion(
                messages=messages,
                temperature=0.0,
                max_tokens=self.config.extraction_max_tokens,
            )
            content = output.choices[0].message.content
            return self._parse_json(content)
        except Exception:
            return None

    def _parse_json(self, content: str) -> Optional[dict]:
        return parse_extractor_payload(content)


class HuggingFaceSafetyAssessor:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._client = None
        if self.config.huggingface_enabled and InferenceClient is not None:
            self._client = InferenceClient(
                model=self.config.safety_model,
                token=self.config.hf_token,
                timeout=self.config.hf_timeout,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def assess(self, turns: list[Turn], language: str) -> Optional[SafetyFlag]:
        if not self.enabled:
            return None

        transcript = "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in turns[-12:]
        ).strip()
        if not transcript:
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a conservative safety reviewer for a mental health screening assistant. "
                    "Return strict JSON only. "
                    "Use one of these levels: none, review, urgent. "
                    "urgent means direct self-harm intent, plan, means, or immediate risk. "
                    "review means indirect disappearance language, hopelessness with collapse, or self-harm concern without clear immediacy. "
                    "Prefer review over none when uncertain."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language}\n"
                    "Return JSON with keys: level, cues, rationale.\n"
                    "cues must be a short list of exact quoted phrases or short descriptions.\n"
                    "Do not include markdown.\n"
                    f"Transcript:\n{transcript}"
                ),
            },
        ]

        try:
            output = self._client.chat_completion(
                messages=messages,
                temperature=0.0,
                max_tokens=self.config.safety_max_tokens,
            )
        except Exception:
            return None

        payload = self._parse_json(output.choices[0].message.content)
        if not payload:
            return None

        level = payload.get("level", "none")
        level = normalize_safety_level(level)
        cues = [str(cue).strip() for cue in payload.get("cues", []) if str(cue).strip()]
        rationale = str(payload.get("rationale", "")).strip() or None
        return SafetyFlag(
            level=level,
            cues=cues,
            rationale=rationale,
            needs_human_review=level in {"review", "urgent"},
        )

    def _parse_json(self, content: str) -> Optional[dict]:
        return parse_json_object(content)
