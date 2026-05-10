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

    stripped_answer = answer.strip()
    sentences = _split_sentences(stripped_answer)
    if len(sentences) <= max_sentences:
        return stripped_answer
    return " ".join(sentences[:max_sentences])


def _split_sentences(text: str) -> list[str]:
    """Split sentences without treating numeric thousand separators as periods."""

    sentences = []
    start = 0
    index = 0
    while index < len(text):
        character = text[index]
        if character in ".!?" and not _is_numeric_period(text, index):
            next_index = index + 1
            if next_index == len(text) or text[next_index].isspace():
                sentence = text[start:next_index].strip()
                if sentence:
                    sentences.append(sentence)
                while next_index < len(text) and text[next_index].isspace():
                    next_index += 1
                start = next_index
                index = next_index
                continue
        index += 1

    trailing_sentence = text[start:].strip()
    if trailing_sentence:
        sentences.append(trailing_sentence)
    return sentences


def _is_numeric_period(text: str, index: int) -> bool:
    """Return True when a period is surrounded by digits, as in 645.108."""

    return (
        text[index] == "."
        and index > 0
        and index + 1 < len(text)
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    )


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
