"""Useful deterministic fallbacks for unsupported analytics dimensions."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

DATASET_GAP_REASON = "dataset_gap"
CAMPAIGN_CREATIVE_TERMS = (
    "campanha",
    "campanhas",
    "criativo",
    "criativos",
    "anuncio",
    "anuncios",
    "peca",
    "pecas",
    "campanha paga",
    "criativo vencedor",
)
ALTERNATIVE_ANALYSIS_TERMS = (
    "analise parecida",
    "analise semelhante",
    "analise proxima",
    "alternativa util",
    "o que da para analisar",
    "o que consigo analisar",
    "o que voce consegue analisar",
)
MISSING_DATA_TERMS = (
    "quais dados faltariam",
    "que dados faltariam",
    "dados faltariam",
    "dados faltam",
    "o que faltaria",
)
AVAILABLE_DATA_TERMS = (
    "dados disponiveis",
    "com os dados disponiveis",
    "voce consegue responder isso",
    "da para responder isso",
    "consegue responder isso",
)


def resolve_scope_fallback(
    question: str,
    conversation_history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return a helpful fallback when the dataset lacks the requested dimension."""

    normalized_question = _normalize_text(question)
    history_has_campaign_gap = _history_mentions_campaign_creative_gap(
        conversation_history
    )

    if _mentions_campaign_or_creative(normalized_question):
        return _build_fallback_state(_campaign_creative_answer())

    if history_has_campaign_gap and _asks_missing_data(normalized_question):
        return _build_fallback_state(_missing_data_answer())

    if history_has_campaign_gap and _asks_available_data_answer(normalized_question):
        return _build_fallback_state(_available_data_answer())

    if _asks_alternative_analysis(normalized_question):
        return _build_fallback_state(_alternative_analysis_answer())

    return None


def _build_fallback_state(answer: str) -> dict[str, Any]:
    """Build an AgentState patch that keeps the useful fallback answer."""

    return {
        "intent": "out_of_scope",
        "traffic_source": None,
        "mentioned_traffic_sources": [],
        "date_range": None,
        "tool_name": None,
        "tool_args": {},
        "tool_result": None,
        "error": None,
        "answer": answer,
        "out_of_scope_reason": DATASET_GAP_REASON,
    }


def _campaign_creative_answer() -> str:
    """Explain campaign/creative limitations and the closest available analysis."""

    return (
        "Não tenho dados de campanha ou criativo no dataset atual. "
        "Para responder isso, seriam necessários dados por campanha/criativo, "
        "como impressões, cliques, usuários, usuários convertidos, pedidos e receita. "
        "Com os dados atuais, a análise mais próxima é comparar canais de tráfego "
        "por usuários, usuários convertidos, taxa de conversão, pedidos e receita."
    )


def _missing_data_answer() -> str:
    """Explain which fields would be required for the unsupported question."""

    return (
        "Faltariam dados por campanha ou criativo, como impressões, cliques, "
        "usuários, usuários convertidos, pedidos e receita associados a cada peça. "
        "Com o dataset atual, a alternativa útil é comparar canais de tráfego "
        "por volume, conversão, pedidos e receita."
    )


def _available_data_answer() -> str:
    """Explain what can and cannot be answered with the current dataset."""

    return (
        "Não consigo responder diretamente sobre campanha ou criativo com os dados "
        "disponíveis. O dataset atual permite comparar canais de tráfego por "
        "usuários, usuários convertidos, taxa de conversão, pedidos e receita."
    )


def _alternative_analysis_answer() -> str:
    """Offer the closest useful analysis using only available fields."""

    return (
        "Com o dataset atual, a análise mais próxima é comparar canais de tráfego "
        "por usuários, usuários convertidos, taxa de conversão, pedidos e receita. "
        "Isso não identifica o melhor criativo, mas mostra quais origens estão "
        "trazendo tráfego mais qualificado e maior impacto comercial."
    )


def _mentions_campaign_or_creative(normalized_question: str) -> bool:
    """Detect unsupported campaign, ad or creative dimensions."""

    return any(term in normalized_question for term in CAMPAIGN_CREATIVE_TERMS)


def _asks_alternative_analysis(normalized_question: str) -> bool:
    """Detect requests for the closest useful analysis with current data."""

    if any(term in normalized_question for term in ALTERNATIVE_ANALYSIS_TERMS):
        return True

    has_current_dataset_reference = (
        "dataset atual" in normalized_question
        or "dados atuais" in normalized_question
        or "esses dados" in normalized_question
    )
    has_analysis_request = any(
        term in normalized_question
        for term in ("analise", "analisar", "consegue fazer", "da para fazer")
    )
    return has_current_dataset_reference and has_analysis_request


def _asks_missing_data(normalized_question: str) -> bool:
    """Detect questions about missing fields for the unavailable analysis."""

    return any(term in normalized_question for term in MISSING_DATA_TERMS)


def _asks_available_data_answer(normalized_question: str) -> bool:
    """Detect whether the user asks if the previous topic can be answered."""

    return any(term in normalized_question for term in AVAILABLE_DATA_TERMS)


def _history_mentions_campaign_creative_gap(
    conversation_history: list[dict[str, Any]],
) -> bool:
    """Detect whether recent context is about missing campaign/creative data."""

    for message in reversed(conversation_history[-5:]):
        content = message.get("content")
        if not isinstance(content, str):
            continue
        normalized_content = _normalize_text(content)
        if _mentions_campaign_or_creative(normalized_content):
            return True
    return False


def _normalize_text(value: str) -> str:
    """Normalize accents, punctuation and whitespace for rule checks."""

    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents)
    return " ".join(without_punctuation.split())
