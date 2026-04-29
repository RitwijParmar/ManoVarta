from __future__ import annotations

import json
import re
import time
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

from manovarta_core.config import RuntimeConfig
from manovarta_core.dialogue import FREQUENCY_MARKERS, TIME_MARKERS
from manovarta_core.knowledge import knowledge_summary_for_topic, profile_summary
from manovarta_core.json_utils import normalize_extractor_payload, normalize_safety_level, parse_extractor_payload, parse_json_object
from manovarta_core.questionnaires import ITEM_INDEX
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import (
    ChatSession,
    DialogueAnalyzerEvidence,
    DialogueAnalyzerResult,
    SafetyFlag,
    ScreeningSnapshot,
    Turn,
)
from manovarta_core.text import extract_window, normalize_text

try:
    from huggingface_hub import InferenceClient
except ImportError:  # pragma: no cover
    InferenceClient = None

try:  # pragma: no cover
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
except ImportError:  # pragma: no cover
    vertexai = None
    GenerativeModel = None
    GenerationConfig = None

AutoModelForCausalLM = None
AutoTokenizer = None
BitsAndBytesConfig = None
PeftModel = None
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
    "gad_q7_afraid": "getting written up, not covering rent, something bad will happen, debt or catastrophe anticipation",
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
    "mind keeps looping",
    "thoughts keep looping",
    "can't stop worrying",
    "cannot stop worrying",
    "worrying a lot",
    "replay whole conversations",
    "replaying comments from my advisor",
    "brain keeps replaying",
    "head keeps saying",
)
ENGLISH_EXCESSIVE_WORRY_CUES = (
    "worrying a lot",
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
    "can't settle",
    "cannot settle",
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
def _load_local_generation_backend(
    model_name: str,
    token: Optional[str],
    adapter_path: Optional[str],
    load_in_4bit: bool,
):
    torch_module, auto_model_cls, auto_tokenizer_cls, quantization_cls, peft_model_cls = _import_local_runtime()

    resolved_adapter = _resolve_adapter_path(adapter_path)
    base_model_name = _resolve_base_model_name(model_name, resolved_adapter)
    tokenizer_source = _resolve_tokenizer_source(base_model_name, resolved_adapter)
    model_kwargs = {
        "token": token,
        "trust_remote_code": True,
    }

    if load_in_4bit and torch_module.cuda.is_available() and quantization_cls is not None:
        model_kwargs["quantization_config"] = quantization_cls(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=_preferred_cuda_dtype(torch_module),
        )
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["low_cpu_mem_usage"] = True
        if torch_module.cuda.is_available():
            model_kwargs["torch_dtype"] = _preferred_cuda_dtype(torch_module)

    tokenizer = auto_tokenizer_cls.from_pretrained(
        tokenizer_source,
        token=token,
        trust_remote_code=True,
    )
    model = auto_model_cls.from_pretrained(
        base_model_name,
        **model_kwargs,
    )
    if resolved_adapter and peft_model_cls is not None:
        model = peft_model_cls.from_pretrained(model, resolved_adapter, token=token)
    elif resolved_adapter and peft_model_cls is None:
        raise RuntimeError("peft is required to load adapter checkpoints")

    if "device_map" not in model_kwargs and torch_module.cuda.is_available():
        model.to("cuda")
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model.eval()
    return tokenizer, model, _infer_input_device(model), torch_module


def _import_local_runtime():
    global torch, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, PeftModel
    if torch is not None and AutoModelForCausalLM is not None and AutoTokenizer is not None:
        return torch, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, PeftModel
    try:  # pragma: no cover
        import torch as torch_module
        from transformers import AutoModelForCausalLM as auto_model_cls, AutoTokenizer as auto_tokenizer_cls, BitsAndBytesConfig as quantization_cls
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("transformers runtime is not installed") from exc
    try:  # pragma: no cover
        from peft import PeftModel as peft_model_cls
    except ImportError:  # pragma: no cover
        peft_model_cls = None
    torch = torch_module
    AutoModelForCausalLM = auto_model_cls
    AutoTokenizer = auto_tokenizer_cls
    BitsAndBytesConfig = quantization_cls
    PeftModel = peft_model_cls
    return torch, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, PeftModel


def _resolve_adapter_path(adapter_path: Optional[str]) -> Optional[str]:
    if not adapter_path:
        return None
    path = Path(adapter_path).expanduser()
    return str(path) if path.exists() else adapter_path


def _resolve_base_model_name(model_name: str, adapter_path: Optional[str]) -> str:
    model_path = Path(model_name).expanduser()
    if model_path.exists():
        return str(model_path)
    if not adapter_path:
        return model_name
    config_path = Path(adapter_path) / "adapter_config.json"
    if not config_path.exists():
        return model_name
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    resolved = payload.get("base_model_name_or_path", model_name)
    resolved_path = Path(str(resolved)).expanduser()
    return str(resolved_path) if resolved_path.exists() else resolved


def _resolve_tokenizer_source(model_name: str, adapter_path: Optional[str]) -> str:
    if not adapter_path:
        return model_name
    adapter_root = Path(adapter_path)
    tokenizer_files = ("tokenizer_config.json", "tokenizer.json", "special_tokens_map.json")
    if any((adapter_root / filename).exists() for filename in tokenizer_files):
        return str(adapter_root)
    return _resolve_base_model_name(model_name, adapter_path)


def _preferred_cuda_dtype(torch_module):
    if torch_module is None:
        return None
    if getattr(torch_module.cuda, "is_bf16_supported", lambda: False)():
        return torch_module.bfloat16
    return torch_module.float16


def _infer_input_device(model) -> Optional[str]:
    hf_device_map = getattr(model, "hf_device_map", None)
    if isinstance(hf_device_map, dict):
        for device in hf_device_map.values():
            if isinstance(device, int):
                return f"cuda:{device}"
            if isinstance(device, str) and device not in {"cpu", "disk"}:
                return device
    try:
        first_parameter = next(model.parameters())
        return str(first_parameter.device)
    except Exception:
        return None


class _LocalGenerationClient:
    def __init__(
        self,
        model_name: str,
        token: Optional[str],
        *,
        adapter_path: Optional[str] = None,
        load_in_4bit: bool = False,
    ) -> None:
        self._model_name = model_name
        self._token = token
        self._adapter_path = adapter_path
        self._load_in_4bit = load_in_4bit
        self._tokenizer = None
        self._model = None
        self._input_device = None
        self._torch = None
        self._lock = Lock()

    def chat_completion(self, *, messages, temperature: float, max_tokens: int):
        self._ensure_backend()
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
            with self._torch.inference_mode():
                generated = self._model.generate(**prompt_inputs, **generation_kwargs)

        prompt_length = prompt_inputs["input_ids"].shape[-1]
        completion = generated[:, prompt_length:]
        content = self._tokenizer.batch_decode(completion, skip_special_tokens=True)[0].strip()
        return _ChatCompletionOutput(content)

    def _ensure_backend(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return
        with self._lock:
            if self._tokenizer is not None and self._model is not None:
                return
            self._tokenizer, self._model, self._input_device, self._torch = _load_local_generation_backend(
                self._model_name,
                self._token,
                self._adapter_path,
                self._load_in_4bit,
            )

    def _apply_template(self, messages):
        try:
            model_inputs = self._tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=False,
                return_tensors="pt",
                return_dict=True,
            )
        except Exception:
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
        if self._input_device and self._input_device != "cpu":
            model_inputs = {
                key: value.to(self._input_device) if hasattr(value, "to") else value
                for key, value in model_inputs.items()
            }
        return model_inputs


class _VertexGenerationClient:
    def __init__(self, config: RuntimeConfig, model_name: str) -> None:
        if vertexai is None or GenerativeModel is None or GenerationConfig is None:
            raise RuntimeError("vertex runtime is not installed")
        if not config.vertex_project:
            raise RuntimeError("vertex project is not configured")
        self._config = config
        self._model_name = model_name
        self._lock = Lock()
        self._initialized = False

    def chat_completion(self, *, messages, temperature: float, max_tokens: int):
        wants_json = any(
            "return strict json only" in str(message.get("content", "")).strip().lower()
            or "return json with keys" in str(message.get("content", "")).strip().lower()
            for message in messages
        )
        system_instruction = "\n\n".join(
            message["content"].strip()
            for message in messages
            if message.get("role") == "system" and message.get("content")
        ).strip()
        prompt = "\n\n".join(
            f"{message.get('role', 'user').upper()}:\n{message.get('content', '').strip()}"
            for message in messages
            if message.get("content")
        ).strip()
        if not prompt:
            return _ChatCompletionOutput("")

        with self._lock:
            if not self._initialized:
                vertexai.init(project=self._config.vertex_project, location=self._config.vertex_location)
                self._initialized = True

            model = GenerativeModel(
                self._model_name,
                system_instruction=system_instruction or None,
            )
            response = model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json" if wants_json else "text/plain",
                ),
            )

        content = getattr(response, "text", "") or ""
        if not content and getattr(response, "candidates", None):
            parts = []
            for candidate in response.candidates:
                candidate_parts = getattr(getattr(candidate, "content", None), "parts", None) or []
                for part in candidate_parts:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        parts.append(part_text)
            content = "\n".join(parts).strip()
        return _ChatCompletionOutput(content.strip())


