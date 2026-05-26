"""FastAPI routes for Glacier AI V1."""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.agent.graph import run_agent_question
from app.core.cache_config import get_cache_settings
from app.core.logging import elapsed_ms, get_logger, log_event, short_text, start_timer
from app.repositories.local_cache_repository import (
    LocalCacheRepository,
    LocalCacheSnapshotNotFoundError,
)
from app.schemas.api import (
    AskRequest,
    AskResponse,
    CacheStatusResponse,
    DashboardOverviewResponse,
)
from app.services.dashboard_overview_service import DashboardOverviewService

router = APIRouter()
logger = get_logger(__name__)

OUT_OF_SCOPE_ERROR = "unsupported_intent"
OUT_OF_SCOPE_MESSAGE = (
    "Essa pergunta está fora do escopo atual da V1. Posso te ajudar a analisar "
    "volume de usuários por origem, receita por canal, dados de um canal e "
    "performance por canal, além de recomendações baseadas nesses dados. "
    "Quando faltar contexto, posso sugerir a próxima análise possível sem "
    "inventar dados."
)
GREETING_MESSAGE = (
    "Olá! Posso te ajudar a analisar tráfego, receita e performance por canal. "
    "Você pode perguntar, por exemplo: "
    "'Como foi o volume de usuários vindos de Search no último mês?' ou "
    "'Qual canal teve melhor performance e por quê?'"
)
SIMPLE_GREETINGS = {"oi", "ola", "bom dia", "boa tarde", "boa noite"}
GENERIC_INTERNAL_ERROR = "internal_error"
GENERIC_INTERNAL_MESSAGE = "Nao foi possivel processar a solicitacao no momento."
LOCAL_CACHE_SNAPSHOT_NOT_FOUND = "local_cache_snapshot_not_found"
LOCAL_CACHE_SNAPSHOT_NOT_FOUND_MESSAGE = (
    "Ainda não há um snapshot local disponível para consultar os dados. "
    "Rode a sincronização do cache antes de fazer essa análise."
)
UNSUPPORTED_TRAFFIC_SOURCE_MESSAGE = (
    "Essa origem de tráfego não está disponível no escopo atual. "
    "Use uma das origens suportadas: Search, Organic, Facebook, Email, Direct, "
    "Display ou Referral."
)
INVALID_DATE_RANGE_MESSAGE = (
    "A janela de datas informada é inválida. A data inicial precisa ser menor "
    "ou igual à data final."
)


ANALYTICS_CONTEXT_METRICS = (
    "users",
    "converted_users",
    "orders",
    "revenue",
    "conversion_rate",
)
ANALYTICS_METRIC_CONTEXT_BY_TOOL = {
    "get_channel_performance_summary": "channel_performance_summary",
    "get_channel_performance_by_source": "channel_performance_by_source",
    "get_revenue_by_source": "revenue_by_source",
    "get_users_by_source": "users_by_source",
}
CONVERSATION_HISTORY_LIMIT = 20
CONVERSATION_STORE: dict[str, list[dict[str, Any]]] = {}


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    """Execute the Glacier AI agent for a validated question."""

    request_start = start_timer()
    log_event(
        logger,
        logging.INFO,
        "ask_request_received",
        conversation_id=payload.conversation_id,
        question_preview=short_text(payload.question),
        thinking_mode=payload.thinking_mode,
    )
    if _is_simple_greeting(payload.question):
        log_event(logger, logging.INFO, "ask_greeting_handled")
        response = AskResponse(
            conversation_id=payload.conversation_id,
            answer=GREETING_MESSAGE,
            thinking_mode=payload.thinking_mode,
            metadata=_execution_metadata(
                {},
                total_time_ms=elapsed_ms(request_start),
                thinking_mode=payload.thinking_mode,
            ),
            used_tool=None,
            data=None,
            error=None,
        )
        _append_conversation_turn(payload, response)
        return response

    conversation_history = _resolve_conversation_history(payload)
    try:
        if payload.thinking_mode:
            final_state = run_agent_question(
                payload.question,
                conversation_history=conversation_history,
                thinking_mode=True,
            )
        else:
            final_state = run_agent_question(
                payload.question,
                conversation_history=conversation_history,
            )
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "ask_request_failed",
            conversation_id=payload.conversation_id,
            thinking_mode=payload.thinking_mode,
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=GENERIC_INTERNAL_MESSAGE,
        ) from exc

    total_time_ms = elapsed_ms(request_start)
    response, status_code = _build_response(
        final_state,
        conversation_id=payload.conversation_id,
        thinking_mode=payload.thinking_mode,
        total_time_ms=total_time_ms,
    )
    log_event(
        logger,
        logging.INFO,
        "ask_request_completed",
        conversation_id=payload.conversation_id,
        intent=final_state.get("intent"),
        tool_name=final_state.get("tool_name"),
        thinking_mode=payload.thinking_mode,
        reflection_used=final_state.get("reflection_used"),
        reflection_score=final_state.get("reflection_score"),
        fallback_used=final_state.get("fallback_used"),
        total_time_ms=total_time_ms,
        tokens_used=final_state.get("tokens_used"),
        cost_estimate=final_state.get("cost_estimate"),
        http_status=status_code,
        controlled_error=bool(response.error),
    )
    if status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status_code, detail=response.model_dump())
    _append_conversation_turn(payload, response)
    return response


