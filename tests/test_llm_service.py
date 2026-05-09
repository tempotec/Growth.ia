"""Unit tests for the OpenAI-backed LLM service."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest

from app.agent.prompts import (
    ANSWER_SYSTEM_PROMPT,
    PARSE_SYSTEM_PROMPT,
    build_answer_user_prompt,
    build_parse_user_prompt,
)
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


def test_parse_question_includes_conversation_history_in_prompt() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _build_chat_response(
        json.dumps(
            {
                "intent": "traffic_volume_by_source",
                "traffic_source": "Search",
                "date_range": {
                    "start_date": "2026-02-01",
                    "end_date": "2026-03-31",
                },
                "needs_data": True,
                "out_of_scope_reason": None,
            }
        )
    )
    service = LLMService(client=client, model="test-model")
    history = [
        {
            "role": "assistant",
            "content": "Search teve 2478 usuarios nos ultimos 30 dias.",
            "intent": "traffic_volume_by_source",
            "traffic_source": "Search",
            "date_range": {
                "start_date": "2026-04-08",
                "end_date": "2026-05-07",
            },
            "analytics_context": {
                "last_intent": "traffic_volume_by_source",
                "last_channel": "Search",
                "last_compared_channels": [],
                "last_metric_context": "users_by_source",
                "last_period": {
                    "start_date": "2026-04-08",
                    "end_date": "2026-05-07",
                },
                "last_tool_result": {
                    "Search": {
                        "users": 2478,
                    }
                },
            },
        }
    ]

    service.parse_question("E em fevereiro e marco?", conversation_history=history)

    messages = client.chat.completions.create.call_args.kwargs["messages"]
    prompt_payload = json.loads(messages[1]["content"])
    assert prompt_payload["conversation_history"][0]["traffic_source"] == "Search"
    assert prompt_payload["conversation_history"][0]["intent"] == "traffic_volume_by_source"
    assert (
        prompt_payload["conversation_history"][0]["analytics_context"][
            "last_tool_result"
        ]["Search"]["users"]
        == 2478
    )


def test_parse_question_prioritizes_channel_performance_for_short_source_followup() -> None:
    client = Mock()
    service = LLMService(client=client, model="test-model")
    history = [
        {
            "role": "assistant",
            "content": "Direct e Referral tem baixo desempenho no periodo.",
            "intent": "best_channel_performance",
            "traffic_source": None,
            "date_range": {
                "start_date": "2026-04-08",
                "end_date": "2026-05-07",
            },
        }
    ]

    result = service.parse_question(
        "e o Facebook nesse periodo?",
        conversation_history=history,
    )

    assert result.intent == "channel_performance_by_source"
    assert result.traffic_source == "Facebook"
    assert result.date_range.start_date.isoformat() == "2026-04-08"
    assert result.date_range.end_date.isoformat() == "2026-05-07"
    client.chat.completions.create.assert_not_called()


def test_parse_question_prioritizes_channel_performance_for_source_data_month() -> None:
    client = Mock()
    service = LLMService(client=client, model="test-model")

    result = service.parse_question("me mostra os dados do Search em marco")

    assert result.intent == "channel_performance_by_source"
    assert result.traffic_source == "Search"
    assert result.date_range.start_date.isoformat() == f"{date.today().year}-03-01"
    assert result.date_range.end_date.isoformat() == f"{date.today().year}-03-31"
    client.chat.completions.create.assert_not_called()


def test_parse_question_detects_multiple_sources_for_explicit_comparison() -> None:
    client = Mock()
    service = LLMService(client=client, model="test-model")

    result = service.parse_question("Compare Facebook e Search")

    assert result.intent == "best_channel_performance"
    assert result.traffic_source is None
    assert result.mentioned_traffic_sources == ["Facebook", "Search"]
    client.chat.completions.create.assert_not_called()


def test_parse_question_detects_multiple_sources_after_entre() -> None:
    client = Mock()
    service = LLMService(client=client, model="test-model")

    result = service.parse_question("Entre Search, Organic e Display, compare os canais")

    assert result.intent == "best_channel_performance"
    assert result.traffic_source is None
    assert result.mentioned_traffic_sources == ["Search", "Organic", "Display"]
    client.chat.completions.create.assert_not_called()


def test_parse_question_overrides_llm_payload_with_detected_multiple_sources() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _build_chat_response(
        json.dumps(
            {
                "intent": "channel_performance_by_source",
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

    result = service.parse_question("Dados de Search e Organic")

    assert result.intent == "best_channel_performance"
    assert result.traffic_source is None
    assert result.mentioned_traffic_sources == ["Search", "Organic"]


def test_parse_question_resolves_recommendation_from_recent_channel_context() -> None:
    client = Mock()
    service = LLMService(client=client, model="test-model")
    history = [
        {
            "role": "assistant",
            "content": "Display teve baixa conversao no periodo.",
            "intent": "channel_performance_by_source",
            "traffic_source": "Display",
            "date_range": {
                "start_date": "2026-04-09",
                "end_date": "2026-05-08",
            },
        }
    ]

    result = service.parse_question(
        "O que voce investigaria antes de tomar uma decisao?",
        conversation_history=history,
    )

    assert result.intent == "recommendation"
    assert result.traffic_source == "Display"
    expected_end_date = date.today()
    expected_start_date = expected_end_date - timedelta(days=29)
    assert result.date_range.start_date == expected_start_date
    assert result.date_range.end_date == expected_end_date
    client.chat.completions.create.assert_not_called()


def test_parse_question_resolves_contextual_business_followup_as_recommendation() -> None:
    client = Mock()
    service = LLMService(client=client, model="test-model")
    history = [
        {
            "role": "assistant",
            "content": "Search liderou em receita no periodo.",
            "intent": "best_channel_performance",
            "traffic_source": "Search",
            "date_range": {
                "start_date": "2026-04-09",
                "end_date": "2026-05-08",
            },
        }
    ]

    result = service.parse_question(
        "Ele teve mais trafego, mais receita ou melhor conversao?",
        conversation_history=history,
    )

    assert result.intent == "recommendation"
    assert result.traffic_source == "Search"
    client.chat.completions.create.assert_not_called()


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


def test_answer_prompt_enforces_pt_br_and_business_guidance() -> None:
    payload = json.loads(
        build_answer_user_prompt(
            question="Como foi o volume de Search?",
            intent="traffic_volume_by_source",
            tool_result={"traffic_source": "Search", "users": 2460},
            out_of_scope_reason=None,
        )
    )

    assert "português do Brasil" in ANSWER_SYSTEM_PROMPT
    assert "Nunca responda em inglês" in ANSWER_SYSTEM_PROMPT
    assert "transformar dados de performance em insight acionável" in ANSWER_SYSTEM_PROMPT
    assert payload["response_guidance"]["language"] == "pt-BR"
    assert "não inventar dados que a tool não retornou" in payload["response_guidance"]["business_rules"]


def test_parse_prompt_uses_supported_out_of_scope_contract() -> None:
    assert "Regras de prioridade" in PARSE_SYSTEM_PROMPT
    assert "out_of_scope_reason=unsupported_intent" in PARSE_SYSTEM_PROMPT
    assert "channel_performance_by_source" in PARSE_SYSTEM_PROMPT
    assert "recommendation" in PARSE_SYSTEM_PROMPT
    assert "mentioned_traffic_sources" in PARSE_SYSTEM_PROMPT
    assert "dados" in PARSE_SYSTEM_PROMPT
    assert "e o Facebook" in PARSE_SYSTEM_PROMPT
    assert "março" in PARSE_SYSTEM_PROMPT
    assert "conversation_history" in PARSE_SYSTEM_PROMPT
    assert "out_of_scope_reason=needs_clarification" in PARSE_SYSTEM_PROMPT


def test_build_parse_prompt_limits_recent_history() -> None:
    history = [
        {"role": "user", "content": f"Pergunta {index}"}
        for index in range(12)
    ]

    payload = json.loads(
        build_parse_user_prompt(
            "E fevereiro?",
            today=date(2026, 5, 7),
            conversation_history=history,
        )
    )

    assert len(payload["conversation_history"]) == 10
    assert payload["conversation_history"][0]["content"] == "Pergunta 2"
    assert "mentioned_traffic_sources" in payload["output_contract"]


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


def test_validate_connectivity_returns_model_reply() -> None:
    client = Mock()
    client.chat.completions.create.return_value = _build_chat_response("OK")
    service = LLMService(client=client, model="test-model")

    result = service.validate_connectivity()

    assert result == "OK"


def test_parse_question_emits_observability_logs(caplog) -> None:
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

    with caplog.at_level(logging.INFO):
        service.parse_question("Como foi o volume de Search?")

    log_text = " ".join(caplog.messages)
    assert "event=llm_parse_started" in log_text
    assert "event=llm_parse_completed" in log_text