def _build_text_generation_client(
    config: RuntimeConfig,
    provider: str,
    model_name: str,
    *,
    adapter_path: Optional[str] = None,
):
    normalized_provider = (provider or config.model_provider).strip().lower()
    if normalized_provider == "local":
        try:
            return _LocalGenerationClient(
                model_name,
                config.hf_token,
                adapter_path=adapter_path,
                load_in_4bit=config.local_load_in_4bit,
            )
        except Exception:
            return None
    if normalized_provider == "vertex":
        try:
            return _VertexGenerationClient(config, model_name)
        except Exception:
            return None
    if normalized_provider == "huggingface" and config.hf_token and InferenceClient is not None:
        return InferenceClient(
            model=model_name,
            token=config.hf_token,
            timeout=config.hf_timeout,
        )
    return None


class HuggingFaceResponder:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._provider = self.config.chat_model_provider
        self._generation_clients = self._build_client_chain(
            primary_model=self.config.chat_model,
            fallback_model=self.config.resolved_chat_fallback_model,
            primary_location=self.config.resolved_vertex_chat_location,
            fallback_location=self.config.resolved_vertex_chat_fallback_location,
            adapter_path=self.config.local_chat_adapter,
        )
        self._analysis_clients = self._build_client_chain(
            primary_model=self.config.resolved_live_chat_analysis_model,
            fallback_model=self.config.resolved_live_chat_analysis_fallback_model,
            primary_location=self.config.resolved_vertex_live_chat_analysis_location,
            fallback_location=self.config.resolved_vertex_live_chat_analysis_fallback_location,
            adapter_path=self.config.local_chat_adapter,
        )
        self._client = self._generation_clients[0] if self._generation_clients else None

    @property
    def enabled(self) -> bool:
        return bool(self._active_generation_clients())

    def compose_reply(
        self,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        target_item: Optional[str],
        fallback_text: str,
    ) -> Tuple[str, str]:
        if not self.enabled or snapshot.safety.level == "urgent":
            return fallback_text, "template"
        if snapshot.safety.level == "review" and snapshot.coverage.dialogue.target_topic == "safety":
            return fallback_text, "template"
        if self._should_prefer_fallback(session, snapshot, target_item):
            return fallback_text, "template"

        analyzer_result = self._analyze_turn(session, snapshot, target_item)
        messages = self._build_messages(session, snapshot, target_item, fallback_text, analyzer_result=analyzer_result)
        for client in self._active_generation_clients():
            try:
                output = client.chat_completion(
                    messages=messages,
                    temperature=self.config.assistant_temperature,
                    max_tokens=self.config.assistant_max_tokens,
                )
                content = output.choices[0].message.content.strip()
            except Exception:
                continue

            cleaned = self._clean_content(content, fallback_text)
            if not cleaned:
                continue
            if (
                self._sounds_invalid_empathy(cleaned)
                or self._repeats_last_question(cleaned, session)
                or self._looks_like_meta_or_draft(cleaned)
                or self._contradicts_recent_channel(cleaned, session)
                or self._summary_stage_sounds_empty(cleaned, snapshot)
                or self._violates_analysis_constraints(cleaned, analyzer_result)
            ):
                continue
            return cleaned, self._provider
        return fallback_text, "template"

    def _build_client_chain(
        self,
        *,
        primary_model: str,
        fallback_model: Optional[str],
        primary_location: str,
        fallback_location: str,
        adapter_path: Optional[str],
    ) -> list[Any]:
        clients: list[Any] = []
        seen_specs: set[tuple[str, str, str, str]] = set()
        client_specs = [
            (primary_model, primary_location, adapter_path),
            (fallback_model, fallback_location, adapter_path),
        ]
        for model_name, location, adapter in client_specs:
            normalized_model = (model_name or "").strip()
            if not normalized_model:
                continue
            normalized_location = (location or self.config.vertex_location).strip()
            spec = (self._provider, normalized_model, normalized_location, adapter or "")
            if spec in seen_specs:
                continue
            seen_specs.add(spec)
            client = self._build_single_client(
                normalized_model,
                location=normalized_location,
                adapter_path=adapter,
            )
            if client is not None:
                clients.append(client)
        return clients

    def _active_generation_clients(self) -> list[Any]:
        legacy_client = getattr(self, "_client", None)
        if legacy_client is not None and (not self._generation_clients or legacy_client is not self._generation_clients[0]):
            return [legacy_client]
        return self._generation_clients

    def _active_analysis_clients(self) -> list[Any]:
        legacy_client = getattr(self, "_client", None)
        if legacy_client is not None and (not self._generation_clients or legacy_client is not self._generation_clients[0]):
            return [legacy_client]
        return self._analysis_clients

    def _build_single_client(
        self,
        model_name: str,
        *,
        location: str,
        adapter_path: Optional[str],
    ):
        client_config = self.config
        if self._provider == "vertex" and location and location != self.config.vertex_location:
            client_config = replace(self.config, vertex_location=location)
        return _build_text_generation_client(
            client_config,
            self._provider,
            model_name,
            adapter_path=adapter_path,
        )

    def _build_messages(
        self,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        target_item: Optional[str],
        fallback_text: str,
        *,
        analyzer_result: Optional[DialogueAnalyzerResult] = None,
    ):
        dialogue = snapshot.coverage.dialogue
        focus_label = ITEM_INDEX[target_item].label if target_item else "general follow-up"
        transcript = self._build_reply_transcript(session.turns)
        earlier_context = self._build_earlier_context(session.turns)
        unresolved = ", ".join(snapshot.unresolved_items[:6]) or "none"
        safety = snapshot.safety.level
        profile_context = profile_summary(session.profile)
        topic_knowledge = knowledge_summary_for_topic(dialogue.target_topic)
        style_guidance = self._build_style_guidance(dialogue)
        nudge_guidance = self._build_nudge_guidance(dialogue)
        coverage_debt = ", ".join(dialogue.coverage_debt) or "none"
        scene_items = ", ".join(dialogue.scene_item_ids) or "none"
        phq_queue = ", ".join(dialogue.phq_queue[:8]) or "none"
        gad_queue = ", ".join(dialogue.gad_queue[:7]) or "none"
        blocked_items = ", ".join(dialogue.blocked_items[:8]) or "none"
        recent_scenes = ", ".join(dialogue.recent_scenes[-4:]) or "none"
        recent_items = ", ".join(dialogue.recent_items[-4:]) or "none"
        recent_assistant_turns = " | ".join(
            turn.text.strip()
            for turn in [turn for turn in session.turns if turn.speaker == "assistant"][-3:]
            if turn.text.strip()
        ) or "none"
        analyzer_summary = self._render_analyzer_summary(analyzer_result)
        phq_remaining = len(dialogue.phq_queue)
        gad_remaining = len(dialogue.gad_queue)

        system_prompt = (
            "You are ManoVarta, a multilingual mental health screening assistant. "
            "You are not a therapist and you do not diagnose. "
            "Write one concise follow-up question or one brief summary-stage message. "
            "Stay in the user's language. Use at most two sentences and prefer one focused question. "
            "Mirror the user's pacing and level of detail without sounding scripted. "
            "Use autonomy-supportive phrasing like 'if easier' or 'you can pick one' for guarded or fatigued users. "
            "Never say 'great to hear', 'good to hear', or 'glad to hear' when the user is describing distress, symptoms, or impairment. "
            "If the user is guarded or brief, ask one smaller concrete follow-up and make it clear that a short answer is okay. "
            "If the user is detailed, let them continue in their own words instead of forcing a checklist. "
            "If the user's code-mix is medium or high, mirror it lightly and naturally without caricature or slang overload. "
            "Prefer one reflective line plus one concrete anchor over stacked empathy or multiple asks. "
            "If the planner suggests a compare, body, coping, support, or scale nudge, weave it in naturally instead of naming it like a technique. "
            "Do not sound gamified, competitive, or childish. "
            "Do not stack gratitude, continuity reminders, and reflective paraphrases in the same short reply. "
            "Do not repeat the previous assistant question in the same wording. "
            "Vary sentence openings and lexical choices across turns. "
            "Do not keep reusing opener shapes like 'It sounds like...', 'When this hits...', or the same contrast frame in back-to-back turns. "
            "If a recent assistant turn already used one sentence family, switch to a different family such as concrete example, daily impact, body-versus-mind, what slips first, or direct gap-closing. "
            "Do not reopen a resolved item unless the latest user turn clearly contradicts it. "
            "Do not switch from PHQ to GAD or GAD to PHQ unless the controller explicitly changed the active domain. "
            "Treat blocked items and recent scenes as off-limits for phrasing unless no other option remains. "
            "If the user already answered timing or frequency, move to what the symptom feels like, how strong it is, or how it affects the day. "
            "If closure mode is true and PHQ or GAD queue items still remain, you are in completion mode. "
            "In completion mode, ask one compact gap-closing question that directly targets the remaining item or a tightly related cluster, even if the wording is more direct than usual. "
            "Do not spend the turn on another broad reflection when queues remain. "
            "If recent assistant turns already used the same contrast or wording shape, do not paraphrase it again; move to a different unresolved area or ask a brief answerable check instead. "
            "If closure mode is true and queues remain, prefer closing one or two unresolved PHQ/GAD items over sounding poetic. "
            "Use contrasts like mood versus interest, appetite versus focus, or mind versus body, but do not sound like a checklist. "
            "If the user asks for a summary but Summary ready is false, give only a brief working reflection and then ask one natural high-yield follow-up instead of closing early. "
            "Do not treat a summary request as permission to stop when major coverage debt remains. "
            "If the dialogue stage is summary, give a plain-language working summary of the main pattern you have enough confidence to hold, "
            "and optionally mention one missing detail only if it truly matters. Do not just say that the conversation can stop. "
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
            f"Active domain: {dialogue.active_domain}\n"
            f"Domain locked: {dialogue.domain_locked}\n"
            f"Target focus: {focus_label}\n"
            f"Target scene: {dialogue.target_scene or 'none'}\n"
            f"Scene items: {scene_items}\n"
            f"Closure mode: {dialogue.closure_mode}\n"
            f"Transition hint: {dialogue.transition_hint}\n"
            f"Reflective anchor: {dialogue.reflective_anchor}\n"
            f"Continuity note: {dialogue.continuity_note}\n"
            f"User profile context: {profile_context}\n"
            f"User style: verbosity={dialogue.user_style.verbosity}, openness={dialogue.user_style.openness}, code_mix={dialogue.user_style.code_mix}, distress_trend={dialogue.user_style.distress_trend}, empathy_level={dialogue.user_style.empathy_level}, steering_preference={dialogue.user_style.steering_preference}\n"
            f"Disclosure efficiency: items_per_turn={dialogue.disclosure.items_per_user_turn}, resolved_per_turn={dialogue.disclosure.resolved_per_user_turn}, nudge_effectiveness={dialogue.disclosure.nudge_effectiveness}\n"
            f"Readiness: {dialogue.readiness}\n"
            f"Fatigue: {dialogue.fatigue}\n"
            f"Coverage debt topics: {coverage_debt}\n"
            f"PHQ queue: {phq_queue}\n"
            f"GAD queue: {gad_queue}\n"
            f"PHQ remaining count: {phq_remaining}\n"
            f"GAD remaining count: {gad_remaining}\n"
            f"Completion mode: {dialogue.closure_mode and (phq_remaining > 0 or gad_remaining > 0)}\n"
            f"Blocked items: {blocked_items}\n"
            f"Recent scenes: {recent_scenes}\n"
            f"Recent items: {recent_items}\n"
            f"Recent assistant turns: {recent_assistant_turns}\n"
            f"Analyzer summary: {analyzer_summary}\n"
            f"Continue intent: {dialogue.continue_intent}\n"
            f"Reopen signal: {dialogue.reopen_signal}\n"
            f"Summary ready: {dialogue.summary_ready}\n"
            f"Recommended nudge families: {', '.join(dialogue.recommended_nudges) or 'none'}\n"
            f"Style guidance: {style_guidance}\n"
            f"Nudge guidance: {nudge_guidance}\n"
            f"Unresolved items: {unresolved}\n"
            f"Knowledge guidance: {topic_knowledge}\n"
            f"Planner rationale: {dialogue.rationale}\n"
            f"Fallback text: {fallback_text}\n"
            f"Earlier context: {earlier_context}\n"
            f"Recent transcript:\n{transcript}\n\n"
            "Draft the next assistant turn so it feels natural, empathetic, and aligned with the user's style."
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _analyze_turn(
        self,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        target_item: Optional[str],
    ) -> Optional[DialogueAnalyzerResult]:
        if not self._analysis_enabled():
            return None
        messages = self._build_analysis_messages(session, snapshot, target_item)
        for client in self._active_analysis_clients():
            try:
                output = client.chat_completion(
                    messages=messages,
                    temperature=0.0,
                    max_tokens=min(max(self.config.assistant_max_tokens, 220), 320),
                )
            except Exception:
                continue
            parsed = self._parse_analysis_payload(output.choices[0].message.content)
            if parsed is not None:
                return parsed
        return None

    def _analysis_enabled(self) -> bool:
        return bool(
            self._active_analysis_clients()
            and self.config.live_chat_llm_analysis_enabled
            and self._provider in {"vertex", "huggingface", "local"}
        )

    def _build_analysis_messages(
        self,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        target_item: Optional[str],
    ) -> list[dict[str, str]]:
        dialogue = snapshot.coverage.dialogue
        focus_label = ITEM_INDEX[target_item].label if target_item else "general follow-up"
        transcript = self._build_reply_transcript(session.turns)
        compact_state = (
            f"language={session.language}; "
            f"active_domain={dialogue.active_domain}; "
            f"domain_locked={dialogue.domain_locked}; "
            f"target_topic={dialogue.target_topic}; "
            f"target_scene={dialogue.target_scene or 'none'}; "
            f"target_item={target_item or 'none'}; "
            f"focus_label={focus_label}; "
            f"phq_queue={','.join(dialogue.phq_queue[:6]) or 'none'}; "
            f"gad_queue={','.join(dialogue.gad_queue[:6]) or 'none'}; "
            f"blocked_items={','.join(dialogue.blocked_items[:6]) or 'none'}; "
            f"recent_items={','.join(dialogue.recent_items[-4:]) or 'none'}; "
            f"recent_scenes={','.join(dialogue.recent_scenes[-3:]) or 'none'}"
        )
        return [
            {
                "role": "system",
                "content": (
                "You are a structured multilingual mental-health conversation analyzer. "
                "Read the latest user turn plus compact dialogue state and return ONLY valid JSON. "
                "Do not hallucinate evidence. "
                "Do not infer self-harm from negated statements. "
                "If anxiety is explicitly downplayed, do not push the active domain to gad unless new positive evidence appears. "
                "If PHQ or GAD queue items still remain, prefer scene candidates that close those remaining items instead of repeating the last angle. "
                "Do not recommend summary-like behavior while PHQ or GAD queues still contain unresolved items."
            ),
            },
            {
                "role": "user",
                "content": (
                    f"Compact state: {compact_state}\n"
                    "Return JSON with this schema:\n"
                    "{"
                    "\"active_domain\":\"phq|gad|mixed|safety\","
                    "\"domain_confidence\":0.0,"
                    "\"stay_in_domain\":true,"
                    "\"user_intents\":[\"continue|summary|reopen|avoidance|clarify\"],"
                    "\"evidence_updates\":[{"
                    "\"item\":\"phq_q4_fatigue\","
                    "\"status\":\"resolved|partial|contradicted|none\","
                    "\"confidence\":0.0,"
                    "\"quote_span\":\"exact short span\","
                    "\"polarity\":\"positive|negative|mixed\""
                    "}],"
                    "\"scene_candidates\":[\"sleep_energy\",\"self_view\",\"worry_core\"],"
                    "\"blocked_pivots\":[\"gad\",\"sleep_timing\"],"
                    "\"negations\":[\"panic_denied\",\"self_harm_denied\"],"
                    "\"safety\":{\"level\":\"none|review|urgent\",\"reason\":\"short reason\"}"
                    "}\n"
                    "Prefer evidence from the latest user turn, but use brief recent context for continuity.\n"
                    f"Recent transcript:\n{transcript}"
                ),
            },
        ]

    def _parse_analysis_payload(self, content: str) -> Optional[DialogueAnalyzerResult]:
        payload = parse_json_object(content)
        if not isinstance(payload, dict):
            return None
        try:
            normalized_evidence = []
            for raw_item in payload.get("evidence_updates", []):
                if not isinstance(raw_item, dict):
                    continue
                normalized_evidence.append(
                    DialogueAnalyzerEvidence(
                        item=str(raw_item.get("item") or raw_item.get("item_id") or "").strip(),
                        status=str(raw_item.get("status") or "none").strip().lower() or "none",
                        confidence=float(raw_item.get("confidence", 0.0) or 0.0),
                        quote_span=str(raw_item.get("quote_span") or raw_item.get("evidence_quote") or "").strip(),
                        polarity=str(raw_item.get("polarity") or "positive").strip().lower() or "positive",
                    ).model_dump()
                )
            normalized_payload = {
                "active_domain": str(payload.get("active_domain") or "mixed").strip().lower() or "mixed",
                "domain_confidence": float(payload.get("domain_confidence", 0.0) or 0.0),
                "stay_in_domain": bool(payload.get("stay_in_domain", True)),
                "user_intents": [str(intent).strip() for intent in payload.get("user_intents", []) if str(intent).strip()],
                "evidence_updates": normalized_evidence,
                "scene_candidates": [str(scene).strip() for scene in payload.get("scene_candidates", []) if str(scene).strip()],
                "blocked_pivots": [str(pivot).strip() for pivot in payload.get("blocked_pivots", []) if str(pivot).strip()],
                "negations": [str(negation).strip() for negation in payload.get("negations", []) if str(negation).strip()],
                "safety": {
                    "level": normalize_safety_level((payload.get("safety") or {}).get("level", "none")),
                    "reason": str((payload.get("safety") or {}).get("reason", "")).strip(),
                },
            }
            return DialogueAnalyzerResult.model_validate(normalized_payload)
        except Exception:
            return None

    def _render_analyzer_summary(self, analyzer_result: Optional[DialogueAnalyzerResult]) -> str:
        if analyzer_result is None:
            return "none"
        evidence_bits = [
            f"{item.item}:{item.status}:{item.confidence:.2f}"
            for item in analyzer_result.evidence_updates[:4]
            if item.item
        ] or ["none"]
        return (
            f"domain={analyzer_result.active_domain}; "
            f"domain_confidence={analyzer_result.domain_confidence:.2f}; "
            f"stay_in_domain={analyzer_result.stay_in_domain}; "
            f"user_intents={','.join(analyzer_result.user_intents) or 'none'}; "
            f"scene_candidates={','.join(analyzer_result.scene_candidates) or 'none'}; "
            f"blocked_pivots={','.join(analyzer_result.blocked_pivots) or 'none'}; "
            f"negations={','.join(analyzer_result.negations) or 'none'}; "
            f"safety={analyzer_result.safety.level}; "
            f"evidence={','.join(evidence_bits)}"
        )

    def _violates_analysis_constraints(
        self,
        cleaned: str,
        analyzer_result: Optional[DialogueAnalyzerResult],
    ) -> bool:
        if analyzer_result is None:
            return False
        normalized = normalize_text(cleaned)
        blocked_pivots = set(analyzer_result.blocked_pivots)
        gad_markers = (
            "worry",
            "worried",
            "anxious",
            "anxiety",
            "panic",
            "on edge",
            "switch off",
            "settle",
            "restless",
            "pacing",
            "tense body",
            "body tension",
            "busy mind",
            "something bad",
            "चिंता",
            "घबराहट",
        )
        phq_markers = (
            "low mood",
            "sad",
            "sadness",
            "heavy mood",
            "losing interest",
            "interest drop",
            "appetite",
            "tired",
            "fatigue",
            "focus",
            "concentrat",
            "harsh on yourself",
            "worthless",
            "उदासी",
            "मन नहीं",
            "थकान",
        )
        safety_markers = (
            "hurt yourself",
            "not wanting to be alive",
            "end your life",
            "kill yourself",
            "खुद को नुकसान",
            "मरने",
        )

        if "self_harm_denied" in analyzer_result.negations and any(marker in normalized for marker in safety_markers):
            return True
        if "panic_denied" in analyzer_result.negations and "gad" in blocked_pivots and any(marker in normalized for marker in gad_markers):
            return True
        if "gad" in blocked_pivots and any(marker in normalized for marker in gad_markers):
            return True
        if "phq" in blocked_pivots and any(marker in normalized for marker in phq_markers):
            return True
        if analyzer_result.stay_in_domain and analyzer_result.active_domain == "phq":
            return any(marker in normalized for marker in gad_markers)
        if analyzer_result.stay_in_domain and analyzer_result.active_domain == "gad":
            return any(marker in normalized for marker in phq_markers)
        return False

    def _contradicts_recent_channel(self, cleaned: str, session: ChatSession) -> bool:
        latest_user_text = ""
        for turn in reversed(session.turns):
            if turn.speaker == "user":
                latest_user_text = normalize_text(turn.text)
                break
        if not latest_user_text:
            return False
        body_negations = (
            "no body issue",
            "not body",
            "mostly mental",
            "only mental",
            "body is not the issue",
            "body is not the main issue",
            "body tension not the main issue",
            "body tension isn t the main issue",
            "body tension is not the main issue",
            "body tension utni badi baat nahi",
            "body mein koi problem nahi",
            "body me koi problem nahi",
            "sharir mein koi samasya nahi",
            "शरीर में कोई समस्या नहीं",
            "शरीर में मुझे कोई समस्या नहीं",
            "शरीर में खास समस्या नहीं",
            "शरीर से ज्यादा दिमाग",
            "शरीर से ज़्यादा दिमाग",
            "body se zyada mind",
            "body se zyada mental",
            "केवल दिमाग",
            "सिर्फ दिमाग",
            "बस दिमाग",
        )
        cleaned_norm = normalize_text(cleaned)
        if any(marker in latest_user_text for marker in body_negations):
            contradictory = (
                "mind and body" in cleaned_norm
                or "both mind and body" in cleaned_norm
                or "दिमाग और शरीर दोनों" in cleaned_norm
                or "mind aur body dono" in cleaned_norm
                or "relax your body" in cleaned_norm
                or "body tension" in cleaned_norm
                or "tense body" in cleaned_norm
                or "body relax karna" in cleaned_norm
                or "शरीर को ढीला" in cleaned_norm
            )
            if contradictory:
                return True
        return False

    def _summary_stage_sounds_empty(self, cleaned: str, snapshot: ScreeningSnapshot) -> bool:
        if snapshot.coverage.dialogue.stage != "summary":
            return False
        cleaned_norm = normalize_text(cleaned)
        empty_summary_markers = (
            "we can pause here",
            "we can stop here",
            "you can stop here",
            "leave this here for now",
            "yahin viram rakh sakte hain",
            "हम अभी यहीं विराम रख सकते हैं",
            "when you want to continue",
            "jab aage badhna chahein",
        )
        if any(marker in cleaned_norm for marker in empty_summary_markers):
            summary_markers = (
                "working picture",
                "working summary",
                "तस्वीर बन रही है",
                "कामचलाऊ सार",
                "picture ban rahi hai",
            )
            return not any(marker in cleaned_norm for marker in summary_markers)
        return False

    def _build_style_guidance(self, dialogue) -> str:
        parts: list[str] = []
        if dialogue.fatigue == "high":
            parts.append("Keep the burden light and accept a short answer without pushing for a full story.")
        if dialogue.user_style.openness == "guarded":
            parts.append("Offer the easiest anchor first so the user can choose what feels safest to answer.")
        elif dialogue.user_style.verbosity == "brief":
            parts.append("Ask for one concrete anchor only, not a broad multi-part explanation.")
        elif dialogue.user_style.verbosity == "detailed":
            parts.append("Let the narrative breathe, then narrow gently toward impact, intensity, or change.")
        else:
            parts.append("Use a balanced guided pace with one focused follow-up.")
        if dialogue.user_style.code_mix in {"medium", "high"}:
            parts.append("Mirror code-mix lightly and naturally.")
        if dialogue.continuity_note:
            parts.append("If it fits, use a then-versus-now comparison instead of restarting the topic from scratch.")
        return " ".join(parts)

    def _build_nudge_guidance(self, dialogue) -> str:
        guidance_map = {
            "example": "Invite one recent concrete moment.",
            "timing": "Ask when it becomes strongest or most noticeable.",
            "impact": "Ask how it affects routine, sleep, work, study, appetite, or relationships.",
            "choice": "Offer a small choice such as example, timing, or daily impact and let the user pick one.",
            "scale": "If words feel hard, accept a quick intensity estimate or stronger-versus-weaker comparison.",
            "body": "Invite body sensations or physical tension if that is easier than naming the whole emotion.",
            "compare": "Ask what changed compared with before or compared with the last check-in.",
            "coping": "Ask what makes it worse, what softens it, or what the user does when it shows up.",
            "support": "Ask for one person, routine, or anchor that notices, helps, or keeps the user steadier.",
            "safety": "Keep the question brief, direct, and non-elaborate.",
            "mood": "Clarify the heaviest part of the low-mood experience.",
            "sleep": "Clarify the sleep pattern rather than asking about sleep in general.",
            "anxiety": "Clarify whether the worry feels mental, physical, or both.",
        }
        nudges = [guidance_map[key] for key in dialogue.recommended_nudges if key in guidance_map]
        return " ".join(nudges[:3]) or "Use the smallest prompt that adds real clarity."

    def _build_reply_transcript(self, turns: list[Turn]) -> str:
        window = turns[-10:] if len(turns) > 10 else turns
        return "\n".join(f"{turn.speaker}: {turn.text}" for turn in window)

    def _build_earlier_context(self, turns: list[Turn]) -> str:
        if len(turns) <= 10:
            return "No earlier context."
        older_user_turns = [turn.text.strip() for turn in turns[:-10] if turn.speaker == "user"][-3:]
        if not older_user_turns:
            return "No earlier context."
        snippets = []
        for turn in older_user_turns:
            words = turn.split()
            snippets.append(" ".join(words[:14]))
        return " | ".join(snippets)

    def _clean_content(self, content: str, fallback_text: str) -> Optional[str]:
        cleaned = content.strip().strip('"')
        if not cleaned:
            return None
        fragments = []
        for line in cleaned.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            normalized = normalize_text(stripped)
            if normalized.startswith("note:") or normalized.startswith("draft") or normalized in {"---", "***"}:
                break
            fragments.append(stripped)
        cleaned = " ".join(fragments).strip()
        cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        if not cleaned:
            return fallback_text
        if "diagnos" in cleaned.lower() or "therap" in cleaned.lower():
            return fallback_text
        return cleaned

    def _sounds_invalid_empathy(self, content: str) -> bool:
        normalized = normalize_text(content)
        banned_phrases = ("great to hear", "good to hear", "glad to hear")
        return any(phrase in normalized for phrase in banned_phrases)

    def _repeats_last_question(self, content: str, session: ChatSession) -> bool:
        assistant_turns = [turn.text for turn in session.turns if turn.speaker == "assistant"][-3:]
        if not assistant_turns:
            return False

        current_tokens = self._question_signature(content)
        current_opening = self._sentence_opening_signature(content)
        current_frames = self._question_frame_markers(content)
        for previous in assistant_turns:
            previous_tokens = self._question_signature(previous)
            if current_tokens and previous_tokens:
                overlap = len(current_tokens & previous_tokens) / max(len(current_tokens | previous_tokens), 1)
                if overlap >= 0.72:
                    return True
            previous_opening = self._sentence_opening_signature(previous)
            if current_opening and previous_opening and current_opening == previous_opening:
                return True
            previous_frames = self._question_frame_markers(previous)
            if current_frames and previous_frames and current_frames & previous_frames:
                return True
        return False

    def _looks_like_meta_or_draft(self, content: str) -> bool:
        normalized = normalize_text(content)
        meta_markers = (
            "note:",
            "this draft",
            "draft maintains",
            "the following",
            "assistant turn",
        )
        return any(marker in normalized for marker in meta_markers)

    def _should_prefer_fallback(self, session: ChatSession, snapshot: ScreeningSnapshot, target_item: Optional[str]) -> bool:
        dialogue = snapshot.coverage.dialogue
        if dialogue.stage == "summary" and dialogue.summary_ready:
            return True
        if dialogue.target_topic == "safety":
            return True
        if (
            self._provider == "local"
            and target_item
            and dialogue.stage in {"rapport", "clarification", "exploration"}
            and dialogue.target_topic != "safety"
        ):
            return True
        if self._provider == "local" and session.language in {"hi", "hinglish"}:
            return True
        if self._provider == "vertex":
            return False
        if not target_item or target_item not in ITEM_INDEX:
            return False
        last_user = next((turn.text for turn in reversed(session.turns) if turn.speaker == "user"), "")
        if not last_user:
            return False
        normalized = normalize_text(last_user)
        words = len(last_user.split())
        short_answer = words <= 7
        timing_or_frequency = any(marker in normalized for marker in TIME_MARKERS + FREQUENCY_MARKERS)
        return short_answer or timing_or_frequency

    def _question_signature(self, text: str) -> set[str]:
        if "?" not in text:
            return set()
        tokens = re.findall(r"\w+", normalize_text(text), flags=re.UNICODE)
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "it",
            "this",
            "that",
            "do",
            "does",
            "did",
            "you",
            "your",
            "when",
            "what",
            "how",
            "at",
            "in",
            "on",
            "to",
            "of",
            "and",
            "or",
            "be",
            "are",
            "feel",
            "feels",
            "felt",
        }
        return {token for token in tokens if token not in stopwords}

    def _sentence_opening_signature(self, text: str) -> tuple[str, ...]:
        normalized = normalize_text(text)
        tokens = re.findall(r"\w+", normalized, flags=re.UNICODE)
        if len(tokens) < 3:
            return tuple()
        return tuple(tokens[:4])

    def _question_frame_markers(self, text: str) -> set[str]:
        normalized = normalize_text(text)
        markers = {
            "it sounds like": "reflective_opener",
            "when this hits": "when_this_hits",
            "when the worry starts": "worry_starts",
            "more like": "more_like",
            "through the day": "through_the_day",
            "comes in waves": "comes_in_waves",
            "before you start": "before_you_start",
            "or both": "or_both",
            "hard to switch off": "hard_to_switch_off",
            "staying active even when things are quiet": "staying_active_quiet",
            "what slips first": "what_slips_first",
        }
        return {label for marker, label in markers.items() if marker in normalized}


