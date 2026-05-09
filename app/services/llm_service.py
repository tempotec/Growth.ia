"""LLM service wrapper for Glacier AI V1."""

from __future__ import annotations

from calendar import monthrange
import json
import logging
import re
import unicodedata
from datetime import date, timedelta
from typing import Any, get_args

from openai import OpenAI

from app.agent.prompts import (
    ANSWER_SYSTEM_PROMPT,
    PARSE_SYSTEM_PROMPT,
    build_answer_user_prompt,
    build_parse_user_prompt,
)
from app.core.config import get_settings
from app.core.logging import elapsed_ms, get_logger, log_event, short_text, start_timer
from app.schemas.analytics import AllowedTrafficSource, ParsedQuestion

ALLOWED_TRAFFIC_SOURCES = tuple(get_args(AllowedTrafficSource))
MONTHS_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
GENERAL_CHANNEL_DATA_TERMS = ("dados", "numeros", "resultado", "resumo", "performance")
PERFORMANCE_CONTEXT_TERMS = (
    "baixo desempenho",
    "performance",
    "melhor canal",
    "pior canal",
    "comparacao",
    "comparar",
    "conversao",
    "receita",
    "pedidos",
)
PERFORMANCE_CONTEXT_INTENTS = {
    "best_channel_performance",
    "channel_performance_by_source",
    "revenue_by_source",
    "recommendation",
}
CONTEXT_DATE_TERMS = ("nesse periodo", "neste periodo", "no mesmo periodo", "nesse mes")
RECOMMENDATION_PATTERNS = (
    "recomendacao",
    "recomenda",
    "acao pratica",
    "o que fazer",
    "proximo passo",
    "gerente de midia",
    "investigar",
    "antes de tomar uma decisao",
    "pausar",
    "pausado",
    "pausada",
    "otimizar",
    "otimizado",
    "otimizada",
    "investir",
    "vale a pena",
    "vale investir",
    "o que isso indica",
    "o que esse resultado indica",
    "resultado indica",
    "decidir",
    "decisao",
    "com base nisso",
)
CONTEXT_REFERENCE_TERMS = (
    "esse canal",
    "este canal",
    "ele",
    "dele",
    "isso",
    "esse resultado",
    "este resultado",
    "esse volume",
    "com base nisso",
    "essa decisao",
    "antes de tomar uma decisao",
)
CONTEXTUAL_BUSINESS_TERMS = (
    "trafego",
    "volume",
    "receita",
    "conversao",
    "pedido",
    "performance",
    "resultado",
)


class LLMServiceError(Exception):
    """Raised when an LLM interaction fails or returns invalid output."""


