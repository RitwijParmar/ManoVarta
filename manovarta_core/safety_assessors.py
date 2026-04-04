from __future__ import annotations

from pathlib import Path
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

    @property
    def enabled(self) -> bool:
        return bool(self.model_path and self.model_path.exists())

    def assess(self, turns: list[Turn], language: str) -> Optional[SafetyFlag]:
        del language
        if not self.enabled:
            return None

        text = build_safety_assessment_text(turns)
        if not text:
            return None

        if self._backend is None:
            self._load_backend()
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

    def _load_backend(self) -> None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:  # pragma: no cover
            self._backend = None
            return
        from training.runtime_utils import detect_device

        device = detect_device(torch, self.device)
        try:
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_path,
                    trust_remote_code=True,
                    fix_mistral_regex=True,
                )
            except TypeError:
                tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            model = AutoModelForSequenceClassification.from_pretrained(self.model_path, trust_remote_code=True)
        except OSError:  # pragma: no cover
            self._backend = None
            return
        if device != "cpu":
            model.to(device)
        model.eval()
        self._backend = (torch, tokenizer, model, device)


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
    flags = [extractor_flag]
    component_levels = {
        "extractor": extractor_flag.level,
        "rule": "none",
        "checkpoint": "none",
    }

    if use_rule_safety_monitor:
        rule_flag = SafetyMonitor().assess(turns)
        component_levels["rule"] = rule_flag.level
        flags.append(rule_flag)

    if safety_assessor is not None and getattr(safety_assessor, "enabled", True):
        assessed_flag = safety_assessor.assess(turns, language)
        if assessed_flag is not None:
            component_levels["checkpoint"] = assessed_flag.level
            flags.append(assessed_flag)

    merged_flag = merge_safety_flags(*flags)
    return {
        "flag": merged_flag,
        "components": component_levels,
    }