class HuggingFaceExtractor:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._provider = self.config.extraction_model_provider
        self._remote_client = (
            _RemoteExtractorClient(self.config.remote_extraction_url, self.config.remote_extraction_timeout)
            if self._provider == "remote"
            else None
        )
        self._client = None
        if self._provider != "remote":
            self._client = _build_text_generation_client(
                self.config,
                self._provider,
                self.config.extraction_model,
                adapter_path=self.config.local_extraction_adapter,
            )

    @property
    def enabled(self) -> bool:
        if self._provider == "remote":
            return self._remote_client is not None and self._remote_client.enabled
        return self._client is not None

    def extract(self, turns: list[Turn], language: str) -> Optional[dict]:
        if not self.enabled:
            return None
        if self._provider == "remote" and self._remote_client is not None:
            return self._remote_client.extract(turns, language)

        normalized_language = language.lower()
        if self._provider == "local":
            payload = self._extract_with_local_fast_path(turns, normalized_language)
            if payload and payload.get("items"):
                return payload
            best_payload = payload
            if normalized_language in {"en", "hi", "hinglish"}:
                full_transcript = self._build_extraction_transcript(turns, include_assistant=True)
                verifier_payload = self._extract_with_window_verifier(turns, normalized_language)
                best_payload = self._merge_payloads(payload, verifier_payload) or verifier_payload or payload
                best_payload = self._build_rule_rescue_payload(turns, normalized_language, best_payload)
                if normalized_language == "en":
                    return self._refine_english_anxiety_payload(full_transcript, best_payload)
                return best_payload
            return self._build_rule_rescue_payload(turns, normalized_language, best_payload)

        if normalized_language in {"en", "hi", "hinglish"}:
            payload = self._extract_with_window_verifier(turns, normalized_language)
            if payload and payload.get("items"):
                return payload
            return self._build_rule_rescue_payload(turns, normalized_language, payload)

        transcript = self._build_extraction_transcript(turns)
        full_transcript = self._build_extraction_transcript(turns, include_assistant=True)
        item_lines = self._item_lines(include_hints=False)
        payload = self._run_attempt_sequence(normalized_language, transcript, full_transcript, item_lines)
        if payload and payload.get("items"):
            return payload
        return self._build_rule_rescue_payload(turns, normalized_language, payload)

    def _extract_with_local_fast_path(self, turns: list[Turn], language: str) -> Optional[dict]:
        transcripts = self._build_local_fast_transcripts(turns)
        best_payload = None
        for index, transcript in enumerate(transcripts):
            try:
                output = self._client.chat_completion(
                    messages=self._build_compact_extraction_messages(language, transcript, max_items=4),
                    temperature=0.0,
                    max_tokens=64 if index == 0 else 80,
                )
            except Exception:
                continue
            payload = self._parse_json(output.choices[0].message.content)
            payload = self._apply_local_refinements(language, transcript, payload)
            if payload and payload.get("items"):
                return payload
            if payload is not None:
                best_payload = payload

        if transcripts:
            best_payload = self._apply_local_refinements(language, transcripts[-1], best_payload)
        return best_payload

    def _extract_with_window_verifier(self, turns: list[Turn], language: str) -> Optional[dict]:
        item_lines = self._item_lines(include_hints=False)
        merged_payload = None
        for transcript in self._build_window_transcripts(turns):
            payload = self._run_attempt_sequence(
                language,
                transcript,
                transcript,
                item_lines,
                prefer_compact=True,
            )
            merged_payload = self._merge_payloads(merged_payload, payload)

        full_transcript = self._build_extraction_transcript(turns, include_assistant=True)
        verifier_payload = self._run_final_pass(language, full_transcript, item_lines, merged_payload)
        merged_payload = self._merge_payloads(merged_payload, verifier_payload)
        if language == "en":
            english_verifier_payload = self._run_english_verifier(full_transcript, item_lines, merged_payload)
            merged_payload = self._merge_payloads(merged_payload, english_verifier_payload)

        fallback_payload = self._run_attempt_sequence(
            language,
            self._build_extraction_transcript(turns),
            full_transcript,
            item_lines,
            prefer_compact=True,
        )
        merged_payload = self._merge_payloads(merged_payload, fallback_payload)
        if language == "en":
            return self._refine_english_anxiety_payload(full_transcript, merged_payload or fallback_payload)
        return merged_payload or fallback_payload
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
        if self._provider == "local":
            return [
                (
                    self._build_compact_extraction_messages(language, primary_transcript),
                    min(self.config.extraction_max_tokens, 96),
                ),
                (
                    self._build_compact_extraction_messages(language, fallback_transcript),
                    min(self.config.extraction_max_tokens, 128),
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
        if self._provider == "local":
            selected_turns = turns[-10:] if include_assistant else [turn for turn in turns if turn.speaker == "user"][-6:]
        else:
            selected_turns = turns[-12:] if include_assistant else [turn for turn in turns if turn.speaker == "user"][-6:]
        return "\n".join(f"{turn.speaker}: {turn.text}" for turn in selected_turns)

    def _build_local_fast_transcripts(self, turns: list[Turn]) -> list[str]:
        transcripts: list[str] = []
        primary_turns = [turn for turn in turns if turn.speaker == "user"][-4:]
        primary = "\n".join(f"{turn.speaker}: {turn.text}" for turn in primary_turns if turn.text.strip())
        if primary:
            transcripts.append(primary)

        fallback_turns = turns[-6:]
        fallback = "\n".join(f"{turn.speaker}: {turn.text}" for turn in fallback_turns if turn.text.strip())
        if fallback and fallback not in transcripts:
            transcripts.append(fallback)
        return transcripts

    def _build_window_transcripts(self, turns: list[Turn]) -> list[str]:
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

    def _build_english_window_transcripts(self, turns: list[Turn]) -> list[str]:
        return self._build_window_transcripts(turns)

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

    def _build_rule_rescue_payload(
        self,
        turns: list[Turn],
        language: str,
        prior_payload: Optional[dict],
    ) -> Optional[dict]:
        snapshot = ConversationScorer().analyze(turns, language, SafetyFlag(level="none"))
        if not snapshot.evidence_spans:
            return prior_payload

        span_index = {span.span_id: span for span in snapshot.evidence_spans}
        rescued_items = []
        for item_id, item in snapshot.items.items():
            if item.value is None or item.status not in {"resolved", "partial"}:
                continue
            quote = ""
            for span_id in item.evidence_span_ids:
                span = span_index.get(span_id)
                if span is not None:
                    quote = span.text_span
                    break
            rescued_items.append(
                {
                    "item_id": item_id,
                    "value": item.value,
                    "evidence_quote": quote,
                    "confidence_note": "Rule-grounded rescue fallback after non-parseable extractor output.",
                }
            )

        if not rescued_items:
            return prior_payload

        merged_items: dict[str, dict[str, Any]] = {}
        for item in (prior_payload or {}).get("items", []):
            item_id = item.get("item_id")
            if item_id:
                merged_items[item_id] = dict(item)
        for item in rescued_items:
            current = merged_items.get(item["item_id"])
            if current is None or self._prefer_item(item, current):
                merged_items[item["item_id"]] = dict(item)

        payload = normalize_extractor_payload(
            {
                "items": list(merged_items.values()),
                "safety_level": prior_payload.get("safety_level", "none") if prior_payload else "none",
                "safety_cues": prior_payload.get("safety_cues", []) if prior_payload else [],
                "notes": " | ".join(
                    part for part in [
                        prior_payload.get("notes", "").strip() if prior_payload else "",
                        "rule_rescue_fallback",
                    ] if part
                ),
            }
        )
        return payload or prior_payload

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

    def _build_compact_extraction_messages(
        self,
        language: str,
        transcript: str,
        *,
        max_items: int = 6,
    ) -> list[dict[str, str]]:
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
                    f"Include at most {max_items} strongest items. "
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

    def _apply_local_refinements(self, language: str, transcript: str, payload: Optional[dict]) -> Optional[dict]:
        base_payload = payload or {
            "items": [],
            "safety_level": "none",
            "safety_cues": [],
            "notes": "local_fast",
        }
        if language in {"en", "hinglish"}:
            refined = self._refine_english_anxiety_payload(transcript, base_payload)
            return refined or base_payload
        return base_payload

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


class _RemoteExtractorClient:
    def __init__(self, base_url: Optional[str], timeout: float) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._base_url)

    def extract(self, turns: list[Turn], language: str) -> Optional[dict]:
        if not self.enabled:
            return None
        payload = json.dumps(
            {
                "language": language,
                "turns": [turn.model_dump(mode="json") for turn in turns],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib_request.Request(
            f"{self._base_url}/screen/transcript/llm",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            return None
        return body.get("result")


class HuggingFaceSafetyAssessor:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._provider = self.config.safety_model_provider
        self._client = (
            _build_text_generation_client(
                self.config,
                self._provider,
                self.config.safety_model,
                adapter_path=self.config.local_safety_adapter,
            )
            if self.config.safety_model
            else None
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