class LLMService:
    """Thin wrapper around OpenAI chat completions."""

    def __init__(self, client: OpenAI | None = None, model: str | None = None) -> None:
        settings = None
        if client is None or model is None:
            settings = get_settings()
        self._model = model or settings.openai_model
        self._client = client or OpenAI(api_key=settings.openai_api_key)
        self._logger = get_logger(__name__)

    def parse_question(
        self,
        question: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> ParsedQuestion:
        """Parse a natural-language question into a structured intent payload."""

        request_start = start_timer()
        recent_history = conversation_history or []
        high_confidence_parse = _parse_high_confidence_question(
            question,
            conversation_history=recent_history,
        )
        if high_confidence_parse is not None:
            log_event(
                self._logger,
                logging.INFO,
                "llm_parse_completed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                intent=high_confidence_parse.intent,
                parse_source="high_confidence_rules",
            )
            return high_confidence_parse

        log_event(
            self._logger,
            logging.INFO,
            "llm_parse_started",
            model=self._model,
            question_preview=short_text(question),
            conversation_turns=len(recent_history),
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_parse_user_prompt(
                            question,
                            conversation_history=recent_history,
                        ),
                    },
                ],
            )
            content = self._extract_content(response)
            payload = json.loads(content)
            parsed_question = ParsedQuestion.model_validate(payload)
            log_event(
                self._logger,
                logging.INFO,
                "llm_parse_completed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                intent=parsed_question.intent,
            )
            return parsed_question
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "llm_parse_failed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                error_type=type(exc).__name__,
            )
            raise LLMServiceError("Failed to parse question with the configured LLM.") from exc

    def generate_answer(
        self,
        *,
        question: str,
        intent: str | None,
        tool_result: Any = None,
        out_of_scope_reason: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate a final business-friendly answer."""

        request_start = start_timer()
        recent_history = conversation_history or []
        log_event(
            self._logger,
            logging.INFO,
            "llm_answer_started",
            model=self._model,
            intent=intent,
            question_preview=short_text(question),
            conversation_turns=len(recent_history),
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_answer_user_prompt(
                            question=question,
                            intent=intent,
                            tool_result=tool_result,
                            out_of_scope_reason=out_of_scope_reason,
                            conversation_history=recent_history,
                        ),
                    },
                ],
            )
            answer = self._extract_content(response).strip()
            log_event(
                self._logger,
                logging.INFO,
                "llm_answer_completed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                intent=intent,
            )
            return answer
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "llm_answer_failed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                error_type=type(exc).__name__,
                intent=intent,
            )
            raise LLMServiceError("Failed to generate final answer with the configured LLM.") from exc

    def validate_connectivity(self) -> str:
        """Run a cheap connectivity check against the configured model."""

        request_start = start_timer()
        log_event(
            self._logger,
            logging.INFO,
            "llm_connectivity_check_started",
            model=self._model,
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                max_tokens=10,
                messages=[
                    {
                        "role": "user",
                        "content": "Reply with exactly OK if you can read this message.",
                    }
                ],
            )
            result = self._extract_content(response).strip()
            log_event(
                self._logger,
                logging.INFO,
                "llm_connectivity_check_completed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
            )
            return result
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "llm_connectivity_check_failed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                error_type=type(exc).__name__,
            )
            raise LLMServiceError("Failed to validate OpenAI connectivity.") from exc

    @staticmethod
    def _extract_content(response: Any) -> str:
        """Extract the first assistant message content from a completion response."""

        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM response did not include content.")
        return content


def _parse_high_confidence_question(
    question: str,
    *,
    conversation_history: list[dict[str, Any]],
) -> ParsedQuestion | None:
    """Resolve common source-specific follow-ups without depending on the LLM."""

    normalized_question = _normalize_text(question)
    sources = _find_traffic_sources(normalized_question)
    recommendation_parse = _parse_recommendation_question(
        normalized_question,
        sources=sources,
        conversation_history=conversation_history,
    )
    if recommendation_parse is not None:
        return recommendation_parse

    if len(sources) != 1:
        return None

    has_general_data_term = any(
        term in normalized_question for term in GENERAL_CHANNEL_DATA_TERMS
    )
    short_performance_followup = (
        _looks_like_short_channel_followup(normalized_question)
        and _history_indicates_performance_context(conversation_history)
    )
    if not has_general_data_term and not short_performance_followup:
        return None

    start_date, end_date = _resolve_date_range(
        normalized_question,
        conversation_history=conversation_history,
        reference_date=date.today(),
    )
    return ParsedQuestion(
        intent="channel_performance_by_source",
        traffic_source=sources[0],
        date_range={
            "start_date": start_date,
            "end_date": end_date,
        },
        needs_data=True,
        out_of_scope_reason=None,
    )


def _parse_recommendation_question(
    normalized_question: str,
    *,
    sources: list[str],
    conversation_history: list[dict[str, Any]],
) -> ParsedQuestion | None:
    """Resolve recommendation and contextual business follow-ups deterministically."""

    if not _looks_like_recommendation_question(normalized_question):
        return None

    traffic_source = sources[0] if len(sources) == 1 else None
    if traffic_source is None:
        traffic_source = _latest_history_traffic_source(conversation_history)

    start_date, end_date = _resolve_date_range(
        normalized_question,
        conversation_history=conversation_history,
        reference_date=date.today(),
    )
    return ParsedQuestion(
        intent="recommendation",
        traffic_source=traffic_source,
        date_range={
            "start_date": start_date,
            "end_date": end_date,
        },
        needs_data=True,
        out_of_scope_reason=None,
    )


def _looks_like_recommendation_question(normalized_question: str) -> bool:
    """Identify recommendation and decision-oriented follow-up questions."""

    if any(pattern in normalized_question for pattern in RECOMMENDATION_PATTERNS):
        return True

    has_context_reference = any(
        re.search(rf"\b{re.escape(term)}\b", normalized_question)
        for term in CONTEXT_REFERENCE_TERMS
    )
    has_business_term = any(
        term in normalized_question for term in CONTEXTUAL_BUSINESS_TERMS
    )
    return has_context_reference and has_business_term


def _normalize_text(value: str) -> str:
    """Normalize accents, punctuation and whitespace for rule checks."""

    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents)
    return " ".join(without_punctuation.split())


def _find_traffic_sources(normalized_question: str) -> list[str]:
    """Return supported traffic sources explicitly mentioned in the question."""

    sources: list[str] = []
    for source in ALLOWED_TRAFFIC_SOURCES:
        if re.search(rf"\b{re.escape(source.lower())}\b", normalized_question):
            sources.append(source)
    return sources


def _looks_like_short_channel_followup(normalized_question: str) -> bool:
    """Identify concise follow-ups such as 'e o Facebook nesse periodo?'."""

    words = normalized_question.split()
    return (
        len(words) <= 8
        and normalized_question.startswith(("e ", "e o ", "e a ", "e esse "))
    ) or any(term in normalized_question for term in CONTEXT_DATE_TERMS)


def _history_indicates_performance_context(
    conversation_history: list[dict[str, Any]],
) -> bool:
    """Detect whether recent history is about channel performance."""

    for message in reversed(conversation_history[-10:]):
        intent = message.get("intent")
        if intent in PERFORMANCE_CONTEXT_INTENTS:
            return True

        content = message.get("content")
        if isinstance(content, str):
            normalized_content = _normalize_text(content)
            if any(term in normalized_content for term in PERFORMANCE_CONTEXT_TERMS):
                return True

    return False


def _latest_history_traffic_source(
    conversation_history: list[dict[str, Any]],
) -> str | None:
    """Return the most recent structured traffic source from conversation history."""

    for message in reversed(conversation_history[-10:]):
        traffic_source = message.get("traffic_source")
        if traffic_source in ALLOWED_TRAFFIC_SOURCES:
            return traffic_source

    return None


def _resolve_date_range(
    normalized_question: str,
    *,
    conversation_history: list[dict[str, Any]],
    reference_date: date,
) -> tuple[date, date]:
    """Resolve explicit month references, inherited periods, or default window."""

    explicit_month = _extract_explicit_month(normalized_question)
    if explicit_month is not None:
        year = _extract_year(normalized_question) or reference_date.year
        last_day = monthrange(year, explicit_month)[1]
        return date(year, explicit_month, 1), date(year, explicit_month, last_day)

    if any(term in normalized_question for term in CONTEXT_DATE_TERMS):
        inherited = _latest_history_date_range(conversation_history)
        if inherited is not None:
            return inherited

    inherited = _latest_history_date_range(conversation_history)
    if inherited is not None and _looks_like_short_channel_followup(normalized_question):
        return inherited

    default_start = reference_date - timedelta(days=29)
    return default_start, reference_date


def _extract_explicit_month(normalized_question: str) -> int | None:
    """Extract a Portuguese month from the question."""

    previous_month_match = re.search(r"\bmes anterior a (\w+)\b", normalized_question)
    if previous_month_match:
        month = MONTHS_PT.get(previous_month_match.group(1))
        if month is None:
            return None
        return 12 if month == 1 else month - 1

    for month_name, month_number in MONTHS_PT.items():
        if re.search(rf"\b{month_name}\b", normalized_question):
            return month_number

    return None


def _extract_year(normalized_question: str) -> int | None:
    """Extract an explicit year from the question when present."""

    match = re.search(r"\b(20\d{2})\b", normalized_question)
    return int(match.group(1)) if match else None


def _latest_history_date_range(
    conversation_history: list[dict[str, Any]],
) -> tuple[date, date] | None:
    """Return the most recent structured date range from conversation history."""

    for message in reversed(conversation_history[-10:]):
        date_range = message.get("date_range")
        if not isinstance(date_range, dict):
            continue
        start_date = date_range.get("start_date")
        end_date = date_range.get("end_date")
        if not isinstance(start_date, str) or not isinstance(end_date, str):
            continue
        try:
            return date.fromisoformat(start_date), date.fromisoformat(end_date)
        except ValueError:
            continue

    return None
