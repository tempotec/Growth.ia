"""Shared agent state for Glacier AI V1."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from app.schemas.analytics import DateRange, ParsedQuestion, SupportedIntent


class AgentState(TypedDict, total=False):
    """State shared across the LangGraph workflow."""

    question: str
    conversation_history: list[dict[str, Any]]
    parsed_question: ParsedQuestion | None
    intent: SupportedIntent | None
    traffic_source: str | None
    mentioned_traffic_sources: list[str]
    date_range: DateRange | None
    tool_name: str | None
    tool_args: dict[str, Any]
    tool_result: Any
    answer: str | None
    error: str | None
    out_of_scope_reason: str | None
    analytics_context: dict[str, Any] | None
