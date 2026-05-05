"""FastAPI routes for Glacier AI V1."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.agent.graph import run_agent_question
from app.core.logging import get_logger, log_event, short_text
from app.schemas.api import AskRequest, AskResponse

router = APIRouter()
logger = get_logger(__name__)

OUT_OF_SCOPE_ERROR = "unsupported_intent"
OUT_OF_SCOPE_MESSAGE = (
    "Essa pergunta esta fora do escopo atual da V1. No momento, consigo responder "
    "apenas perguntas sobre volume de trafego por origem, receita por canal e "
    "melhor performance por canal."
)
GENERIC_INTERNAL_ERROR = "internal_error"
GENERIC_INTERNAL_MESSAGE = "Nao foi possivel processar a solicitacao no momento."


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    """Execute the Glacier AI agent for a validated question."""

    log_event(
        logger,
        logging.INFO,
        "ask_request_received",
        question_preview=short_text(payload.question),
    )
    try:
        final_state = run_agent_question(payload.question)
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "ask_request_failed",
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=GENERIC_INTERNAL_MESSAGE,
        ) from exc

    response, status_code = _build_response(final_state)
    log_event(
        logger,
        logging.INFO,
        "ask_request_completed",
        intent=final_state.get("intent"),
        tool_name=final_state.get("tool_name"),
        http_status=status_code,
        controlled_error=bool(response.error),
    )
    if status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status_code, detail=response.model_dump())
    return response


@router.get("/health")
def health() -> dict[str, str]:
    """Return a small healthcheck payload."""

    return {"status": "ok"}


def _build_response(state: dict) -> tuple[AskResponse, int]:
    """Translate the final agent state into the public HTTP response contract."""

    intent = state.get("intent")
    out_of_scope_reason = state.get("out_of_scope_reason")
    error = state.get("error")

    if intent == "out_of_scope" and out_of_scope_reason == OUT_OF_SCOPE_ERROR:
        response = AskResponse(
            answer=state.get("answer") or OUT_OF_SCOPE_MESSAGE,
            used_tool=None,
            data=None,
            error=OUT_OF_SCOPE_ERROR,
        )
        return response, status.HTTP_200_OK

    if error:
        response = AskResponse(
            answer=state.get("answer") or error,
            used_tool=state.get("tool_name"),
            data=state.get("tool_result"),
            error=error,
        )
        if _is_bad_request_error(error):
            return response, status.HTTP_400_BAD_REQUEST
        return response, status.HTTP_500_INTERNAL_SERVER_ERROR

    return (
        AskResponse(
            answer=state.get("answer") or "",
            used_tool=state.get("tool_name"),
            data=state.get("tool_result"),
            error=None,
        ),
        status.HTTP_200_OK,
    )


def _is_bad_request_error(error: str) -> bool:
    """Identify controlled client-facing validation errors."""

    lowered = error.lower()
    return "unsupported traffic_source" in lowered or "start_date must" in lowered
