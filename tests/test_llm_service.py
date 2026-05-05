"""Unit tests for the OpenAI-backed LLM service."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from app.services.llm_service import LLMService, LLMServiceError


def _build_chat_response(content: str) -> Mock:
    response = Mock()
    response.choices = [Mock(message=Mock(content=content))]
    return response


def test_llm_service_uses_default_openai_client(valid_env: dict[str, str]) -> None:
    mock_client = Mock()
    with patch(
        "app.services.llm_service.OpenAI",
        return_value=mock_client,
    ) as mock_openai:
        service = LLMService()

    mock_openai.assert_called_once_with(api_key=valid_env["OPENAI_API_KEY"])
    assert service._client is mock_client
    assert service._model == valid_env["OPENAI_MODEL"]


def test_parse_question_returns_validated_parsed_question() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _build_chat_response(
        json.dumps(
            {
                "intent": "traffic_volume_by_source",
                "traffic_source": "Search",
                "date_range": {
                    "start_date": "2026-04-01",
                    "end_date": "2026-04-30",
                },
                "needs_data": True,
                "out_of_scope_reason": None,
            }
        )
    )
    service = LLMService(client=client, model="test-model")

    result = service.parse_question("Como foi o volume de Search?")

    assert result.intent == "traffic_volume_by_source"
    assert result.traffic_source == "Search"


def test_parse_question_raises_controlled_error_for_invalid_payload() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _build_chat_response("not-json")
    service = LLMService(client=client, model="test-model")

    with pytest.raises(LLMServiceError):
        service.parse_question("Pergunta invalida")


def test_generate_answer_returns_trimmed_content() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _build_chat_response("  Resposta final.  ")
    service = LLMService(client=client, model="test-model")

    answer = service.generate_answer(
        question="Qual canal teve melhor performance?",
        intent="best_channel_performance",
        tool_result=[{"traffic_source": "Organic"}],
        out_of_scope_reason=None,
    )

    assert answer == "Resposta final."


def test_generate_answer_raises_controlled_error_when_completion_fails() -> None:
    client = Mock()
    client.chat.completions.create.side_effect = RuntimeError("boom")
    service = LLMService(client=client, model="test-model")

    with pytest.raises(LLMServiceError):
        service.generate_answer(
            question="Qual canal teve melhor performance?",
            intent="best_channel_performance",
            tool_result=[],
            out_of_scope_reason=None,
        )
