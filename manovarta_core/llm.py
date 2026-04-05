from __future__ import annotations

import json
import time
from functools import lru_cache
from threading import Lock
from typing import Any, Optional, Tuple

from manovarta_core.config import RuntimeConfig
from manovarta_core.knowledge import knowledge_summary_for_topic, profile_summary
from manovarta_core.json_utils import normalize_extractor_payload, normalize_safety_level, parse_extractor_payload, parse_json_object
from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.schemas import ChatSession, SafetyFlag, ScreeningSnapshot, Turn
from manovarta_core.text import extract_window, normalize_text

try:
    from huggingface_hub import InferenceClient
except ImportError:  # pragma: no cover
    InferenceClient = None

try:  # pragma: no cover
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:  # pragma: no cover
    AutoModelForCausalLM = None
    AutoTokenizer = None
    torch = None


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
ENGLISH_VERIFIER_FOCUS_ITEMS = (
    "gad_q1_nervous",
    "gad_q2_control_worry",
    "gad_q3_excessive_worry",
    "gad_q4_trouble_relaxing",
    "gad_q6_irritability",
    "phq_q3_sleep",
    "phq_q9_self_harm",
)
ENGLISH_CONTROL_WORRY_CUES = (
    "mind won't stop",
    "thoughts won't stop",
    "can't stop worrying",
    "cannot stop worrying",
    "replay whole conversations",
    "replaying comments from my advisor",
    "brain keeps replaying",
    "head keeps saying",
)
ENGLISH_EXCESSIVE_WORRY_CUES = (
    "get written up",
    "cover rent",
    "wrong thing",
    "messed up the marriage",
    "difficult calls",
    "work stuff",
    "advisor",
    "kids",
    "marriage",
    "rent",
)
ENGLISH_TROUBLE_RELAXING_CUES = (
    "can't really switch off",
    "cannot really switch off",
    "can't switch off",
    "cannot switch off",
    "replay whole conversations",
    "replaying comments from my advisor",
    "pace around",
    "pacing around",
    "do not sit still",
    "can't sit still",
)


class _ChatCompletionMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _ChatCompletionChoice:
    def __init__(self, content: str) -> None:
        self.message = _ChatCompletionMessage(content)


class _ChatCompletionOutput:
    def __init__(self, content: str) -> None:
        self.choices = [_ChatCompletionChoice(content)]


@lru_cache(maxsize=4)
def _load_local_generation_backend(model_name: str, token: Optional[str]):
    if AutoTokenizer is None or AutoModelForCausalLM is None or torch is None:
        raise RuntimeError("transformers runtime is not installed")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        token=token,
        trust_remote_code=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        token=token,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model.eval()
    return tokenizer, model


class _LocalGenerationClient:
    def __init__(self, model_name: str, token: Optional[str]) -> None:
        self._tokenizer, self._model = _load_local_generation_backend(model_name, token)
        self._lock = Lock()

    def chat_completion(self, *, messages, temperature: float, max_tokens: int):
        prompt_inputs = self._apply_template(messages)
        generation_kwargs = {
            "max_new_tokens": min(max_tokens, 96),
            "pad_token_id": self._tokenizer.pad_token_id or self._tokenizer.eos_token_id,
            "eos_token_id": self._tokenizer.eos_token_id,
            "do_sample": temperature > 0.05,
        }
        if generation_kwargs["do_sample"]:
            generation_kwargs["temperature"] = max(temperature, 0.2)

        with self._lock:
            with torch.inference_mode():
                generated = self._model.generate(**prompt_inputs, **generation_kwargs)

        prompt_length = prompt_inputs["input_ids"].shape[-1]
        completion = generated[:, prompt_length:]
        content = self._tokenizer.batch_decode(completion, skip_special_tokens=True)[0].strip()
        return _ChatCompletionOutput(content)

    def _apply_template(self, messages):
        try:
            model_inputs = self._tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
        except Exception:
            prompt = "\n".join(f"{message['role']}: {message['content']}" for message in messages) + "\nassistant:"
            model_inputs = self._tokenizer(prompt, return_tensors="pt")
        return model_inputs


