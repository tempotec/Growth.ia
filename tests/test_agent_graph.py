"""Unit tests for the Glacier AI LangGraph workflow."""

from __future__ import annotations

from unittest.mock import Mock

from app.agent.graph import build_agent_graph
from app.schemas.analytics import ParsedQuestion


def test_graph_skips_tool_execution_for_out_of_scope(valid_date_range_payload: dict[str, str]) -> None:
    llm_service = Mock()
    llm_service.parse_question.return_value = ParsedQuestion(
        intent="out_of_scope",
        traffic_source=None,
        date_range=valid_date_range_payload,
        needs_data=False,
        out_of_scope_reason="unsupported_intent",
    )
    llm_service.generate_answer.return_value = "Essa pergunta esta fora do escopo atual da V1."
    tool = Mock()
    graph = build_agent_graph(
        llm_service=llm_service,
        tool_registry={"get_users_by_source": tool},
    )

    result = graph.invoke({"question": "Me fale sobre CAC"})

    assert result["tool_name"] is None
    assert result["answer"] == "Essa pergunta esta fora do escopo atual da V1."
    tool.assert_not_called()


def test_graph_executes_tool_for_supported_intent(valid_parsed_question_payload: dict) -> None:
    llm_service = Mock()
    llm_service.parse_question.return_value = ParsedQuestion(**valid_parsed_question_payload)
    llm_service.generate_answer.return_value = "Search trouxe 1234 usuarios."
    tool = Mock(return_value={"traffic_source": "Search", "users": 1234})
    graph = build_agent_graph(
        llm_service=llm_service,
        tool_registry={"get_users_by_source": tool},
    )

    result = graph.invoke({"question": "Como foi Search no ultimo mes?"})

    assert result["tool_name"] == "get_users_by_source"
    assert result["tool_result"]["users"] == 1234
    assert result["answer"] == "Search trouxe 1234 usuarios."
    tool.assert_called_once()
