"""Answer style detection and safety formatting."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

SHORT_ANSWER_PATTERNS = (
    "em uma frase",
    "uma frase",
    "curta",
    "curto",
    "resuma",
    "conclusao curta",
    "direto",
    "objetivo",
)
DEFAULT_SHORT_MAX_SENTENCES = 2


def detect_answer_style(question: str) -> dict[str, Any]:
    """Return deterministic answer style flags for the current question."""

    short_answer = _looks_like_short_answer_request(question)
    return {
        "short_answer": short_answer,
        "max_sentences": DEFAULT_SHORT_MAX_SENTENCES if short_answer else None,
        "use_default_answer_structure": not short_answer,
    }


def limit_sentences(answer: str, max_sentences: int | None) -> str:
    """Limit an answer to a maximum number of sentences when requested."""

    if max_sentences is None or max_sentences <= 0:
        return answer

    parts = re.split(r"(?<=[.!?])\s+", answer.strip())
    sentences = [part.strip() for part in parts if part.strip()]
    if len(sentences) <= max_sentences:
        return answer.strip()
    return " ".join(sentences[:max_sentences])


def _looks_like_short_answer_request(question: str) -> bool:
    """Detect explicit user requests for concise answers."""

    normalized_question = _normalize_text(question)
    return any(pattern in normalized_question for pattern in SHORT_ANSWER_PATTERNS)


def _normalize_text(value: str) -> str:
    """Normalize accents, punctuation and whitespace for rule checks."""

    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents)
    return " ".join(without_punctuation.split())
