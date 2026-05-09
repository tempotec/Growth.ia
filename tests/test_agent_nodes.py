"""Unit tests for Glacier AI agent nodes."""

from __future__ import annotations

from unittest.mock import Mock

from app.agent.nodes import (
    execute_tool,
    generate_answer,
    parse_question,
    route_to_tool,
)
from app.repositories.local_cache_repository import LocalCacheSnapshotNotFoundError
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


def test_parse_question_node_populates_state(valid_parsed_question_payload: dict) -> None:
    llm_service = Mock()
    llm_service.parse_question.return_value = ParsedQuestion(**valid_parsed_question_payload)

    history = [{"role": "assistant", "content": "Search teve 10 usuarios."}]
    result = parse_question(
        {
            "question": "E em fevereiro?",
            "conversation_history": history,
        },
        llm_service=llm_service,
    )

    assert result["intent"] == "traffic_volume_by_source"
    assert result["traffic_source"] == "Search"
    assert result["mentioned_traffic_sources"] == []
    assert result["error"] is None
    llm_service.parse_question.assert_called_once_with(
        "E em fevereiro?",
        conversation_history=history,
    )


def test_parse_question_resolves_contextual_user_winner_without_llm() -> None:
    llm_service = Mock()

    result = parse_question(
        {
            "question": "Qual deles trouxe mais usuarios?",
            "conversation_history": _comparison_history(),
        },
        llm_service=llm_service,
    )

    assert result["tool_name"] is None
    assert result["intent"] == "traffic_volume_by_source"
    assert result["mentioned_traffic_sources"] == ["Search", "Organic", "Display"]
    assert "Search trouxe mais usuarios" in result["answer"]
    assert "2.493" in result["answer"]
    assert "Facebook" not in result["answer"]
    llm_service.parse_question.assert_not_called()


def test_parse_question_resolves_contextual_conversion_winner_without_llm() -> None:
    llm_service = Mock()

    result = parse_question(
        {
            "question": "Qual deles teve a maior taxa de conversao?",
            "conversation_history": _comparison_history(),
        },
        llm_service=llm_service,
    )

    assert result["tool_name"] is None
    assert result["intent"] == "best_channel_performance"
    assert "Display teve a maior taxa de conversao" in result["answer"]
    assert "81,60%" in result["answer"]
    assert "Facebook" not in result["answer"]
    llm_service.parse_question.assert_not_called()


def test_parse_question_resolves_contextual_revenue_winner_without_llm() -> None:
    llm_service = Mock()

    result = parse_question(
        {
            "question": "Qual deles gerou mais receita?",
            "conversation_history": _comparison_history(),
        },
        llm_service=llm_service,
    )

    assert result["tool_name"] is None
    assert result["intent"] == "revenue_by_source"
    assert "Search gerou mais receita" in result["answer"]
    assert "R$ 622.593,80" in result["answer"]
    assert "Facebook" not in result["answer"]
    llm_service.parse_question.assert_not_called()


def test_parse_question_resolves_contextual_metric_breakdown_without_llm() -> None:
    llm_service = Mock()

    result = parse_question(
        {
            "question": "Separe por volume, conversao e receita.",
            "conversation_history": _comparison_history(),
        },
        llm_service=llm_service,
    )

    assert result["tool_name"] is None
    assert result["intent"] == "recommendation"
    assert "volume: Search lidera" in result["answer"]
    assert "conversao: Display lidera" in result["answer"]
    assert "receita: Search lidera" in result["answer"]
    llm_service.parse_question.assert_not_called()


def test_parse_question_resolves_contextual_priority_without_llm() -> None:
    llm_service = Mock()

    result = parse_question(
        {
            "question": "Entre eles, qual priorizar?",
            "conversation_history": _comparison_history(),
        },
        llm_service=llm_service,
    )

    assert result["tool_name"] is None
    assert result["intent"] == "recommendation"
    assert "priorizaria Search" in result["answer"]
    assert "maior receita" in result["answer"]
    assert "maior volume" in result["answer"]
    assert "Display" in result["answer"]
    llm_service.parse_question.assert_not_called()


def test_parse_question_node_returns_controlled_error_on_failure() -> None:
    llm_service = Mock()
    llm_service.parse_question.side_effect = Exception("boom")

    result = parse_question({"question": "Pergunta invalida"}, llm_service=llm_service)

    assert result["intent"] == "out_of_scope"
    assert result["tool_name"] is None
    assert result["answer"] is not None


