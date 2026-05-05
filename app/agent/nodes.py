"""LangGraph nodes for Glacier AI V1."""

from __future__ import annotations

from typing import Callable

from app.agent.state import AgentState
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.llm_service import LLMService, LLMServiceError
from app.tools import TOOL_REGISTRY

ToolCallable = Callable[..., object]


def parse_question(
    state: AgentState,
    llm_service: LLMService | None = None,
) -> AgentState:
    """Parse the incoming question into structured agent state."""

    service = llm_service or LLMService()
    question = state["question"]

    try:
        parsed_question = service.parse_question(question)
    except (LLMServiceError, Exception):
        return {
            "intent": "out_of_scope",
            "tool_name": None,
            "tool_args": {},
            "tool_result": None,
            "error": "Nao foi possivel interpretar a pergunta de forma confiavel.",
            "answer": "Nao foi possivel interpretar a pergunta de forma confiavel.",
            "out_of_scope_reason": "parse_failure",
        }

    return {
        "parsed_question": parsed_question,
        "intent": parsed_question.intent,
        "traffic_source": parsed_question.traffic_source,
        "date_range": parsed_question.date_range,
        "out_of_scope_reason": parsed_question.out_of_scope_reason,
        "error": None,
        "answer": None,
    }


def route_to_tool(state: AgentState) -> AgentState:
    """Map a supported intent to a concrete tool invocation."""

    if state.get("intent") == "out_of_scope" or state.get("error"):
        return {"tool_name": None, "tool_args": {}}

    date_range = state.get("date_range")
    tool_args = {}
    if date_range is not None:
        tool_args["start_date"] = date_range.start_date
        tool_args["end_date"] = date_range.end_date

    intent = state.get("intent")
    if intent == "traffic_volume_by_source":
        tool_args["traffic_source"] = state.get("traffic_source")
        return {"tool_name": "get_users_by_source", "tool_args": tool_args}
    if intent == "revenue_by_source":
        return {"tool_name": "get_revenue_by_source", "tool_args": tool_args}
    if intent == "best_channel_performance":
        return {
            "tool_name": "get_channel_performance_summary",
            "tool_args": tool_args,
        }
    return {"tool_name": None, "tool_args": {}}


def execute_tool(
    state: AgentState,
    *,
    tool_registry: dict[str, ToolCallable] | None = None,
    repository: AnalyticsRepository | None = None,
) -> AgentState:
    """Execute the selected tool and persist its structured result."""

    tool_name = state.get("tool_name")
    if not tool_name:
        return {"tool_result": None}

    tools = tool_registry or TOOL_REGISTRY
    tool = tools[tool_name]
    tool_args = dict(state.get("tool_args", {}))
    if repository is not None:
        tool_args["repository"] = repository

    try:
        tool_result = tool(**tool_args)
    except Exception as exc:
        message = str(exc) or "Nao foi possivel consultar os dados solicitados."
        return {
            "tool_result": None,
            "error": message,
            "answer": message,
        }

    return {"tool_result": tool_result, "error": None}


def generate_answer(
    state: AgentState,
    llm_service: LLMService | None = None,
) -> AgentState:
    """Generate the final answer unless a controlled answer already exists."""

    if state.get("answer"):
        return {"answer": state["answer"]}

    service = llm_service or LLMService()
    try:
        answer = service.generate_answer(
            question=state["question"],
            intent=state.get("intent"),
            tool_result=state.get("tool_result"),
            out_of_scope_reason=state.get("out_of_scope_reason"),
        )
    except LLMServiceError:
        answer = "Nao foi possivel gerar a resposta final no momento."
        return {"answer": answer, "error": answer}

    return {"answer": answer}


def should_execute_tool(state: AgentState) -> str:
    """Decide whether the workflow should execute a data tool."""

    return "execute_tool" if state.get("tool_name") else "generate_answer"
