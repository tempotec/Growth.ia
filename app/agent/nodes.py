"""LangGraph nodes for Glacier AI V1."""

from __future__ import annotations

import logging
from typing import Callable

from app.agent.answer_style import detect_answer_style, limit_sentences
from app.agent.contextual_followup import resolve_contextual_followup
from app.agent.performance_answer import build_best_performance_answer
from app.agent.scope_fallback import resolve_scope_fallback
from app.agent.state import AgentState
from app.core.logging import elapsed_ms, get_logger, log_event, start_timer
from app.repositories.local_cache_repository import LocalCacheSnapshotNotFoundError
from app.services.analytics_read_service import AnalyticsReadService
from app.services.llm_service import LLMService, LLMServiceError
from app.tools import TOOL_REGISTRY

ToolCallable = Callable[..., object]
logger = get_logger(__name__)


def parse_question(
    state: AgentState,
    llm_service: LLMService | None = None,
) -> AgentState:
    """Parse the incoming question into structured agent state."""

    question = state["question"]
    conversation_history = state.get("conversation_history", [])
    answer_style = detect_answer_style(question)
    scope_fallback = resolve_scope_fallback(question, conversation_history)
    if scope_fallback is not None:
        return {**scope_fallback, **answer_style}

    contextual_followup = resolve_contextual_followup(question, conversation_history)
    if contextual_followup is not None:
        return {**contextual_followup, **answer_style}

    service = llm_service or LLMService()
    try:
        parsed_question = service.parse_question(
            question,
            conversation_history=conversation_history,
        )
    except (LLMServiceError, Exception):
        return {
            "intent": "out_of_scope",
            "tool_name": None,
            "tool_args": {},
            "tool_result": None,
            "error": "Nao foi possivel interpretar a pergunta de forma confiavel.",
            "answer": "Nao foi possivel interpretar a pergunta de forma confiavel.",
            "out_of_scope_reason": "parse_failure",
            **answer_style,
        }

    return {
        "parsed_question": parsed_question,
        "intent": parsed_question.intent,
        "traffic_source": parsed_question.traffic_source,
        "mentioned_traffic_sources": parsed_question.mentioned_traffic_sources,
        "date_range": parsed_question.date_range,
        "out_of_scope_reason": parsed_question.out_of_scope_reason,
        "error": None,
        "answer": None,
        **answer_style,
    }


def route_to_tool(state: AgentState) -> AgentState:
    """Map a supported intent to a concrete tool invocation."""

    if state.get("answer"):
        return {"tool_name": None, "tool_args": {}}

    if state.get("intent") == "out_of_scope" or state.get("error"):
        return {"tool_name": None, "tool_args": {}}

    date_range = state.get("date_range")
    tool_args = {}
    if date_range is not None:
        tool_args["start_date"] = date_range.start_date
        tool_args["end_date"] = date_range.end_date

    intent = state.get("intent")
    if intent == "traffic_volume_by_source":
        if not state.get("traffic_source"):
            return {
                "intent": "out_of_scope",
                "out_of_scope_reason": "needs_clarification",
                "tool_name": None,
                "tool_args": {},
            }
        tool_args["traffic_source"] = state.get("traffic_source")
        return {"tool_name": "get_users_by_source", "tool_args": tool_args}
    if intent == "revenue_by_source":
        return {"tool_name": "get_revenue_by_source", "tool_args": tool_args}
    if intent == "best_channel_performance":
        return {
            "tool_name": "get_channel_performance_summary",
            "tool_args": tool_args,
        }
    if intent == "channel_performance_by_source":
        if not state.get("traffic_source"):
            return {
                "intent": "out_of_scope",
                "out_of_scope_reason": "needs_clarification",
                "tool_name": None,
                "tool_args": {},
            }
        tool_args["traffic_source"] = state.get("traffic_source")
        return {
            "tool_name": "get_channel_performance_by_source",
            "tool_args": tool_args,
        }
    if intent == "recommendation":
        if state.get("traffic_source"):
            tool_args["traffic_source"] = state.get("traffic_source")
            return {
                "tool_name": "get_channel_performance_by_source",
                "tool_args": tool_args,
            }
        return {
            "tool_name": "get_channel_performance_summary",
            "tool_args": tool_args,
        }
    return {"tool_name": None, "tool_args": {}}