def test_route_to_tool_maps_supported_intents(valid_parsed_question_payload: dict) -> None:
    parsed = ParsedQuestion(**valid_parsed_question_payload)

    traffic_result = route_to_tool(
        {
            "intent": "traffic_volume_by_source",
            "traffic_source": parsed.traffic_source,
            "date_range": parsed.date_range,
        }
    )
    revenue_result = route_to_tool(
        {
            "intent": "revenue_by_source",
            "date_range": parsed.date_range,
        }
    )
    performance_result = route_to_tool(
        {
            "intent": "best_channel_performance",
            "date_range": parsed.date_range,
        }
    )
    channel_result = route_to_tool(
        {
            "intent": "channel_performance_by_source",
            "traffic_source": parsed.traffic_source,
            "date_range": parsed.date_range,
        }
    )
    recommendation_channel_result = route_to_tool(
        {
            "intent": "recommendation",
            "traffic_source": parsed.traffic_source,
            "date_range": parsed.date_range,
        }
    )
    recommendation_summary_result = route_to_tool(
        {
            "intent": "recommendation",
            "date_range": parsed.date_range,
        }
    )

    assert traffic_result["tool_name"] == "get_users_by_source"
    assert revenue_result["tool_name"] == "get_revenue_by_source"
    assert performance_result["tool_name"] == "get_channel_performance_summary"
    assert channel_result["tool_name"] == "get_channel_performance_by_source"
    assert channel_result["tool_args"]["traffic_source"] == "Search"
    assert (
        recommendation_channel_result["tool_name"]
        == "get_channel_performance_by_source"
    )
    assert recommendation_channel_result["tool_args"]["traffic_source"] == "Search"
    assert recommendation_summary_result["tool_name"] == "get_channel_performance_summary"


def test_route_to_tool_requests_clarification_when_source_specific_intent_lacks_source() -> None:
    result = route_to_tool({"intent": "channel_performance_by_source"})

    assert result["intent"] == "out_of_scope"
    assert result["tool_name"] is None
    assert result["out_of_scope_reason"] == "needs_clarification"


def test_route_to_tool_skips_out_of_scope() -> None:
    result = route_to_tool({"intent": "out_of_scope"})

    assert result["tool_name"] is None
    assert result["tool_args"] == {}


def test_route_to_tool_skips_already_resolved_contextual_answer() -> None:
    result = route_to_tool(
        {
            "intent": "traffic_volume_by_source",
            "answer": "Entre Search e Organic, Search trouxe mais usuarios.",
        }
    )

    assert result["tool_name"] is None
    assert result["tool_args"] == {}


def test_execute_tool_calls_selected_tool() -> None:
    tool = Mock(return_value={"users": 10})

    result = execute_tool(
        {
            "tool_name": "get_users_by_source",
            "tool_args": {"traffic_source": "Search"},
        },
        tool_registry={"get_users_by_source": tool},
    )

    assert result["tool_result"] == {"users": 10}
    tool.assert_called_once_with(traffic_source="Search")


def test_execute_tool_filters_list_result_to_explicitly_mentioned_sources() -> None:
    tool = Mock(
        return_value=[
            {"traffic_source": "Facebook", "users": 200},
            {"traffic_source": "Search", "users": 1000},
            {"traffic_source": "Organic", "users": 500},
        ]
    )

    result = execute_tool(
        {
            "tool_name": "get_channel_performance_summary",
            "tool_args": {},
            "mentioned_traffic_sources": ["Search", "Organic"],
        },
        tool_registry={"get_channel_performance_summary": tool},
    )

    assert result["tool_result"] == [
        {"traffic_source": "Search", "users": 1000},
        {"traffic_source": "Organic", "users": 500},
    ]


def test_execute_tool_returns_controlled_error_on_failure() -> None:
    tool = Mock(side_effect=ValueError("source invalida"))

    result = execute_tool(
        {
            "tool_name": "get_users_by_source",
            "tool_args": {"traffic_source": "TikTok"},
        },
        tool_registry={"get_users_by_source": tool},
    )

    assert result["tool_result"] is None
    assert result["error"] == "source invalida"


def test_execute_tool_maps_missing_local_cache_snapshot_to_controlled_error() -> None:
    tool = Mock(side_effect=LocalCacheSnapshotNotFoundError("Run the cache sync first."))

    result = execute_tool(
        {
            "tool_name": "get_channel_performance_summary",
            "tool_args": {},
        },
        tool_registry={"get_channel_performance_summary": tool},
    )

    assert result["tool_result"] is None
    assert result["error"] == "local_cache_snapshot_not_found"
    assert result["answer"] == "Run the cache sync first."


def test_generate_answer_node_uses_llm_service() -> None:
    llm_service = Mock()
    llm_service.generate_answer.return_value = "Organic teve a melhor performance."

    result = generate_answer(
        {
            "question": "Qual canal teve melhor performance?",
            "intent": "best_channel_performance",
            "tool_result": [{"traffic_source": "Organic"}],
            "out_of_scope_reason": None,
        },
        llm_service=llm_service,
    )

    assert result["answer"] == "Organic teve a melhor performance."
    llm_service.generate_answer.assert_called_once_with(
        question="Qual canal teve melhor performance?",
        intent="best_channel_performance",
        tool_result=[{"traffic_source": "Organic"}],
        out_of_scope_reason=None,
        conversation_history=[],
    )


def test_generate_answer_node_preserves_existing_answer() -> None:
    llm_service = Mock()

    result = generate_answer(
        {
            "answer": "Pergunta fora do escopo atual da V1.",
        },
        llm_service=llm_service,
    )

    assert result["answer"] == "Pergunta fora do escopo atual da V1."
    llm_service.generate_answer.assert_not_called()
