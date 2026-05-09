"""Unit tests for API schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.api import AskRequest, AskResponse, ConversationMessage


def test_ask_request_accepts_valid_question(
    valid_ask_request_payload: dict[str, str],
) -> None:
    request = AskRequest(**valid_ask_request_payload)

    assert request.question == valid_ask_request_payload["question"]


def test_ask_request_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        AskRequest(question="")


def test_ask_request_accepts_conversation_history() -> None:
    request = AskRequest(
        question="E em fevereiro e marco?",
        conversation_history=[
            {
                "role": "assistant",
                "content": "Search teve 2478 usuarios nos ultimos 30 dias.",
                "intent": "traffic_volume_by_source",
                "traffic_source": "Search",
                "date_range": {
                    "start_date": "2026-04-08",
                    "end_date": "2026-05-07",
                },
            }
        ],
    )

    assert len(request.conversation_history) == 1
    assert request.conversation_history[0].traffic_source == "Search"


def test_conversation_message_rejects_system_role() -> None:
    with pytest.raises(ValidationError):
        ConversationMessage(role="system", content="hidden context")


def test_ask_response_accepts_used_tool_payload(
    valid_ask_response_payload: dict,
) -> None:
    response = AskResponse(**valid_ask_response_payload)

    assert response.used_tool == "get_channel_performance_summary"
    assert response.error is None


def test_ask_response_accepts_out_of_scope_payload() -> None:
    response = AskResponse(
        answer="Essa pergunta esta fora do escopo atual da V1.",
        used_tool=None,
        data=None,
        error="unsupported_intent",
    )

    assert response.used_tool is None
    assert response.data is None
    assert response.error == "unsupported_intent"


def test_ask_response_accepts_parse_metadata() -> None:
    response = AskResponse(
        answer="Search trouxe usuarios no periodo.",
        used_tool="get_users_by_source",
        data={"users": 10},
        error=None,
        intent="traffic_volume_by_source",
        traffic_source="Search",
        date_range={
            "start_date": "2026-02-01",
            "end_date": "2026-03-31",
        },
    )

    assert response.intent == "traffic_volume_by_source"
    assert response.traffic_source == "Search"
    assert response.date_range is not None
