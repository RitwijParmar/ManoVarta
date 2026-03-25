import re
from typing import Iterable, Optional


WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_text(text: str) -> str:
    cleaned = WORD_RE.sub(" ", text.lower())
    return " ".join(cleaned.split())


def contains_any(text: str, phrases: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(phrase) in normalized for phrase in phrases)


def first_match(text: str, phrases: Iterable[str]) -> Optional[str]:
    normalized = normalize_text(text)
    for phrase in phrases:
        if normalize_text(phrase) in normalized:
            return phrase
    return None


def extract_window(text: str, phrase: str, radius: int = 32) -> str:
    lowered = text.lower()
    index = lowered.find(phrase)
    if index == -1:
        return text.strip()
    start = max(0, index - radius)
    end = min(len(text), index + len(phrase) + radius)
    snippet = text[start:end].strip(" ,.")
    return snippet or text.strip()