def _build_text_generation_client(config: RuntimeConfig, model_name: str):
    if config.local_inference_enabled:
        try:
            return _LocalGenerationClient(model_name, config.hf_token)
        except Exception:
            return None
    if config.huggingface_enabled and InferenceClient is not None:
        return InferenceClient(
            model=model_name,
            token=config.hf_token,
            timeout=config.hf_timeout,
        )
    return None


class HuggingFaceResponder:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._client = _build_text_generation_client(self.config, self.config.chat_model)

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
        return cleaned, self.config.model_provider

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
            for turn in session.turns[-6:]
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
        self._client = _build_text_generation_client(self.config, self.config.extraction_model)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def extract(self, turns: list[Turn], language: str) -> Optional[dict]:
        if not self.enabled:
            return None

        if self.config.local_inference_enabled:
            transcript = self._build_extraction_transcript(turns)
            full_transcript = self._build_extraction_transcript(turns, include_assistant=True)
            item_lines = self._item_lines(include_hints=False)
            payload = self._run_attempt_sequence(
                language,
                transcript,
                full_transcript,
                item_lines,
                prefer_compact=True,
            )
            if language.lower() == "en":
                return self._refine_english_anxiety_payload(full_transcript, payload)
            return payload

        if language.lower() == "en":
            return self._extract_with_english_windows(turns)

        transcript = self._build_extraction_transcript(turns)
        full_transcript = self._build_extraction_transcript(turns, include_assistant=True)
        item_lines = self._item_lines(include_hints=False)
        return self._run_attempt_sequence(language, transcript, full_transcript, item_lines)

    def _extract_with_english_windows(self, turns: list[Turn]) -> Optional[dict]:
        item_lines = self._item_lines(include_hints=False)
        merged_payload = None
        for transcript in self._build_english_window_transcripts(turns):
            payload = self._run_attempt_sequence(
                "en",
                transcript,
                transcript,
                item_lines,
                prefer_compact=True,
            )
            merged_payload = self._merge_payloads(merged_payload, payload)

        full_transcript = self._build_extraction_transcript(turns, include_assistant=True)
        verifier_payload = self._run_english_verifier(full_transcript, item_lines, merged_payload)
        merged_payload = self._merge_payloads(merged_payload, verifier_payload)
        if merged_payload and merged_payload.get("items"):
            return self._refine_english_anxiety_payload(full_transcript, merged_payload)

        fallback_payload = self._run_attempt_sequence(
            "en",
            self._build_extraction_transcript(turns),
            full_transcript,
            item_lines,
            prefer_compact=True,
        )
        if fallback_payload:
            return self._refine_english_anxiety_payload(full_transcript, fallback_payload)
        return fallback_payload

    def _run_attempt_sequence(
        self,
        language: str,
        primary_transcript: str,
        fallback_transcript: str,
        item_lines: str,
        *,
        prefer_compact: bool = False,
    ) -> Optional[dict]:
        attempts = self._build_attempts(
            language,
            primary_transcript,
            fallback_transcript,
            item_lines,
            prefer_compact=prefer_compact,
        )
        if self.config.local_inference_enabled:
            attempts = attempts[:1]

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

    def _build_attempts(
        self,
        language: str,
        primary_transcript: str,
        fallback_transcript: str,
        item_lines: str,
        *,
        prefer_compact: bool = False,
    ) -> list[tuple[list[dict[str, str]], int]]:
        if self.config.local_inference_enabled:
            return [
                (
                    self._build_compact_extraction_messages(language, primary_transcript),
                    min(self.config.extraction_max_tokens, 96),
                ),
            ]

        if prefer_compact:
            return [
                (
                    self._build_compact_extraction_messages(language, primary_transcript),
                    min(self.config.extraction_max_tokens, 240),
                ),
                (
                    self._build_extraction_messages(language, primary_transcript, item_lines),
                    min(self.config.extraction_max_tokens, 300),
                ),
                (
                    self._build_compact_extraction_messages(language, fallback_transcript),
                    min(self.config.extraction_max_tokens, 240),
                ),
            ]

        return [
            (
                self._build_extraction_messages(language, primary_transcript, item_lines),
                min(self.config.extraction_max_tokens, 360),
            ),
            (
                self._build_compact_extraction_messages(language, primary_transcript),
                min(self.config.extraction_max_tokens, 260),
            ),
            (
                self._build_compact_extraction_messages(language, fallback_transcript),
                min(self.config.extraction_max_tokens, 260),
            ),
        ]

    def _parse_json(self, content: str) -> Optional[dict]:
        return parse_extractor_payload(content)

    def _build_extraction_transcript(self, turns: list[Turn], *, include_assistant: bool = False) -> str:
        if self.config.local_inference_enabled:
            selected_turns = turns[-8:] if include_assistant else [turn for turn in turns if turn.speaker == "user"][-4:]
        else:
            selected_turns = turns[-12:] if include_assistant else [turn for turn in turns if turn.speaker == "user"][-6:]
        return "\n".join(f"{turn.speaker}: {turn.text}" for turn in selected_turns)

    def _build_english_window_transcripts(self, turns: list[Turn]) -> list[str]:
        user_indices = [index for index, turn in enumerate(turns) if turn.speaker == "user"]
        if not user_indices:
            return []
        if len(user_indices) <= 2:
            return [self._build_window_transcript(turns, 0, len(turns) - 1)]

        windows: list[str] = []
        seen = set()
        for start in range(len(user_indices) - 1):
            start_idx = user_indices[start]
            if start_idx > 0 and turns[start_idx - 1].speaker == "assistant":
                start_idx -= 1
            end_idx = user_indices[start + 1]
            window = self._build_window_transcript(turns, start_idx, end_idx)
            if window and window not in seen:
                seen.add(window)
                windows.append(window)

        full_transcript = self._build_extraction_transcript(turns, include_assistant=True)
        if full_transcript and full_transcript not in seen:
            windows.append(full_transcript)
        return windows

    def _build_window_transcript(self, turns: list[Turn], start_idx: int, end_idx: int) -> str:
        return "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in turns[start_idx:end_idx + 1]
        )

    def _run_english_verifier(
        self,
        transcript: str,
        item_lines: str,
        candidate_payload: Optional[dict],
    ) -> Optional[dict]:
        try:
            output = self._client.chat_completion(
                messages=self._build_english_verifier_messages(transcript, item_lines, candidate_payload),
                temperature=0.0,
                max_tokens=min(self.config.extraction_max_tokens, 320),
            )
        except Exception:
            return None
        return self._parse_json(output.choices[0].message.content)

    def _refine_english_anxiety_payload(self, transcript: str, payload: Optional[dict]) -> Optional[dict]:
        if not payload:
            return payload

        normalized = normalize_text(transcript)
        items = {item["item_id"]: dict(item) for item in payload.get("items", []) if item.get("item_id")}

        control_hit = self._find_first_cue(transcript, ENGLISH_CONTROL_WORRY_CUES)
        excessive_hit = self._find_first_cue(transcript, ENGLISH_EXCESSIVE_WORRY_CUES)
        relaxing_hit = self._find_first_cue(transcript, ENGLISH_TROUBLE_RELAXING_CUES)

        if control_hit:
            item = items.get("gad_q2_control_worry")
            value = 3 if any(phrase in normalized for phrase in ("mind won t stop", "thoughts won t stop", "can t stop worrying", "cannot stop worrying")) else 2
            if item is None or int(item.get("value", 0)) < value:
                items["gad_q2_control_worry"] = {
                    "item_id": "gad_q2_control_worry",
                    "value": value,
                    "evidence_quote": extract_window(transcript, control_hit),
                    "confidence_note": "Persistent looping or uncontrollable worry language.",
                }
            elif int(item.get("value", 0)) > value:
                item["value"] = value

        if excessive_hit:
            items["gad_q3_excessive_worry"] = self._prefer_structured_item(
                items.get("gad_q3_excessive_worry"),
                {
                    "item_id": "gad_q3_excessive_worry",
                    "value": 2,
                    "evidence_quote": extract_window(transcript, excessive_hit),
                    "confidence_note": "Concrete worry about outcomes across work, family, or finances.",
                },
            )

        if relaxing_hit:
            items["gad_q4_trouble_relaxing"] = self._prefer_structured_item(
                items.get("gad_q4_trouble_relaxing"),
                {
                    "item_id": "gad_q4_trouble_relaxing",
                    "value": 2,
                    "evidence_quote": extract_window(transcript, relaxing_hit),
                    "confidence_note": "Difficulty settling or switching off after stress.",
                },
            )

        refined = normalize_extractor_payload(
            {
                "items": list(items.values()),
                "safety_level": payload.get("safety_level", "none"),
                "safety_cues": payload.get("safety_cues", []),
                "notes": " | ".join(part for part in [payload.get("notes", "").strip(), "english_anxiety_refined"] if part),
            }
        )
        return refined or payload

    def _find_first_cue(self, transcript: str, cues: tuple[str, ...]) -> Optional[str]:
        normalized = normalize_text(transcript)
        for cue in cues:
            if normalize_text(cue) in normalized:
                return cue
        return None

    def _prefer_structured_item(self, current: Optional[dict[str, Any]], candidate: dict[str, Any]) -> dict[str, Any]:
        if current is None:
            return dict(candidate)
        return dict(candidate) if self._prefer_item(candidate, current) else current

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
                    "Keep evidence quotes short. "
                    "Use compact one-line JSON. "
                    'Example: {"items":[{"item_id":"phq_q3_sleep","value":2,"evidence_quote":"sleep breaks at 3 am"}],"safety_level":"none","safety_cues":[],"notes":"brief"}. '
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
                    "or saying everything should end.\n"
                    'If nothing is supported, return {"items":[],"safety_level":"none","safety_cues":[],"notes":"none"}.\n\n'
                    f"User disclosures:\n{transcript}"
                ),
            },
        ]

    def _build_english_verifier_messages(
        self,
        transcript: str,
        item_lines: str,
        candidate_payload: Optional[dict],
    ) -> list[dict[str, str]]:
        if candidate_payload and candidate_payload.get("items"):
            candidate_lines = "\n".join(
                f"- {item['item_id']}: {item['value']} | quote={item.get('evidence_quote', '')}"
                for item in candidate_payload["items"]
            )
        else:
            candidate_lines = "- none"
        focus_lines = "\n".join(
            f"- {item_id}: {ITEM_INDEX[item_id].label} ({EXTRACTOR_ITEM_HINTS.get(item_id, ITEM_INDEX[item_id].focus)})"
            for item_id in ENGLISH_VERIFIER_FOCUS_ITEMS
        )
        return [
            {
                "role": "system",
                "content": (
                    "You are verifying and completing English mental health symptom extraction from a short transcript. "
                    "Return strict JSON only with keys: items, safety_level, safety_cues, notes. "
                    "Keep supported candidate items, remove unsupported ones, and add any clearly supported missing items. "
                    "Pay extra attention to subtle English cues for nervousness, trouble relaxing, irritability, replaying worries, disrupted sleep, and disappearance or self-harm language. "
                    "Do not add markdown fences."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Language: en\n"
                    "Use these item ids and meanings:\n"
                    f"{item_lines}\n\n"
                    "Candidate support from earlier passes:\n"
                    f"{candidate_lines}\n\n"
                    "Priority English miss-check items:\n"
                    f"{focus_lines}\n\n"
                    "Return only supported items with values 1, 2, or 3.\n"
                    f"Transcript:\n{transcript}"
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
        self._client = _build_text_generation_client(self.config, self.config.safety_model) if self.config.safety_model else None

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
