from __future__ import annotations

import json
import time
from typing import Any, Optional, Tuple

from manovarta_core.config import RuntimeConfig
from manovarta_core.knowledge import knowledge_summary_for_topic, profile_summary
from manovarta_core.json_utils import normalize_extractor_payload, normalize_safety_level, parse_extractor_payload, parse_json_object
from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.schemas import ChatSession, SafetyFlag, ScreeningSnapshot, Turn

try:
    from huggingface_hub import InferenceClient
except ImportError:  # pragma: no cover
    InferenceClient = None


EXTRACTOR_TOPIC_GUIDANCE = ("mood", "sleep", "energy", "self_view", "focus", "anxiety", "safety")

EXTRACTOR_ITEM_HINTS = {
    "phq_q1_anhedonia": "flat or numb days, going quiet, saying maybe later, not caring enough to join usual activities",
    "phq_q2_low_mood": "heavy days, emptiness, stomach drop, flat most of the day, feeling down after things go quiet",
    "phq_q3_sleep": "late sleep onset, waking at 3 or 4, sleep breaking repeatedly, restless or messy sleep",
    "phq_q4_fatigue": "dragging through the day, wiped after work, low stamina, drained from the morning onward",
    "phq_q5_appetite": "late afternoon before eating, meals skipped unintentionally, eating whatever is quickest, appetite not like before",
    "phq_q6_worthlessness": "wasting everyone's time, never cut out for this, others better off without me, feeling weak or like a burden",
    "phq_q7_concentration": "staring at the same screen, reading the same paragraph repeatedly, mind not sticking to tasks, analysis going nowhere",
    "phq_q8_psychomotor": "paced around, could not sit still, keyed up, noticeably slowed speech or movement",
    "phq_q9_self_harm": "disappearing, not wanting to be here, taking pills, direct self-harm or suicide language",
    "gad_q1_nervous": "heart racing, chest tightness, jaw tight, on edge before calls, physical anxiety",
    "gad_q2_control_worry": "mind will not stop, replaying comments, thoughts keep looping, cannot switch off the worry",
    "gad_q3_excessive_worry": "worrying about many areas, rent and work and family, every outcome, all the what-ifs",
    "gad_q4_trouble_relaxing": "cannot switch off, cannot settle, replaying whole conversations, body staying tense after stress",
    "gad_q5_restlessness": "pacing around, cleaning or checking to avoid sitting still, chain se baith nahi pata",
    "gad_q6_irritability": "snappy for no good reason, choti baat par gussa, irritability from stress spillover",
    "gad_q7_fear_awful": "getting written up, not covering rent, something bad will happen, debt or catastrophe anticipation",
}


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

        transcript = self._build_extraction_transcript(turns)
        item_lines = self._item_lines(include_hints=False)
        attempts = [
            (
                self._build_extraction_messages(language, transcript, item_lines),
                min(self.config.extraction_max_tokens, 360),
            ),
            (
                self._build_compact_extraction_messages(language, transcript),
                min(self.config.extraction_max_tokens, 260),
            ),
            (
                self._build_compact_extraction_messages(language, self._build_extraction_transcript(turns, include_assistant=True)),
                min(self.config.extraction_max_tokens, 260),
            ),
        ]

        last_payload = None
        for index, (messages, max_tokens) in enumerate(attempts):
            try:
                output = self._client.chat_completion(
                    messages=messages,
                    temperature=0.0,
                    max_tokens=max_tokens,
                )
            except Exception:
                if index < len(attempts) - 1:
                    time.sleep(0.35 * (index + 1))
                continue
            payload = self._parse_json(output.choices[0].message.content)
            if payload is not None:
                if payload.get("items"):
                    return payload
                last_payload = payload
            if index < len(attempts) - 1:
                time.sleep(0.2)
        return last_payload

    def _parse_json(self, content: str) -> Optional[dict]:
        return parse_extractor_payload(content)

    def _build_extraction_transcript(self, turns: list[Turn], *, include_assistant: bool = False) -> str:
        selected_turns = turns[-12:] if include_assistant else [turn for turn in turns if turn.speaker == "user"][-6:]
        return "\n".join(f"{turn.speaker}: {turn.text}" for turn in selected_turns)

    def _run_candidate_pass(self, language: str, transcript: str, item_lines: str) -> Optional[dict]:
        try:
            output = self._client.chat_completion(
                messages=self._build_candidate_messages(language, transcript, item_lines),
                temperature=0.0,
                max_tokens=self.config.extraction_max_tokens,
            )
        except Exception:
            return None
        return self._parse_candidate_payload(output.choices[0].message.content)

    def _run_final_pass(
        self,
        language: str,
        transcript: str,
        item_lines: str,
        candidate_payload: Optional[dict],
    ) -> Optional[dict]:
        try:
            output = self._client.chat_completion(
                messages=self._build_final_messages(language, transcript, item_lines, candidate_payload),
                temperature=0.0,
                max_tokens=self.config.extraction_max_tokens,
            )
        except Exception:
            return None
        return self._parse_json(output.choices[0].message.content)

    def _item_lines(self, include_hints: bool = True) -> str:
        if include_hints:
            return "\n".join(
                f"- {item_id}: {item.label} ({item.focus}); common indirect cues: {EXTRACTOR_ITEM_HINTS.get(item_id, item.focus)}"
                for item_id, item in ITEM_INDEX.items()
            )
        return "\n".join(
            f"- {item_id}: {item.label} ({item.focus})"
            for item_id, item in ITEM_INDEX.items()
        )

    def _knowledge_guidance(self) -> str:
        return "\n".join(knowledge_summary_for_topic(topic) for topic in EXTRACTOR_TOPIC_GUIDANCE)

    def _coverage_reminders(self) -> str:
        return (
            "- Appetite: skipped meals, late afternoon before eating, or living on quick convenience food.\n"
            "- Worthlessness: wasting everyone's time, never cut out for this, weak, burden, others better off.\n"
            "- Concentration: staring at the same task, rereading, getting nowhere, mind not sticking.\n"
            "- Trouble relaxing: replaying comments, not switching off, carrying tension after stress.\n"
            "- Worry and awful outcomes: rent, work, family, money, or catastrophe expectations."
        )

    def _build_extraction_messages(self, language: str, transcript: str, item_lines: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You extract questionnaire-aligned evidence from mental health screening transcripts. "
                    "Return strict JSON only. "
                    "Use only the schema requested. "
                    "Do not add markdown fences. "
                    "Be conservative, but be exhaustive for all supported symptoms. "
                    "One user statement can support multiple items when the evidence clearly overlaps. "
                    "Use safety_level exactly as one of: none, review, urgent."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language}\n"
                    "Use these item ids and meanings:\n"
                    f"{item_lines}\n\n"
                    "Scoring rubric:\n"
                    "- 1 = mild, vague, occasional, or indirectly supported\n"
                    "- 2 = clear support, repeated mention, or definite functional impact\n"
                    "- 3 = severe, near-daily, escalating, or strongly impairing support\n\n"
                    "Return JSON with keys: items, safety_level, safety_cues, notes.\n"
                    "items must be a list of objects with item_id, value, evidence_quote, confidence_note.\n"
                    "Only include items with value 1, 2, or 3.\n"
                    "Look carefully for subtle but supported signals.\n"
                    "Treat indirect but concrete evidence as valid when it clearly implies the symptom.\n"
                    f"Coverage reminders:\n{self._coverage_reminders()}\n\n"
                    f"Transcript (prioritize user disclosures):\n{transcript}"
                ),
            },
        ]

    def _build_compact_extraction_messages(self, language: str, transcript: str) -> list[dict[str, str]]:
        compact_items = "\n".join(
            f"- {item_id}: {item.label}"
            for item_id, item in ITEM_INDEX.items()
        )
        return [
            {
                "role": "system",
                "content": (
                    "Extract supported questionnaire items from multilingual mental health transcripts. "
                    "Return strict JSON only with keys: items, safety_level, safety_cues, notes. "
                    "Only include supported items with values 1, 2, or 3. "
                    "Each item should include item_id, value, and evidence_quote. "
                    "Use safety_level exactly as one of: none, review, urgent."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language}\n"
                    "Supported item ids:\n"
                    f"{compact_items}\n\n"
                    "Indirect cues count when clearly supported, including: skipped meals, not sleeping through the night, "
                    "mind not sticking, feeling weak or like a burden, heart racing, replaying worries, wanting to disappear, "
                    "or saying everything should end.\n\n"
                    f"User disclosures:\n{transcript}"
                ),
            },
        ]

    def _build_candidate_messages(self, language: str, transcript: str, item_lines: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are a high-recall clinical evidence miner for questionnaire-aligned screening transcripts. "
                    "Return strict JSON only with keys: supported_items, safety_level, safety_cues, notes. "
                    "Each supported_items entry must include item_id, value, evidence_quote, confidence_note. "
                    "Be exhaustive for all directly stated and strongly implied symptoms. "
                    "One user phrase can support multiple items. "
                    "Indirect functional evidence counts when it clearly signals the symptom, such as missed meals, pacing, replaying conversations, "
                    "staring at the same screen, or feeling like others would be better off without them. "
                    "Do not add markdown fences. "
                    "Do not guess unsupported symptoms. "
                    "Use safety_level exactly as one of: none, review, urgent."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language}\n"
                    "Use these item ids, meanings, and indirect cue reminders:\n"
                    f"{item_lines}\n\n"
                    "Scoring rubric:\n"
                    "- 1 = mild, occasional, or indirectly supported\n"
                    "- 2 = clear support, repeated mention, or definite functional impact\n"
                    "- 3 = severe, near-daily, escalating, or strongly impairing support\n\n"
                    "Coverage reminders:\n"
                    "- Appetite may appear as skipped meals, late eating, or eating only whatever is quickest.\n"
                    "- Worthlessness may appear as self-blame, burden language, feeling weak, or saying others are better off.\n"
                    "- Concentration may appear as rereading, staring at the same task, or getting nowhere.\n"
                    "- Relaxation difficulty may appear as replaying comments, not switching off, or carrying body tension after stress.\n"
                    "- Fear that something awful will happen may appear as catastrophe expectations about money, work, or family consequences.\n"
                    f"Clinical guidance summary:\n{self._knowledge_guidance()}\n\n"
                    f"Transcript:\n{transcript}"
                ),
            },
        ]

    def _build_final_messages(
        self,
        language: str,
        transcript: str,
        item_lines: str,
        candidate_payload: Optional[dict],
    ) -> list[dict[str, str]]:
        if candidate_payload and candidate_payload.get("items"):
            candidate_lines = "\n".join(
                f"- {item['item_id']}: {item['value']} | quote={item.get('evidence_quote', '')} | note={item.get('confidence_note', '')}"
                for item in candidate_payload.get("items", [])
            )
        else:
            candidate_lines = "- none"

        return [
            {
                "role": "system",
                "content": (
                    "You verify and complete questionnaire-aligned extraction from screening transcripts. "
                    "Return strict JSON only with keys: items, safety_level, safety_cues, notes. "
                    "Each item must include item_id, value, evidence_quote, confidence_note. "
                    "Keep every candidate item that is truly supported and add any supported item that the first pass missed. "
                    "Prefer coverage of supported symptoms over minimality, but never invent unsupported evidence. "
                    "Use safety_level exactly as one of: none, review, urgent."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Language: {language}\n"
                    "Use these item ids and meanings:\n"
                    f"{item_lines}\n\n"
                    "Return only items with value 1, 2, or 3.\n"
                    "Focus especially on subtle but supported signals for appetite, worthlessness, concentration, trouble relaxing, irritability, "
                    "fear of awful outcomes, and control of worry.\n"
                    "Candidate support from pass 1:\n"
                    f"{candidate_lines}\n\n"
                    f"Clinical guidance summary:\n{self._knowledge_guidance()}\n\n"
                    f"Transcript:\n{transcript}"
                ),
            },
        ]

    def _parse_candidate_payload(self, content: str) -> Optional[dict]:
        payload = parse_json_object(content)
        if not isinstance(payload, dict):
            return None

        raw_items = payload.get("supported_items", payload.get("items", []))
        items = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            items.append(
                {
                    "item_id": raw_item.get("item_id"),
                    "value": raw_item.get("value"),
                    "evidence_quote": raw_item.get("evidence_quote") or raw_item.get("quote") or raw_item.get("evidence"),
                    "confidence_note": raw_item.get("confidence_note") or raw_item.get("reason") or raw_item.get("rationale"),
                }
            )
        return normalize_extractor_payload(
            {
                "items": items,
                "safety_level": payload.get("safety_level", "none"),
                "safety_cues": payload.get("safety_cues", []),
                "notes": payload.get("notes", ""),
            }
        )

    def _merge_payloads(self, candidate_payload: Optional[dict], final_payload: Optional[dict]) -> Optional[dict]:
        payloads = [payload for payload in (candidate_payload, final_payload) if payload]
        if not payloads:
            return None

        merged_items: dict[str, dict[str, Any]] = {}
        for payload in payloads:
            for item in payload.get("items", []):
                item_id = item["item_id"]
                current = merged_items.get(item_id)
                if current is None or self._prefer_item(item, current):
                    merged_items[item_id] = dict(item)

        safety_level = max((payload.get("safety_level", "none") for payload in payloads), key=self._safety_rank)
        safety_cues = []
        seen_cues = set()
        for payload in payloads:
            for cue in payload.get("safety_cues", []):
                cue_text = str(cue).strip()
                if cue_text and cue_text not in seen_cues:
                    seen_cues.add(cue_text)
                    safety_cues.append(cue_text)

        notes = " | ".join(
            note for note in (payload.get("notes", "").strip() for payload in payloads) if note
        )
        return normalize_extractor_payload(
            {
                "items": list(merged_items.values()),
                "safety_level": safety_level,
                "safety_cues": safety_cues,
                "notes": notes,
            }
        )

    def _prefer_item(self, candidate: dict[str, Any], current: dict[str, Any]) -> bool:
        if int(candidate.get("value", -1)) != int(current.get("value", -1)):
            return int(candidate.get("value", -1)) > int(current.get("value", -1))
        candidate_quote = str(candidate.get("evidence_quote", "") or "").strip()
        current_quote = str(current.get("evidence_quote", "") or "").strip()
        if bool(candidate_quote) != bool(current_quote):
            return bool(candidate_quote)
        candidate_note = str(candidate.get("confidence_note", "") or "").strip()
        current_note = str(current.get("confidence_note", "") or "").strip()
        return len(candidate_note) > len(current_note)

    def _safety_rank(self, level: str) -> int:
        return {"none": 0, "review": 1, "urgent": 2}.get(normalize_safety_level(level), 0)


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
