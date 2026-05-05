"""LangGraph assembly for Glacier AI V1."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    execute_tool,
    generate_answer,
    parse_question,
    route_to_tool,
    should_execute_tool,
)
from app.agent.state import AgentState
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.llm_service import LLMService
from app.tools import TOOL_REGISTRY


def build_agent_graph(
    *,
    llm_service: LLMService | None = None,
    repository: AnalyticsRepository | None = None,
    tool_registry: dict | None = None,
):
    """Build and compile the Glacier AI LangGraph workflow."""

    tools = tool_registry or TOOL_REGISTRY
    graph = StateGraph(AgentState)

    graph.add_node(
        "parse_question",
        lambda state: parse_question(state, llm_service=llm_service),
    )
    graph.add_node("route_to_tool", route_to_tool)
    graph.add_node(
        "execute_tool",
        lambda state: execute_tool(
            state,
            tool_registry=tools,
            repository=repository,
        ),
    )
    graph.add_node(
        "generate_answer",
        lambda state: generate_answer(state, llm_service=llm_service),
    )

    graph.add_edge(START, "parse_question")
    graph.add_edge("parse_question", "route_to_tool")
    graph.add_conditional_edges(
        "route_to_tool",
        should_execute_tool,
        {
            "execute_tool": "execute_tool",
            "generate_answer": "generate_answer",
        },
    )
    graph.add_edge("execute_tool", "generate_answer")
    graph.add_edge("generate_answer", END)
    return graph.compile()


@lru_cache
def get_agent_graph():
    """Return a cached compiled graph for the default runtime configuration."""

    return build_agent_graph()


def run_agent_question(question: str) -> AgentState:
    """Execute the compiled graph for a single natural-language question."""

    graph = get_agent_graph()
    return graph.invoke({"question": question})