def execute_tool(
    state: AgentState,
    *,
    tool_registry: dict[str, ToolCallable] | None = None,
    repository: AnalyticsReadService | None = None,
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
    except LocalCacheSnapshotNotFoundError as exc:
        return {
            "tool_result": None,
            "error": "local_cache_snapshot_not_found",
            "answer": str(exc),
        }
    except Exception as exc:
        message = str(exc) or "Nao foi possivel consultar os dados solicitados."
        return {
            "tool_result": None,
            "error": message,
            "answer": message,
        }

    filtered_tool_result = _filter_tool_result_to_mentioned_sources(
        tool_result,
        state.get("mentioned_traffic_sources", []),
    )
    return {"tool_result": filtered_tool_result, "error": None}


def generate_answer(
    state: AgentState,
    llm_service: LLMService | None = None,
) -> AgentState:
    """Generate the final answer unless a controlled answer already exists."""

    if state.get("answer"):
        answer = limit_sentences(state["answer"], state.get("max_sentences"))
        return {"answer": answer}

    if state.get("intent") == "best_channel_performance":
        performance_answer = build_best_performance_answer(
            state.get("tool_result"),
            short_answer=bool(state.get("short_answer")),
        )
        if performance_answer is not None:
            answer = limit_sentences(performance_answer, state.get("max_sentences"))
            return {"answer": answer}

    service = llm_service or LLMService()
    try:
        answer_kwargs = {
            "question": state["question"],
            "intent": state.get("intent"),
            "tool_result": state.get("tool_result"),
            "out_of_scope_reason": state.get("out_of_scope_reason"),
            "conversation_history": state.get("conversation_history", []),
        }
        if state.get("short_answer"):
            answer_kwargs.update(
                {
                    "short_answer": True,
                    "max_sentences": state.get("max_sentences"),
                    "use_default_answer_structure": state.get(
                        "use_default_answer_structure",
                        False,
                    ),
                }
            )
        answer = service.generate_answer(**answer_kwargs)
    except LLMServiceError:
        answer = "Nao foi possivel gerar a resposta final no momento."
        return {"answer": answer, "error": answer}

    answer = limit_sentences(answer, state.get("max_sentences"))
    return {"answer": answer}


def reflect_answer(
    state: AgentState,
    llm_service: LLMService | None = None,
) -> AgentState:
    """Critique the generated answer internally for thinking mode."""

    initial_answer = state.get("answer") or ""
    if not initial_answer:
        return {
            "initial_answer": initial_answer,
            "reflection_used": False,
            "fallback_used": True,
            "reflection_error": "missing_initial_answer",
        }

    service = llm_service or LLMService()
    request_start = start_timer()
    try:
        critique = service.reflect_answer(
            question=state["question"],
            intent=state.get("intent"),
            tool_result=state.get("tool_result"),
            initial_answer=initial_answer,
            conversation_history=state.get("conversation_history", []),
        )
    except (LLMServiceError, Exception) as exc:
        reflection_time_ms = elapsed_ms(request_start)
        log_event(
            logger,
            logging.WARNING,
            "agent_reflection_failed",
            intent=state.get("intent"),
            duration_ms=reflection_time_ms,
        )
        return {
            "initial_answer": initial_answer,
            "reflection_used": False,
            "fallback_used": True,
            "reflection_error": str(exc),
            "reflection_time_ms": reflection_time_ms,
            "answer": initial_answer,
        }

    reflection_time_ms = elapsed_ms(request_start)
    return {
        "initial_answer": initial_answer,
        "critique": critique,
        "reflection_score": critique.get("score"),
        "reflection_time_ms": reflection_time_ms,
        "reflection_error": None,
    }


def revise_answer(
    state: AgentState,
    llm_service: LLMService | None = None,
) -> AgentState:
    """Revise the answer once using the internal critique."""

    initial_answer = state.get("initial_answer") or state.get("answer") or ""
    critique = state.get("critique")
    if not initial_answer or not critique:
        return {
            "answer": initial_answer,
            "reflection_used": False,
            "fallback_used": True,
            "reflection_error": "missing_critique",
        }

    service = llm_service or LLMService()
    try:
        revised_answer = service.revise_answer(
            question=state["question"],
            intent=state.get("intent"),
            tool_result=state.get("tool_result"),
            initial_answer=initial_answer,
            critique=critique,
            conversation_history=state.get("conversation_history", []),
        )
    except (LLMServiceError, Exception) as exc:
        log_event(
            logger,
            logging.WARNING,
            "agent_revision_failed",
            intent=state.get("intent"),
            reflection_score=state.get("reflection_score"),
        )
        return {
            "answer": initial_answer,
            "reflection_used": False,
            "fallback_used": True,
            "reflection_error": str(exc),
        }

    revised_answer = limit_sentences(revised_answer, state.get("max_sentences"))
    return {
        "answer": revised_answer,
        "reflection_used": True,
        "fallback_used": False,
        "reflection_error": None,
    }


def should_execute_tool(state: AgentState) -> str:
    """Decide whether the workflow should execute a data tool."""

    return "execute_tool" if state.get("tool_name") else "generate_answer"


def should_reflect(state: AgentState) -> str:
    """Decide whether the workflow should run the optional reflection pass."""

    if not state.get("thinking_mode"):
        return "end"
    if state.get("error"):
        return "end"
    if not state.get("answer"):
        return "end"
    return "reflect_answer"


def should_revise(state: AgentState) -> str:
    """Decide whether a critique is available for answer revision."""

    return "revise_answer" if state.get("critique") else "end"


def _filter_tool_result_to_mentioned_sources(
    tool_result: object,
    mentioned_traffic_sources: list[str],
) -> object:
    """Limit list results to channels explicitly mentioned by the user."""

    if len(mentioned_traffic_sources) <= 1 or not isinstance(tool_result, list):
        return tool_result

    allowed_sources = set(mentioned_traffic_sources)
    return [
        row
        for row in tool_result
        if isinstance(row, dict) and row.get("traffic_source") in allowed_sources
    ]
