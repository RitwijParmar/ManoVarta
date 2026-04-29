from __future__ import annotations

from pathlib import Path
import threading
from typing import Iterable, Optional, Sequence

from manovarta_core.json_utils import normalize_safety_level
from manovarta_core.safety import SafetyMonitor
from manovarta_core.schemas import SafetyFlag, Turn


SAFETY_RANK = {"none": 0, "review": 1, "urgent": 2}
SAFETY_LABEL_TO_ID = {"none": 0, "review": 1, "urgent": 2}


def merge_safety_flags(*flags: SafetyFlag) -> SafetyFlag:
    resolved = [flag for flag in flags if flag is not None]
    if not resolved:
        return SafetyFlag()

    dominant = max(resolved, key=lambda flag: SAFETY_RANK.get(flag.level, 0))
    cues: list[str] = []
    rationale_parts: list[str] = []
    for flag in resolved:
        cues.extend(flag.cues)
        if flag.rationale:
            rationale_parts.append(flag.rationale)
    return SafetyFlag(
        level=dominant.level,
        cues=list(dict.fromkeys(cue for cue in cues if cue)),
        rationale=" ".join(dict.fromkeys(rationale_parts)) or None,
        needs_human_review=dominant.level in {"review", "urgent"},
    )


def compose_runtime_safety_flag(
    *,
    extractor_flag: SafetyFlag | None = None,
    rule_flag: SafetyFlag | None = None,
    checkpoint_flag: SafetyFlag | None = None,
) -> SafetyFlag:
    advisory_flag = extractor_flag or SafetyFlag()
    rule_flag = rule_flag or SafetyFlag()
    checkpoint_flag = checkpoint_flag or SafetyFlag()

    corroborating_flags = [
        flag for flag in (rule_flag, checkpoint_flag) if flag.level != "none"
    ]
    if not corroborating_flags:
        return SafetyFlag()

    merged = merge_safety_flags(*corroborating_flags)
    advisory_cues = []
    advisory_notes = []
    if advisory_flag.level != "none":
        advisory_cues.append(f"extractor_advisory:{advisory_flag.level}")
        if advisory_flag.rationale:
            advisory_notes.append(advisory_flag.rationale)
    if advisory_flag.cues:
        advisory_cues.extend(f"extractor_advisory:{cue}" for cue in advisory_flag.cues if cue)

    merged_cues = list(dict.fromkeys(merged.cues + advisory_cues))
    rationale_parts = [part for part in [merged.rationale, *advisory_notes] if part]
    if advisory_cues:
        rationale_parts.append("Advisory safety signal was treated as advisory until corroborated by the runtime safety stack.")

    return merged.model_copy(
        update={
            "cues": merged_cues,
            "rationale": " ".join(dict.fromkeys(rationale_parts)) or merged.rationale,
        }
    )


def build_safety_assessment_text(turns: Sequence[Turn]) -> str:
    user_turns = [turn.text.strip() for turn in turns if turn.speaker == "user" and turn.text.strip()]
    if not user_turns:
        return ""

    latest_turn = user_turns[-1]
    recent_turns = "\n".join(user_turns[-2:]).strip()
    full_text = "\n".join(user_turns)
    sections = [f"Most recent disclosure:\n{latest_turn}"]
    if recent_turns and recent_turns != latest_turn:
        sections.append(f"Recent context:\n{recent_turns}")

    words = full_text.split()
    if len(words) > 96:
        sections.append(f"Conversation tail:\n{' '.join(words[-96:])}")
    return "\n\n".join(sections)


def build_turns_from_extractor_example(example: dict) -> list[Turn]:
    transcript_block = example["text"].rsplit("<|assistant|>", 1)[0]
    transcript = transcript_block.split("Transcript:\n", 1)[-1]
    turns: list[Turn] = []
    for index, raw_line in enumerate(transcript.splitlines(), start=1):
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        speaker, text = line.split(":", 1)
        speaker = speaker.strip().lower()
        if speaker not in {"assistant", "user"}:
            continue
        turns.append(
            Turn(
                turn_id=index,
                speaker=speaker,
                text=text.strip(),
                language_tag=example.get("language", "en"),
            )
        )
    return turns


