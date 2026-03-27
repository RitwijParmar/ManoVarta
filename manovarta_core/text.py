import re
from typing import Iterable, Optional


WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_text(text: str) -> str:
    cleaned = WORD_RE.sub(" ", text.lower())
    return " ".join(cleaned.split())


def contains_any(text: str, phrases: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    return any(contains_phrase(normalized, phrase, pre_normalized=True) for phrase in phrases)


def first_match(text: str, phrases: Iterable[str]) -> Optional[str]:
    for phrase in phrases:
        if contains_phrase(text, phrase):
            return phrase
    return None


def contains_phrase(text: str, phrase: str, pre_normalized: bool = False) -> bool:
    normalized = text if pre_normalized else normalize_text(text)
    target = normalize_text(phrase)
    if not target:
        return False
    pattern = rf"(^|\s){re.escape(target)}($|\s)"
    return re.search(pattern, normalized) is not None


def extract_window(text: str, phrase: str, radius: int = 32) -> str:
    lowered = text.lower()
    index = lowered.find(phrase)
    if index == -1:
        return text.strip()
    start = max(0, index - radius)
    end = min(len(text), index + len(phrase) + radius)
    snippet = text[start:end].strip(" ,.")
    return snippet or text.strip()
