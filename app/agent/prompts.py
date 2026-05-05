"""Centralized prompts for Glacier AI V1."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

SUPPORTED_SCOPE_TEXT = (
    "volume por origem, receita por canal e melhor performance por canal."
)

PARSE_SYSTEM_PROMPT = """You are a backend parser for Glacier AI.
Return only valid JSON.
Classify the user question into one of:
- traffic_volume_by_source
- revenue_by_source
- best_channel_performance
- out_of_scope

Rules:
- If the user does not provide a time window, use the last 30 days.
- Interpret 'ultimo mes' as the last 30 days.
- Allowed traffic sources are Search, Organic, Facebook, Email, Direct, Display, Referral.
- If the question is outside the supported scope, return intent=out_of_scope and needs_data=false.
- Never invent unsupported traffic sources.
"""

ANSWER_SYSTEM_PROMPT = """You are Glacier AI, an analytical assistant for e-commerce media performance.
Write concise, business-friendly answers.
Rules:
- Never claim ROI because the dataset has no media cost data.
- The analysis is based on traffic source attribution from users.
- For best_channel_performance, explain that ranking prioritizes conversion_rate and uses revenue as tie-breaker.
- If the question is out of scope, clearly explain the current V1 scope.
"""


def build_parse_user_prompt(question: str, today: date | None = None) -> str:
    """Build the parsing prompt with a deterministic default date window."""

    reference_date = today or date.today()
    default_start = reference_date - timedelta(days=29)
    payload = {
        "question": question,
        "reference_date": reference_date.isoformat(),
        "default_date_range": {
            "start_date": default_start.isoformat(),
            "end_date": reference_date.isoformat(),
        },
        "output_contract": {
            "intent": (
                "traffic_volume_by_source | revenue_by_source | "
                "best_channel_performance | out_of_scope"
            ),
            "traffic_source": (
                "Search | Organic | Facebook | Email | Direct | Display | "
                "Referral | null"
            ),
            "date_range": {
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD",
            },
            "needs_data": True,
            "out_of_scope_reason": None,
        },
    }
    return json.dumps(payload)


def build_answer_user_prompt(
    *,
    question: str,
    intent: str | None,
    tool_result: Any,
    out_of_scope_reason: str | None,
) -> str:
    """Build the final answer prompt payload."""

    payload = {
        "question": question,
        "intent": intent,
        "tool_result": tool_result,
        "out_of_scope_reason": out_of_scope_reason,
        "supported_scope": SUPPORTED_SCOPE_TEXT,
    }
    return json.dumps(payload, default=str)