class CompositeSafetyAssessor:
    def __init__(self, assessors: Iterable[object]) -> None:
        self.assessors = [assessor for assessor in assessors if assessor is not None]

    @property
    def enabled(self) -> bool:
        return any(getattr(assessor, "enabled", True) for assessor in self.assessors)

    def warmup(self) -> bool:
        warmed = False
        for assessor in self.assessors:
            if not getattr(assessor, "enabled", True):
                continue
            warmup = getattr(assessor, "warmup", None)
            if warmup is None:
                continue
            warmed = bool(warmup()) or warmed
        return warmed

    def assess(self, turns: list[Turn], language: str) -> Optional[SafetyFlag]:
        flags: list[SafetyFlag] = []
        for assessor in self.assessors:
            if not getattr(assessor, "enabled", True):
                continue
            flag = assessor.assess(turns, language)
            if flag is not None:
                flags.append(flag)
        if not flags:
            return None
        return merge_safety_flags(*flags)


class LocalSafetyCheckpointAssessor:
    def __init__(self, model_path: str | Path | None, *, device: str = "auto", max_length: int = 256) -> None:
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.device = device
        self.max_length = max_length
        self._backend = None
        self._load_lock = threading.Lock()
        self._load_complete = threading.Event()
        self._load_started = False

    @property
    def enabled(self) -> bool:
        return bool(self.model_path and self.model_path.exists())

    def warmup(self, *, wait_timeout: float | None = None) -> bool:
        if not self.enabled:
            return False
        should_load_inline = False
        with self._load_lock:
            if self._backend is not None:
                return True
            if not self._load_started:
                self._load_started = True
                self._load_complete.clear()
                should_load_inline = True
        if should_load_inline:
            self._load_backend()
        else:
            self._load_complete.wait(wait_timeout)
        return self._backend is not None

    def assess(self, turns: list[Turn], language: str) -> Optional[SafetyFlag]:
        del language
        if not self.enabled:
            return None

        text = build_safety_assessment_text(turns)
        if not text:
            return None

        if self._backend is None:
            self._load_backend_async()
            return None
        if self._backend is None:
            return None

        torch, tokenizer, model, device = self._backend
        encoded = tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        if device != "cpu":
            encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = model(**encoded).logits
        label_id = int(logits.argmax(dim=-1).item())
        label = normalize_safety_level(model.config.id2label.get(label_id, str(label_id)).lower())
        if label == "none":
            return SafetyFlag()
        return SafetyFlag(
            level=label,
            cues=[f"local_safety:{self.model_path.name}"],
            rationale="Local safety checkpoint flagged elevated risk.",
            needs_human_review=True,
        )

    def _load_backend_async(self) -> None:
        if self._backend is not None or not self.enabled:
            return
        with self._load_lock:
            if self._backend is not None or self._load_started:
                return
            self._load_started = True
            self._load_complete.clear()
        thread = threading.Thread(target=self._load_backend, name="local-safety-checkpoint-loader", daemon=True)
        thread.start()

    def _load_backend(self) -> None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:  # pragma: no cover
            with self._load_lock:
                self._backend = None
                self._load_started = False
            self._load_complete.set()
            return
        from training.runtime_utils import detect_device

        try:
            device = detect_device(torch, self.device)
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_path,
                    trust_remote_code=True,
                    fix_mistral_regex=True,
                )
            except TypeError:
                tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            model = AutoModelForSequenceClassification.from_pretrained(self.model_path, trust_remote_code=True)
        except Exception:  # pragma: no cover
            with self._load_lock:
                self._backend = None
                self._load_started = False
            self._load_complete.set()
            return
        if device != "cpu":
            model.to(device)
        model.eval()
        self._backend = (torch, tokenizer, model, device)
        self._load_complete.set()


def evaluate_safety_stack(
    *,
    extractor_safety_level: str,
    turns: list[Turn],
    language: str,
    use_rule_safety_monitor: bool = False,
    safety_assessor: object | None = None,
) -> dict[str, object]:
    extractor_flag = SafetyFlag(
        level=normalize_safety_level(extractor_safety_level),
        needs_human_review=normalize_safety_level(extractor_safety_level) in {"review", "urgent"},
    )
    component_levels = {
        "extractor": extractor_flag.level,
        "rule": "none",
        "checkpoint": "none",
    }
    rule_flag = SafetyFlag()
    checkpoint_flag = SafetyFlag()

    if use_rule_safety_monitor:
        rule_flag = SafetyMonitor().assess(turns)
        component_levels["rule"] = rule_flag.level

    if safety_assessor is not None and getattr(safety_assessor, "enabled", True):
        assessed_flag = safety_assessor.assess(turns, language)
        if assessed_flag is not None:
            component_levels["checkpoint"] = assessed_flag.level
            checkpoint_flag = assessed_flag

    merged_flag = compose_runtime_safety_flag(
        extractor_flag=extractor_flag,
        rule_flag=rule_flag,
        checkpoint_flag=checkpoint_flag,
    )
    return {
        "flag": merged_flag,
        "components": component_levels,
    }