@router.get("/health")
def health() -> dict[str, str]:
    """Return a small healthcheck payload."""

    return {"status": "ok"}


@router.get("/cache/status", response_model=CacheStatusResponse)
def cache_status() -> CacheStatusResponse:
    """Return operational status for the local cache sync layer."""

    settings = get_cache_settings()
    repository = LocalCacheRepository()

    try:
        latest_sync = repository.get_latest_sync_status()
    except LocalCacheSnapshotNotFoundError:
        return CacheStatusResponse(
            status="warning",
            data_source_mode=settings.data_source_mode,
            last_sync_status=None,
            last_snapshot_at=None,
            cache_age_minutes=None,
            last_sync_started_at=None,
            last_sync_completed_at=None,
            last_sync_error_message="No cache sync has been recorded yet.",
        )

    last_snapshot_at = _parse_snapshot_datetime(latest_sync.get("snapshot_at"))
    return CacheStatusResponse(
        status="ok" if latest_sync["status"] == "success" else "warning",
        data_source_mode=settings.data_source_mode,
        last_sync_status=latest_sync["status"],
        last_snapshot_at=last_snapshot_at,
        cache_age_minutes=_compute_cache_age_minutes(last_snapshot_at),
        last_sync_started_at=_parse_snapshot_datetime(latest_sync["started_at"]),
        last_sync_completed_at=_parse_snapshot_datetime(latest_sync["completed_at"]),
        last_sync_error_message=latest_sync["error_message"],
    )


@router.get("/api/dashboard/overview", response_model=DashboardOverviewResponse)
def dashboard_overview(
    period: str = "30d",
    channel: str = "all",
) -> DashboardOverviewResponse:
    """Return the dashboard overview contract for the frontend shell."""
    return DashboardOverviewService().build_overview(period=period, channel=channel)


