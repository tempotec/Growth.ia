"""Unit tests for the Glacier AI LangGraph workflow."""

from __future__ import annotations

from unittest.mock import Mock

from app.agent.graph import build_agent_graph
from app.schemas.analytics import ParsedQuestion


def _comparison_history() -> list[dict]:
    return [
        {
            "role": "assistant",
            "content": "Comparei Search, Organic e Display.",
            "analytics_context": {
                "last_intent": "best_channel_performance",
                "last_channel": None,
                "last_compared_channels": ["Search", "Organic", "Display"],
                "last_metric_context": "channel_performance_summary",
                "last_period": {
                    "start_date": "2026-04-10",
                    "end_date": "2026-05-09",
                },
                "last_tool_result": {
                    "Search": {
                        "users": 2493,
                        "converted_users": 1984,
                        "orders": 3094,
                        "revenue": 622593.8,
                        "conversion_rate": 0.7958,
                    },
                    "Organic": {
                        "users": 534,
                        "converted_users": 420,
                        "orders": 650,
                        "revenue": 135000,
                        "conversion_rate": 0.787,
                    },
                    "Display": {
                        "users": 141,
                        "converted_users": 115,
                        "orders": 160,
                        "revenue": 36000,
                        "conversion_rate": 0.816,
                    },
                },
            },
        }
    ]


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


def test_graph_resolves_contextual_followup_without_tool_or_llm() -> None:
    llm_service = Mock()
    tool = Mock()
    graph = build_agent_graph(
        llm_service=llm_service,
        tool_registry={"get_channel_performance_summary": tool},
    )

    result = graph.invoke(
        {
            "question": "Qual deles trouxe mais usuarios?",
            "conversation_history": _comparison_history(),
        }
    )

    assert result["tool_name"] is None
    assert result["answer"].startswith("Entre Search, Organic e Display, Search")
    assert result["analytics_context"]["last_compared_channels"] == [
        "Search",
        "Organic",
        "Display",
    ]
    tool.assert_not_called()
    llm_service.parse_question.assert_not_called()
    llm_service.generate_answer.assert_not_called()
