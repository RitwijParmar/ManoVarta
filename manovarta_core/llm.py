from __future__ import annotations

import json
import logging
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
from manovarta_core.safety import PROTECTIVE_CUES, PROTECTIVE_NEGATION_PATTERNS
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
    from google import auth as google_auth
    from google.auth.transport.requests import Request as GoogleAuthRequest
except ImportError:  # pragma: no cover
    google_auth = None
    GoogleAuthRequest = None

AutoModelForCausalLM = None
AutoTokenizer = None
BitsAndBytesConfig = None
PeftModel = None
torch = None


logger = logging.getLogger(__name__)


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
    "phq_q1_anhedonia",
    "phq_q2_low_mood",
    "phq_q5_appetite",
    "phq_q6_worthlessness",
    "gad_q1_nervous",
    "gad_q2_control_worry",
    "gad_q3_excessive_worry",
    "gad_q4_trouble_relaxing",
    "gad_q5_restlessness",
    "gad_q6_irritability",
    "gad_q7_afraid",
    "phq_q3_sleep",
    "phq_q9_self_harm",
)
ENGLISH_ANHEDONIA_CUES = (
    "go through the motions",
    "go through motions",
    "do not get much from them",
    "don't get much from them",
    "feel very little from them",
    "things i used to enjoy feel flat",
    "things i usually care about feel flat",
    "before i even start them",
    "used to enjoy",
    "used to enjoy feel flat",
    "keep delaying starting things",
    "put off starting things",
    "pulling away from people",
    "ignore texts",
)
ENGLISH_LOW_MOOD_CUES = (
    "low mood",
    "feel flat most of the day",
    "emotionally flat underneath",
    "everything feels flat underneath",
    "days feel heavy",
    "day feels heavy",
    "my mood stays heavy",
    "mood stays heavy most of the day",
    "heavy most of the day",
    "heavy and blank",
    "flat and heavy",
    "empty most days",
    "drop in my stomach",
    "dimmer and heavier than it used to",
    "heavy muted feeling",
    "muted feeling that sits underneath everything",
    "heavier than it used to",
)
ENGLISH_SLEEP_CUES = (
    "sleep is messy",
    "wake up around 3 a.m.",
    "wake up around 3 am",
    "wake around 3 or 4",
    "drift in and out until morning",
    "sleep problem is happening",
    "waking during the night",
    "wake too early",
    "sleep keeps breaking",
)
ENGLISH_APPETITE_CUES = (
    "skip lunch",
    "skipped lunch",
    "still have not eaten properly",
    "late afternoon before eating",
    "skip meals",
    "skipping meals",
    "lunch gets skipped",
    "whatever is quickest",
    "meals get skipped",
    "meals get delayed",
    "appetite is off",
    "not eating much",
    "appetite does not really show up",
    "appetite does not show up",
)
ENGLISH_WORTHLESSNESS_CUES = (
    "wasting everyone's time",
    "waste everyone's time",
    "better off without me",
    "letting people down",
    "hard on myself",
    "harsh on myself",
    "judging myself",
    "blame myself",
    "feel like i am failing",
    "feeling like i am failing",
    "failing at things that should be easy",
    "tiny tasks feel bigger than they should",
    "not cut out for this",
    "feeling weak",
    "like a burden",
)
ENGLISH_CONTROL_WORRY_CUES = (
    "mind won't stop",
    "thoughts won't stop",
    "mind keeps looping",
    "thoughts keep looping",
    "even when i try to stop it",
    "try to stop it",
    "can't stop worrying",
    "cannot stop worrying",
    "worrying a lot",
    "replay whole conversations",
    "replaying comments from my advisor",
    "brain keeps replaying",
    "head keeps saying",
    "hard to shut it off",
    "cannot really turn it off",
    "cannot turn it off",
    "turn it off on my own",
    "no real control over it",
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
    "work or money",
    "let people down",
    "miss something important",
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
    "relaxing has been hard",
    "do not feel settled",
    "body still feels revved up",
    "actually unwinding",
)
ENGLISH_NERVOUS_CUES = (
    "always on edge",
    "on edge",
    "on edge before calls",
    "feel anxious",
    "feeling anxious",
    "feel on edge",
    "constantly nervous",
    "jaw stays tight",
    "chest tight",
    "hands start shaking",
    "keyed up",
    "before difficult calls",
)
ENGLISH_RESTLESSNESS_CUES = (
    "pace around",
    "pacing around",
    "can't sit still",
    "cannot sit still",
    "do not sit still",
    "need to move around",
    "urge to move around",
    "keep getting up",
)
ENGLISH_CONCENTRATION_CUES = (
    "reread the same email",
    "reread the same paragraph",
    "rereading things",
    "lose my thread",
    "concentration slips",
    "focus slips",
    "mind not sticking",
)
ENGLISH_PSYCHOMOTOR_CUES = (
    "body feels slowed down",
    "move more slowly",
    "move slower than usual",
    "slowed down feeling",
    "takes effort to get myself started",
    "takes real effort just to get started",
    "delay basic tasks",
)
ENGLISH_AFRAID_CUES = (
    "something bad will happen",
    "something bad is about to happen",
    "cover rent",
    "get written up",
    "say the wrong thing",
    "catastrophe",
    "awful will happen",
    "something is about to go wrong",
    "miss something important",
)
ENGLISH_SELF_HARM_POSITIVE_CUES = (
    "hurt myself",
    "harm myself",
    "kill myself",
    "end my life",
    "want to die",
    "not wanting to be alive",
    "better off without me around",
    "everyone would have an easier life",
    "want to disappear",
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

    def warmup(self) -> bool:
        self._ensure_backend()
        return self._tokenizer is not None and self._model is not None

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
        if google_auth is None or GoogleAuthRequest is None:
            raise RuntimeError("google auth runtime is not installed")
        if not config.vertex_project:
            raise RuntimeError("vertex project is not configured")
        self._config = config
        self._model_name = model_name
        self._lock = Lock()
        self._credentials = None

    def chat_completion(self, *, messages, temperature: float, max_tokens: int):
        system_instruction, prompt, wants_json = self._prepare_request(messages)
        if not prompt:
            return _ChatCompletionOutput("")

        payload = self._build_request_payload(
            system_instruction=system_instruction,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            wants_json=wants_json,
        )
        response = self._post_json(self._endpoint_url(), payload)
        content = self._extract_response_text(response)
        return _ChatCompletionOutput(content.strip())

    def warmup(self) -> bool:
        if self._credentials_or_refresh() is None:
            return False
        response = self._post_json(self._endpoint_url(), self._build_warmup_payload())
        self._extract_response_text(response)
        return True

    def _prepare_request(self, messages) -> tuple[str, str, bool]:
        wants_json = self._wants_json_response(messages)
        system_instruction = "\n\n".join(
            str(message.get("content", "")).strip()
            for message in messages
            if message.get("role") == "system" and message.get("content")
        ).strip()
        prompt = "\n\n".join(
            f"{str(message.get('role', 'user')).upper()}:\n{str(message.get('content', '')).strip()}"
            for message in messages
            if message.get("content") and message.get("role") != "system"
        ).strip()
        return system_instruction, prompt, wants_json

    def _wants_json_response(self, messages) -> bool:
        normalized_content = " ".join(
            str(message.get("content", "")).strip().lower()
            for message in messages
            if message.get("content")
        )
        return (
            "json" in normalized_content
            and (
                "return" in normalized_content
                or "schema" in normalized_content
                or "valid json" in normalized_content
            )
        )

    def _endpoint_url(self) -> str:
        location = (self._config.vertex_location or "us-central1").strip()
        if location == "global":
            base_url = "https://aiplatform.googleapis.com"
        else:
            base_url = f"https://{location}-aiplatform.googleapis.com"
        return (
            f"{base_url}/v1/projects/{self._config.vertex_project}/locations/{location}"
            f"/publishers/google/models/{self._model_name}:generateContent"
        )

    def _build_request_payload(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        wants_json: bool,
    ) -> dict[str, Any]:
        effective_max_tokens = max_tokens
        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json" if wants_json else "text/plain",
        }
        thinking_config = self._thinking_config(wants_json=wants_json)
        if thinking_config:
            generation_config["thinkingConfig"] = thinking_config
            if thinking_config.get("thinkingBudget", 0) > 0:
                effective_max_tokens = max(max_tokens, 384)
                generation_config["maxOutputTokens"] = effective_max_tokens
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        return payload

    def _build_warmup_payload(self) -> dict[str, Any]:
        generation_config: dict[str, Any] = {
            "temperature": 0.0,
            "maxOutputTokens": 8,
            "responseMimeType": "text/plain",
        }
        return {
            "contents": [{"role": "user", "parts": [{"text": "Reply with ok."}]}],
            "generationConfig": generation_config,
        }

    def _thinking_config(self, *, wants_json: bool) -> Optional[dict[str, int]]:
        if wants_json:
            return None
        normalized_model = self._model_name.strip().lower()
        if normalized_model.startswith("gemini-2.5-pro"):
            return {"thinkingBudget": 128}
        if normalized_model.startswith("gemini-2.5-flash"):
            return {"thinkingBudget": 0}
        return None

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        credentials = self._credentials_or_refresh()
        request = urllib_request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode())
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"{exc.code} {exc.reason}: {detail}") from exc

    def _credentials_or_refresh(self):
        with self._lock:
            if self._credentials is None:
                credentials, _ = google_auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                self._credentials = credentials
            if not getattr(self._credentials, "valid", False) or getattr(self._credentials, "expired", False):
                self._credentials.refresh(GoogleAuthRequest())
            return self._credentials

    def _extract_response_text(self, response) -> str:
        parts: list[str] = []
        if isinstance(response, dict):
            for candidate in response.get("candidates", []) or []:
                for part in ((candidate.get("content") or {}).get("parts") or []):
                    part_text = part.get("text")
                    if part_text:
                        parts.append(str(part_text))
        else:
            for candidate in getattr(response, "candidates", None) or []:
                candidate_parts = getattr(getattr(candidate, "content", None), "parts", None) or []
                for part in candidate_parts:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        parts.append(str(part_text))
        if parts:
            return "".join(parts).strip()
        if isinstance(response, dict):
            return str(response.get("text", "") or "").strip()
        return str(getattr(response, "text", "") or "").strip()


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
        self._last_reply_diagnostics: dict[str, str] = {}
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

    def warmup(self) -> bool:
        warmed = False
        seen_clients: set[tuple[str, str, str]] = set()
        for client in [*self._active_generation_clients(), *self._active_analysis_clients()]:
            warmup_key = self._warmup_key(client)
            if warmup_key in seen_clients:
                continue
            seen_clients.add(warmup_key)
            warmup = getattr(client, "warmup", None)
            if warmup is None:
                continue
            warmed = bool(warmup()) or warmed
        return warmed

    def compose_reply(
        self,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        target_item: Optional[str],
        fallback_text: str,
    ) -> Tuple[str, str]:
        self._last_reply_diagnostics = {"source": "template", "reason": "not_attempted", "detail": ""}
        if not self.enabled or snapshot.safety.level == "urgent":
            self._last_reply_diagnostics = {"source": "template", "reason": "responder_disabled_or_urgent", "detail": ""}
            return fallback_text, "template"
        if snapshot.safety.level == "review" and snapshot.coverage.dialogue.target_topic == "safety":
            self._last_reply_diagnostics = {"source": "template", "reason": "safety_review", "detail": ""}
            return fallback_text, "template"
        if self._should_prefer_fallback(session, snapshot, target_item):
            self._last_reply_diagnostics = {"source": "template", "reason": "planner_prefers_fallback", "detail": ""}
            return fallback_text, "template"

        analyzer_result = self._analyze_turn(session, snapshot, target_item)
        messages = self._build_messages(session, snapshot, target_item, fallback_text, analyzer_result=analyzer_result)
        last_failure_reason = "no_generation_attempt"
        last_failure_detail = ""
        for client in self._active_generation_clients():
            client_label = self._client_label(client)
            repair_context: tuple[str, str] | None = None
            for attempt_index in range(2):
                prompt_messages = messages
                if repair_context is not None:
                    prompt_messages = self._build_repair_messages(
                        messages,
                        session,
                        repair_context[0],
                        repair_context[1],
                    )
                try:
                    output = client.chat_completion(
                        messages=prompt_messages,
                        temperature=self.config.assistant_temperature,
                        max_tokens=self.config.assistant_max_tokens,
                    )
                    content = output.choices[0].message.content.strip()
                except Exception as exc:
                    last_failure_reason = "generation_error"
                    last_failure_detail = f"{client_label}:{type(exc).__name__}:{str(exc)[:180]}"
                    logger.warning(
                        "reply_generation_error provider=%s client=%s attempt=%s target_item=%s error=%s",
                        self._provider,
                        client_label,
                        attempt_index + 1,
                        target_item or "none",
                        exc,
                    )
                    break

                cleaned = self._clean_content(content, fallback_text)
                if not cleaned:
                    last_failure_reason = "empty_or_invalid"
                    last_failure_detail = f"{client_label}:{content[:180]}"
                    repair_context = ("empty_or_invalid", content[:240])
                    continue
                rejection_reason = self._reply_rejection_reason(cleaned, session, snapshot, analyzer_result)
                if rejection_reason is None:
                    self._last_reply_diagnostics = {
                        "source": self._provider,
                        "reason": "accepted",
                        "detail": f"{client_label}:attempt_{attempt_index + 1}",
                    }
                    return cleaned, self._provider
                last_failure_reason = rejection_reason
                last_failure_detail = f"{client_label}:{cleaned[:180]}"
                logger.info(
                    "reply_generation_rejected provider=%s client=%s attempt=%s target_item=%s reason=%s draft=%r",
                    self._provider,
                    client_label,
                    attempt_index + 1,
                    target_item or "none",
                    rejection_reason,
                    cleaned[:240],
                )
                if attempt_index == 0:
                    repair_context = (rejection_reason, cleaned[:240])
                    continue
                break
        logger.info(
            "reply_generation_fallback provider=%s target_item=%s reason=%s detail=%r",
            self._provider,
            target_item or "none",
            last_failure_reason,
            last_failure_detail,
        )
        self._last_reply_diagnostics = {
            "source": "template",
            "reason": last_failure_reason,
            "detail": last_failure_detail,
        }
        return fallback_text, "template"

    @property
    def last_reply_diagnostics(self) -> dict[str, str]:
        return dict(self._last_reply_diagnostics)

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

    def _client_label(self, client: Any) -> str:
        model_name = getattr(client, "_model_name", None)
        if model_name:
            return str(model_name)
        return type(client).__name__

    def _warmup_key(self, client: Any) -> tuple[str, str, str]:
        model_name = str(getattr(client, "_model_name", "") or "")
        client_config = getattr(client, "_config", None)
        location = str(getattr(client_config, "vertex_location", "") or "")
        return (type(client).__name__, model_name, location)

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

    def _build_repair_messages(
        self,
        original_messages: list[dict[str, str]],
        session: ChatSession,
        rejection_reason: str,
        rejected_draft: str,
    ) -> list[dict[str, str]]:
        recent_turns = " | ".join(
            turn.text.strip()
            for turn in [turn for turn in session.turns if turn.speaker == "assistant"][-3:]
            if turn.text.strip()
        ) or "none"
        repair_instruction = (
            "Rewrite the assistant turn. "
            f"The previous draft was rejected for: {rejection_reason}. "
            "Keep the same topic target, but switch to a different sentence family from the recent assistant turns. "
            "Do not reuse the same opener, reflection frame, or question shape. "
            "Use at most two sentences, stay in the user's language, and return only the rewritten turn.\n"
            f"Rejected draft: {rejected_draft}\n"
            f"Recent assistant turns to avoid echoing: {recent_turns}"
        )
        return [*original_messages, {"role": "user", "content": repair_instruction}]

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

    def _reply_rejection_reason(
        self,
        cleaned: str,
        session: ChatSession,
        snapshot: ScreeningSnapshot,
        analyzer_result: Optional[DialogueAnalyzerResult],
    ) -> Optional[str]:
        if self._sounds_invalid_empathy(cleaned):
            return "invalid_empathy"
        if self._repeats_last_question(cleaned, session):
            return "duplicate_question"
        if self._repeats_recent_reply_family(cleaned, session):
            return "repetitive_full_reply"
        if self._looks_like_meta_or_draft(cleaned):
            return "meta_or_draft"
        if self._contradicts_recent_channel(cleaned, session):
            return "contradicts_recent_channel"
        if self._summary_stage_sounds_empty(cleaned, snapshot):
            return "empty_summary"
        if self._violates_analysis_constraints(cleaned, analyzer_result):
            return "analysis_constraint_violation"
        return None

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

    def _repeats_recent_reply_family(self, content: str, session: ChatSession) -> bool:
        assistant_turns = [turn.text for turn in session.turns if turn.speaker == "assistant"][-3:]
        if not assistant_turns:
            return False

        current_sentences = self._normalized_sentences(content)
        if not current_sentences:
            return False
        current_families = self._reply_family_markers(content)
        current_opening = self._sentence_opening_signature(content)
        current_reply_signature = self._reply_signature(content)

        for previous in assistant_turns:
            previous_sentences = self._normalized_sentences(previous)
            previous_families = self._reply_family_markers(previous)
            previous_opening = self._sentence_opening_signature(previous)
            previous_reply_signature = self._reply_signature(previous)
            if current_opening and previous_opening and current_opening == previous_opening:
                return True
            if current_families and previous_families and current_families & previous_families:
                return True
            if current_reply_signature and previous_reply_signature:
                overlap = len(current_reply_signature & previous_reply_signature) / max(
                    len(current_reply_signature | previous_reply_signature),
                    1,
                )
                if overlap >= 0.78:
                    return True
            for current_sentence in current_sentences:
                for previous_sentence in previous_sentences:
                    if current_sentence == previous_sentence:
                        return True
                    sentence_overlap = len(current_sentence & previous_sentence) / max(
                        len(current_sentence | previous_sentence),
                        1,
                    )
                    if sentence_overlap >= 0.74:
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

    def _reply_signature(self, text: str) -> set[str]:
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
            "to",
            "of",
            "and",
            "or",
            "be",
            "are",
            "if",
            "when",
            "what",
            "how",
            "more",
            "like",
            "then",
        }
        return {token for token in tokens if token not in stopwords and len(token) > 2}

    def _normalized_sentences(self, text: str) -> list[set[str]]:
        normalized = normalize_text(text)
        sentences = [segment.strip() for segment in re.split(r"[?.!]+", normalized) if segment.strip()]
        token_sets: list[set[str]] = []
        for sentence in sentences:
            tokens = {
                token
                for token in re.findall(r"\w+", sentence, flags=re.UNICODE)
                if len(token) > 2 and token not in {"the", "and", "that", "this", "with", "from", "your"}
            }
            if tokens:
                token_sets.append(tokens)
        return token_sets

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

    def _reply_family_markers(self, text: str) -> set[str]:
        normalized = normalize_text(text)
        markers = {
            "it sounds like": "reflective_opener",
            "that timing helps": "timing_anchor",
            "that helps me understand how often": "frequency_anchor",
            "when this hits": "when_this_hits",
            "when the worry starts": "worry_starts",
            "what slips first": "what_slips_first",
            "or both": "or_both",
            "lag raha hai": "lag_raha_hai",
            "jab yeh hota hai": "jab_yeh_hota_hai",
            "jab din heavy ho jata hai": "din_heavy",
            "mind or body": "mind_or_body",
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

    def warmup(self) -> bool:
        if not self.enabled or self._provider == "remote":
            return False
        warmup = getattr(self._client, "warmup", None)
        if warmup is None:
            return False
        return bool(warmup())

    def extract(self, turns: list[Turn], language: str) -> Optional[dict]:
        if not self.enabled:
            return None
        normalized_language = language.lower()
        if self._provider == "remote" and self._remote_client is not None:
            payload = self._remote_client.extract(turns, language)
            if payload is None:
                return None
            if self.config.remote_extraction_hybrid_enabled:
                return self._postprocess_extraction_payload(turns, normalized_language, payload)
            return payload

        if self._provider == "local":
            payload = self._extract_with_local_fast_path(turns, normalized_language)
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

    def _postprocess_extraction_payload(
        self,
        turns: list[Turn],
        language: str,
        payload: Optional[dict],
    ) -> Optional[dict]:
        if not payload:
            return payload
        merged_payload = normalize_extractor_payload(payload) or payload
        merged_payload = self._build_rule_rescue_payload(turns, language, merged_payload) or merged_payload
        if language == "en":
            transcript = self._build_extraction_transcript(turns, include_assistant=True)
            refined_payload = self._refine_english_anxiety_payload(transcript, merged_payload)
            if refined_payload:
                return refined_payload
        return merged_payload

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

        anhedonia_hit = self._find_first_cue(transcript, ENGLISH_ANHEDONIA_CUES)
        low_mood_hit = self._find_first_cue(transcript, ENGLISH_LOW_MOOD_CUES)
        sleep_hit = self._find_first_cue(transcript, ENGLISH_SLEEP_CUES)
        appetite_hit = self._find_first_cue(transcript, ENGLISH_APPETITE_CUES)
        worthlessness_hit = self._find_first_cue(transcript, ENGLISH_WORTHLESSNESS_CUES)
        concentration_hit = self._find_first_cue(transcript, ENGLISH_CONCENTRATION_CUES)
        psychomotor_hit = self._find_first_cue(transcript, ENGLISH_PSYCHOMOTOR_CUES)
        nervous_hit = self._find_first_cue(transcript, ENGLISH_NERVOUS_CUES)
        control_hit = self._find_first_cue(transcript, ENGLISH_CONTROL_WORRY_CUES)
        excessive_hit = self._find_first_cue(transcript, ENGLISH_EXCESSIVE_WORRY_CUES)
        relaxing_hit = self._find_first_cue(transcript, ENGLISH_TROUBLE_RELAXING_CUES)
        restlessness_hit = self._find_first_cue(transcript, ENGLISH_RESTLESSNESS_CUES)
        afraid_hit = self._find_first_cue(transcript, ENGLISH_AFRAID_CUES)
        self_harm_denial_hit = self._find_first_pattern_match(transcript, PROTECTIVE_NEGATION_PATTERNS)
        if self_harm_denial_hit is None:
            self_harm_denial_hit = self._find_first_cue(transcript, PROTECTIVE_CUES)
        if self_harm_denial_hit is None:
            self_harm_denial_hit = self._find_first_pattern_match(
                transcript,
                (
                    r"\b(?:no|not|never|have\s+not|haven't|had\s+not)\b.{0,48}\bbetter off dead\b",
                    r"\b(?:no|not|never|have\s+not|haven't)\b.{0,48}\bwishing i was dead\b",
                ),
            )

        if anhedonia_hit:
            items["phq_q1_anhedonia"] = self._prefer_structured_item(
                items.get("phq_q1_anhedonia"),
                {
                    "item_id": "phq_q1_anhedonia",
                    "value": 2,
                    "evidence_quote": extract_window(transcript, anhedonia_hit),
                    "confidence_note": "Reduced interest or emotional flatness around usually meaningful activities.",
                },
            )

        if low_mood_hit:
            items["phq_q2_low_mood"] = self._prefer_structured_item(
                items.get("phq_q2_low_mood"),
                {
                    "item_id": "phq_q2_low_mood",
                    "value": self._english_support_value(transcript, low_mood_hit),
                    "evidence_quote": extract_window(transcript, low_mood_hit, radius=72),
                    "confidence_note": "Persistent heaviness, emptiness, or low mood language across the day.",
                },
            )

        if sleep_hit:
            items["phq_q3_sleep"] = self._prefer_structured_item(
                items.get("phq_q3_sleep"),
                {
                    "item_id": "phq_q3_sleep",
                    "value": self._english_support_value(transcript, sleep_hit),
                    "evidence_quote": extract_window(transcript, sleep_hit, radius=72),
                    "confidence_note": "Broken, early, or repeatedly interrupted sleep is clearly described.",
                },
            )

        if appetite_hit:
            items["phq_q5_appetite"] = self._prefer_structured_item(
                items.get("phq_q5_appetite"),
                {
                    "item_id": "phq_q5_appetite",
                    "value": self._english_support_value(transcript, appetite_hit),
                    "evidence_quote": extract_window(transcript, appetite_hit, radius=72),
                    "confidence_note": "Meals are skipped, delayed, or appetite is clearly off.",
                },
            )

        if worthlessness_hit:
            items["phq_q6_worthlessness"] = self._prefer_structured_item(
                items.get("phq_q6_worthlessness"),
                {
                    "item_id": "phq_q6_worthlessness",
                    "value": 2,
                    "evidence_quote": extract_window(transcript, worthlessness_hit),
                    "confidence_note": "Self-blame, burden language, or harsh self-judgment is present.",
                },
            )

        if concentration_hit:
            items["phq_q7_concentration"] = self._prefer_structured_item(
                items.get("phq_q7_concentration"),
                {
                    "item_id": "phq_q7_concentration",
                    "value": self._english_support_value(transcript, concentration_hit),
                    "evidence_quote": extract_window(transcript, concentration_hit, radius=72),
                    "confidence_note": "Concentration slips, rereading, or losing the thread is explicit.",
                },
            )

        if psychomotor_hit:
            items["phq_q8_psychomotor"] = self._prefer_structured_item(
                items.get("phq_q8_psychomotor"),
                {
                    "item_id": "phq_q8_psychomotor",
                    "value": self._english_support_value(transcript, psychomotor_hit),
                    "evidence_quote": extract_window(transcript, psychomotor_hit, radius=72),
                    "confidence_note": "Slowed movement or activation difficulty is clearly described.",
                },
            )

        if nervous_hit:
            items["gad_q1_nervous"] = self._prefer_structured_item(
                items.get("gad_q1_nervous"),
                {
                    "item_id": "gad_q1_nervous",
                    "value": self._english_support_value(transcript, nervous_hit),
                    "evidence_quote": extract_window(transcript, nervous_hit, radius=72),
                    "confidence_note": "On-edge or physical anxiety language is explicitly present.",
                },
            )

        if control_hit:
            item = items.get("gad_q2_control_worry")
            value = self._english_control_worry_value(transcript, control_hit)
            if item is None or int(item.get("value", 0)) < value:
                items["gad_q2_control_worry"] = {
                    "item_id": "gad_q2_control_worry",
                    "value": value,
                    "evidence_quote": extract_window(transcript, control_hit, radius=72),
                    "confidence_note": "Persistent looping or uncontrollable worry language.",
                }
            elif int(item.get("value", 0)) > value:
                item["value"] = value

        if excessive_hit:
            items["gad_q3_excessive_worry"] = self._prefer_structured_item(
                items.get("gad_q3_excessive_worry"),
                {
                    "item_id": "gad_q3_excessive_worry",
                    "value": self._english_support_value(transcript, excessive_hit),
                    "evidence_quote": extract_window(transcript, excessive_hit, radius=72),
                    "confidence_note": "Concrete worry about outcomes across work, family, or finances.",
                },
            )

        if relaxing_hit:
            items["gad_q4_trouble_relaxing"] = self._prefer_structured_item(
                items.get("gad_q4_trouble_relaxing"),
                {
                    "item_id": "gad_q4_trouble_relaxing",
                    "value": self._english_support_value(transcript, relaxing_hit),
                    "evidence_quote": extract_window(transcript, relaxing_hit, radius=72),
                    "confidence_note": "Difficulty settling or switching off after stress.",
                },
            )

        if restlessness_hit:
            items["gad_q5_restlessness"] = self._prefer_structured_item(
                items.get("gad_q5_restlessness"),
                {
                    "item_id": "gad_q5_restlessness",
                    "value": self._english_support_value(transcript, restlessness_hit),
                    "evidence_quote": extract_window(transcript, restlessness_hit, radius=72),
                    "confidence_note": "Restlessness or urge to keep moving is clearly described.",
                },
            )

        if afraid_hit:
            items["gad_q7_afraid"] = self._prefer_structured_item(
                items.get("gad_q7_afraid"),
                {
                    "item_id": "gad_q7_afraid",
                    "value": self._english_support_value(transcript, afraid_hit),
                    "evidence_quote": extract_window(transcript, afraid_hit, radius=72),
                    "confidence_note": "Fear of consequences or something awful happening is explicit.",
                },
            )

        if self_harm_denial_hit and not self._has_positive_self_harm_signal(transcript):
            items["phq_q9_self_harm"] = {
                "item_id": "phq_q9_self_harm",
                "value": 0,
                "evidence_quote": extract_window(transcript, self_harm_denial_hit),
                "confidence_note": "Explicit denial of self-harm or suicidal intent.",
            }

        refined = normalize_extractor_payload(
            {
                "items": list(items.values()),
                "safety_level": payload.get("safety_level", "none"),
                "safety_cues": payload.get("safety_cues", []),
                "notes": " | ".join(
                    part
                    for part in [payload.get("notes", "").strip(), "english_screening_refined"]
                    if part
                ),
            }
        )
        return refined or payload

    def _english_support_value(self, transcript: str, cue: str, *, default: int = 2) -> int:
        snippet = normalize_text(extract_window(transcript, cue, radius=96))
        if any(
            phrase in snippet
            for phrase in (
                "every day",
                "daily",
                "almost every day",
                "most days",
                "more days than not",
                "five days a week",
                "five nights a week",
                "most workdays",
                "most evenings",
                "hard to shut it off",
                "cannot really turn it off",
                "cannot turn it off",
            )
        ):
            return 3
        if any(
            phrase in snippet
            for phrase in (
                "some days",
                "several days",
                "often",
                "usually",
                "nights a week",
                "days a week",
                "most of the day",
                "throughout the day",
            )
        ):
            return max(default, 2)
        if any(
            phrase in snippet
            for phrase in (
                "sometimes",
                "occasionally",
                "briefly",
                "once or twice",
            )
        ):
            return 1
        return default

    def _english_control_worry_value(self, transcript: str, cue: str) -> int:
        snippet = normalize_text(extract_window(transcript, cue, radius=96))
        severe_control_hit = any(
            phrase in snippet
            for phrase in (
                "mind won t stop",
                "thoughts won t stop",
                "can t stop worrying",
                "cannot stop worrying",
                "hard to shut it off",
                "cannot really turn it off",
                "cannot turn it off",
                "turn it off on my own",
                "even when i try to stop it",
            )
        )
        if severe_control_hit:
            if any(
                phrase in snippet
                for phrase in (
                    "every day",
                    "daily",
                    "almost every day",
                    "most days",
                    "more days than not",
                    "five days a week",
                    "usually",
                    "often",
                )
            ):
                return 3
            return 2
        if any(
            phrase in snippet
            for phrase in (
                "mind keeps looping",
                "thoughts keep looping",
                "replay whole conversations",
                "brain keeps replaying",
                "head keeps saying",
                "worrying a lot",
            )
        ):
            return 2
        return self._english_support_value(transcript, cue, default=2)

    def _find_first_cue(self, transcript: str, cues: tuple[str, ...]) -> Optional[str]:
        normalized = normalize_text(transcript)
        for cue in cues:
            if normalize_text(cue) in normalized:
                return cue
        return None

    def _find_first_pattern_match(self, transcript: str, patterns: tuple[str, ...]) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, transcript, flags=re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _has_positive_self_harm_signal(self, transcript: str) -> bool:
        normalized_transcript = normalize_text(transcript)
        scrubbed_transcript = transcript
        for pattern in PROTECTIVE_NEGATION_PATTERNS:
            scrubbed_transcript = re.sub(pattern, " ", scrubbed_transcript, flags=re.IGNORECASE)
        scrubbed_normalized = normalize_text(scrubbed_transcript)
        for cue in PROTECTIVE_CUES:
            scrubbed_normalized = scrubbed_normalized.replace(normalize_text(cue), " ")
        return any(normalize_text(cue) in scrubbed_normalized for cue in ENGLISH_SELF_HARM_POSITIVE_CUES if normalize_text(cue) in normalized_transcript)

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
                    "- 0 = explicit, direct denial or absence, mainly for clear safety denials such as no self-harm thoughts\n"
                    "- 1 = mild, vague, occasional, or indirectly supported\n"
                    "- 2 = clear support, repeated mention, or definite functional impact\n"
                    "- 3 = severe, near-daily, escalating, or strongly impairing support\n\n"
                    "Return JSON with keys: items, safety_level, safety_cues, notes.\n"
                    "items must be a list of objects with item_id, value, evidence_quote, confidence_note.\n"
                    "Only include items with value 1, 2, or 3, except use value 0 for explicit denials such as clearly denying self-harm or suicidal thoughts.\n"
                    "Look carefully for subtle but supported signals.\n"
                    "Treat indirect but concrete evidence as valid when it clearly implies the symptom.\n"
                    "If the user clearly says they are not suicidal, are not thinking of harming themselves, or have no plan or wish to hurt themselves, include phq_q9_self_harm with value 0.\n"
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
                    "Only include supported items with values 1, 2, or 3, except value 0 for explicit denials such as no self-harm thoughts. "
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
                    "If the user explicitly denies self-harm or suicidal thinking, include phq_q9_self_harm with value 0.\n"
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
                    "Pay extra attention to subtle English cues for low mood, anhedonia, appetite change, harsh self-view, nervousness, trouble relaxing, restlessness, awful-outcome worry, disrupted sleep, and disappearance or self-harm language. "
                    "Use value 0 for explicit denials, especially when the user clearly denies self-harm or suicidal thoughts. "
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
                    "Return supported items with values 1, 2, or 3, or value 0 for explicit denials.\n"
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
                    "- 0 = explicit, direct denial or absence, mainly for clear safety denials such as no self-harm thoughts\n"
                    "- 1 = mild, occasional, or indirectly supported\n"
                    "- 2 = clear support, repeated mention, or definite functional impact\n"
                    "- 3 = severe, near-daily, escalating, or strongly impairing support\n\n"
                    "Coverage reminders:\n"
                    "- Appetite may appear as skipped meals, late eating, or eating only whatever is quickest.\n"
                    "- Worthlessness may appear as self-blame, burden language, feeling weak, or saying others are better off.\n"
                    "- Concentration may appear as rereading, staring at the same task, or getting nowhere.\n"
                    "- Relaxation difficulty may appear as replaying comments, not switching off, or carrying body tension after stress.\n"
                    "- Fear that something awful will happen may appear as catastrophe expectations about money, work, or family consequences.\n"
                    "- Clear denial like 'I am not suicidal' should close phq_q9_self_harm with value 0.\n"
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
                    "Return items with value 1, 2, or 3, or value 0 for explicit denials.\n"
                    "Focus especially on subtle but supported signals for anhedonia, low mood, appetite, worthlessness, concentration, nervousness, trouble relaxing, restlessness, irritability, "
                    "fear of awful outcomes, control of worry, and clear self-harm denial.\n"
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

    def warmup(self) -> bool:
        if not self.enabled:
            return False
        warmup = getattr(self._client, "warmup", None)
        if warmup is None:
            return False
        return bool(warmup())

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