def _build_response(
    state: dict,
    *,
    conversation_id: str,
    thinking_mode: bool,
    total_time_ms: float,
) -> tuple[AskResponse, int]:
    """Translate the final agent state into the public HTTP response contract."""

    intent = state.get("intent")
    out_of_scope_reason = state.get("out_of_scope_reason")
    error = state.get("error")
    parse_metadata = _response_metadata(state)
    execution_metadata = _execution_metadata(
        state,
        total_time_ms=total_time_ms,
        thinking_mode=thinking_mode,
    )

    if intent == "out_of_scope" and out_of_scope_reason == OUT_OF_SCOPE_ERROR:
        response = AskResponse(
            conversation_id=conversation_id,
            answer=OUT_OF_SCOPE_MESSAGE,
            thinking_mode=thinking_mode,
            metadata=execution_metadata,
            used_tool=None,
            data=None,
            error=OUT_OF_SCOPE_ERROR,
            **parse_metadata,
        )
        return response, status.HTTP_200_OK

    if error:
        answer = state.get("answer") or error
        response_error = error
        if error == LOCAL_CACHE_SNAPSHOT_NOT_FOUND:
            answer = LOCAL_CACHE_SNAPSHOT_NOT_FOUND_MESSAGE
            response_error = LOCAL_CACHE_SNAPSHOT_NOT_FOUND
        elif _is_unsupported_traffic_source_error(error):
            answer = UNSUPPORTED_TRAFFIC_SOURCE_MESSAGE
            response_error = UNSUPPORTED_TRAFFIC_SOURCE_MESSAGE
        elif _is_invalid_date_range_error(error):
            answer = INVALID_DATE_RANGE_MESSAGE
            response_error = INVALID_DATE_RANGE_MESSAGE

        response = AskResponse(
            conversation_id=conversation_id,
            answer=answer,
            thinking_mode=thinking_mode,
            metadata=execution_metadata,
            used_tool=state.get("tool_name"),
            data=state.get("tool_result"),
            error=response_error,
            **parse_metadata,
        )
        if error == LOCAL_CACHE_SNAPSHOT_NOT_FOUND:
            return response, status.HTTP_503_SERVICE_UNAVAILABLE
        if _is_bad_request_error(error):
            return response, status.HTTP_400_BAD_REQUEST
        return response, status.HTTP_500_INTERNAL_SERVER_ERROR

    return (
        AskResponse(
            conversation_id=conversation_id,
            answer=state.get("answer") or "",
            thinking_mode=thinking_mode,
            metadata=execution_metadata,
            used_tool=state.get("tool_name"),
            data=state.get("tool_result"),
            error=None,
            **parse_metadata,
        ),
        status.HTTP_200_OK,
    )


def _resolve_conversation_history(payload: AskRequest) -> list[dict]:
    """Return explicit history or the stored history for the conversation id."""

    explicit_history = _serialize_conversation_history(payload)
    if explicit_history:
        return explicit_history
    return CONVERSATION_STORE.get(payload.conversation_id, [])[-10:]


def _append_conversation_turn(payload: AskRequest, response: AskResponse) -> None:
    """Persist a compact in-memory conversation turn for follow-up context."""

    history = CONVERSATION_STORE.setdefault(payload.conversation_id, [])
    history.append(
        {
            "role": "user",
            "content": payload.question,
        }
    )

    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "content": response.answer,
    }
    for key in (
        "intent",
        "traffic_source",
        "mentioned_traffic_sources",
        "date_range",
        "analytics_context",
    ):
        value = getattr(response, key)
        if value is not None:
            if hasattr(value, "model_dump"):
                assistant_message[key] = value.model_dump(mode="json", exclude_none=True)
            else:
                assistant_message[key] = value

    history.append(assistant_message)
    CONVERSATION_STORE[payload.conversation_id] = history[-CONVERSATION_HISTORY_LIMIT:]


def _execution_metadata(
    state: dict,
    *,
    total_time_ms: float,
    thinking_mode: bool,
):
    """Build public execution metadata without exposing internal critique."""

    return {
        "tool_used": state.get("tool_name"),
        "reflection_used": bool(state.get("reflection_used")),
        "reflection_score": state.get("reflection_score"),
        "fallback_used": bool(state.get("fallback_used")),
        "total_time_ms": total_time_ms,
        "reflection_time_ms": state.get("reflection_time_ms"),
        "tokens_used": state.get("tokens_used"),
        "cost_estimate": state.get("cost_estimate"),
    }


def _serialize_conversation_history(payload: AskRequest) -> list[dict]:
    """Convert recent Pydantic chat messages into compact JSON-ready context."""

    return [
        message.model_dump(mode="json", exclude_none=True)
        for message in payload.conversation_history[-10:]
    ]


def _response_metadata(state: dict) -> dict:
    """Expose the last parse so the frontend can enrich future history."""

    analytics_context = state.get("analytics_context") or _build_analytics_context(state)
    return {
        "intent": state.get("intent"),
        "traffic_source": state.get("traffic_source"),
        "mentioned_traffic_sources": state.get("mentioned_traffic_sources", []),
        "date_range": state.get("date_range"),
        "analytics_context": analytics_context,
    }


def _build_analytics_context(state: dict) -> dict | None:
    """Build compact structured context from the last tool result."""

    compact_result = _compact_tool_result(
        state.get("tool_result"),
        fallback_source=state.get("traffic_source"),
    )
    if not compact_result:
        return None

    mentioned_sources = state.get("mentioned_traffic_sources") or []
    if len(mentioned_sources) > 1:
        compact_result = {
            source: compact_result[source]
            for source in mentioned_sources
            if source in compact_result
        }
        if not compact_result:
            return None

    last_channel = state.get("traffic_source")
    if last_channel is None and len(compact_result) == 1 and len(mentioned_sources) <= 1:
        last_channel = next(iter(compact_result))

    return {
        "last_intent": state.get("intent"),
        "last_channel": last_channel,
        "last_compared_channels": mentioned_sources if len(mentioned_sources) > 1 else [],
        "last_metric_context": ANALYTICS_METRIC_CONTEXT_BY_TOOL.get(
            state.get("tool_name"),
            state.get("tool_name"),
        ),
        "last_period": state.get("date_range"),
        "last_tool_result": compact_result,
    }


def _compact_tool_result(
    tool_result: Any,
    *,
    fallback_source: str | None,
) -> dict[str, dict[str, int | float]]:
    """Keep only source-keyed metrics useful for analytics follow-ups."""

    if isinstance(tool_result, list):
        compact_rows = {}
        for row in tool_result:
            if not isinstance(row, dict):
                continue
            source = row.get("traffic_source")
            if not isinstance(source, str):
                continue
            compact_metrics = _compact_metric_row(row)
            if compact_metrics:
                compact_rows[source] = compact_metrics
        return compact_rows

    if isinstance(tool_result, dict):
        source = tool_result.get("traffic_source") or fallback_source
        if isinstance(source, str):
            compact_metrics = _compact_metric_row(tool_result)
            return {source: compact_metrics} if compact_metrics else {}

    return {}


def _compact_metric_row(row: dict[str, Any]) -> dict[str, int | float]:
    """Extract only numeric metrics needed by the next analytics turn."""

    compact_metrics = {}
    for metric in ANALYTICS_CONTEXT_METRICS:
        value = row.get(metric)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            compact_metrics[metric] = value
    return compact_metrics


def _is_bad_request_error(error: str) -> bool:
    """Identify controlled client-facing validation errors."""

    return _is_unsupported_traffic_source_error(error) or _is_invalid_date_range_error(
        error
    )


def _is_unsupported_traffic_source_error(error: str) -> bool:
    """Identify unsupported traffic source errors from repositories."""

    return "unsupported traffic_source" in error.lower()


def _is_invalid_date_range_error(error: str) -> bool:
    """Identify invalid date range errors from validation layers."""

    return "start_date must" in error.lower()


def _is_simple_greeting(question: str) -> bool:
    """Detect greetings that should not invoke the agent or tools."""

    return _normalize_question_text(question) in SIMPLE_GREETINGS


def _normalize_question_text(value: str) -> str:
    """Normalize punctuation, accents and whitespace for simple intent guards."""

    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^\w\s]", "", without_accents)
    return " ".join(without_punctuation.split())


def _parse_snapshot_datetime(value: str | None) -> datetime | None:
    """Parse a stored sync timestamp into a datetime."""

    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _compute_cache_age_minutes(snapshot_at: datetime | None) -> int | None:
    """Compute the age in minutes of the latest snapshot."""

    if snapshot_at is None:
        return None
    return max(0, int((datetime.now(UTC) - snapshot_at).total_seconds() // 60))
