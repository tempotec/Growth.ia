"""Deterministic analytics follow-up resolution."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

METRICS = ("users", "converted_users", "orders", "revenue", "conversion_rate")
VOLUME_TERMS = ("usuario", "usuarios", "trafego", "volume")
CONVERSION_TERMS = ("conversao", "converter", "converteu", "taxa de conversao")
REVENUE_TERMS = ("receita", "faturamento", "dinheiro")
PRIORITY_TERMS = ("priorizar", "prioridade", "investir")
CONTEXT_REFERENCE_TERMS = (
    "qual deles",
    "entre eles",
    "desses canais",
    "destes canais",
    "qual desses",
    "qual destes",
)


def resolve_contextual_followup(
    question: str,
    conversation_history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Answer metric follow-ups from the latest structured analytics context."""

    analytics_context = _latest_analytics_context(conversation_history)
    if analytics_context is None:
        return None

    rows = _context_rows(analytics_context)
    if not rows:
        return None

    normalized_question = _normalize_text(question)
    channels = _context_channels(analytics_context, rows)
    if not channels:
        return None

    if _looks_like_metric_breakdown(normalized_question):
        answer = _build_metric_breakdown_answer(channels, rows)
        if answer is None:
            return None
        return _build_resolved_state(
            analytics_context=analytics_context,
            channels=channels,
            intent="recommendation",
            answer=answer,
        )

    if _looks_like_priority_followup(normalized_question):
        answer = _build_priority_answer(channels, rows)
        if answer is None:
            return None
        return _build_resolved_state(
            analytics_context=analytics_context,
            channels=channels,
            intent="recommendation",
            answer=answer,
        )

    if not _has_context_reference(normalized_question):
        return None

    metric = _requested_metric(normalized_question)
    if metric is None:
        return None

    answer = _build_metric_winner_answer(channels, rows, metric)
    if answer is None:
        return None

    return _build_resolved_state(
        analytics_context=analytics_context,
        channels=channels,
        intent=_intent_for_metric(metric),
        answer=answer,
    )


def _latest_analytics_context(
    conversation_history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the latest analytics_context from recent chat history."""

    for message in reversed(conversation_history[-10:]):
        analytics_context = message.get("analytics_context")
        if isinstance(analytics_context, dict):
            return analytics_context
    return None


def _context_rows(analytics_context: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Normalize last_tool_result into source-keyed numeric metric rows."""

    tool_result = analytics_context.get("last_tool_result")
    if not isinstance(tool_result, dict):
        return {}

    rows: dict[str, dict[str, float]] = {}
    for source, metrics in tool_result.items():
        if not isinstance(source, str) or not isinstance(metrics, dict):
            continue

        numeric_metrics = {}
        for metric in METRICS:
            value = metrics.get(metric)
            if isinstance(value, bool):
                continue
            if isinstance(value, int | float):
                numeric_metrics[metric] = float(value)

        if numeric_metrics:
            rows[source] = numeric_metrics

    return rows


def _context_channels(
    analytics_context: dict[str, Any],
    rows: dict[str, dict[str, float]],
) -> list[str]:
    """Return the channel scope, preferring the explicit compared group."""

    compared_channels = analytics_context.get("last_compared_channels")
    if isinstance(compared_channels, list) and compared_channels:
        return [
            source
            for source in compared_channels
            if isinstance(source, str) and source in rows
        ]
    return list(rows.keys())


def _build_resolved_state(
    *,
    analytics_context: dict[str, Any],
    channels: list[str],
    intent: str,
    answer: str,
) -> dict[str, Any]:
    """Return an AgentState patch for a fully resolved follow-up."""

    return {
        "intent": intent,
        "traffic_source": None,
        "mentioned_traffic_sources": channels if len(channels) > 1 else [],
        "date_range": analytics_context.get("last_period"),
        "analytics_context": analytics_context,
        "tool_name": None,
        "tool_args": {},
        "tool_result": None,
        "error": None,
        "answer": answer,
        "out_of_scope_reason": None,
    }


def _looks_like_metric_breakdown(normalized_question: str) -> bool:
    """Detect requests to split the same context by key business metrics."""

    return (
        any(term in normalized_question for term in ("separe", "separa", "separar"))
        and any(term in normalized_question for term in VOLUME_TERMS)
        and any(term in normalized_question for term in CONVERSION_TERMS)
        and any(term in normalized_question for term in REVENUE_TERMS)
    )


def _looks_like_priority_followup(normalized_question: str) -> bool:
    """Detect contextual priority questions for a previously compared group."""

    return any(term in normalized_question for term in PRIORITY_TERMS) and (
        _has_context_reference(normalized_question)
        or "canal" in normalized_question
        or "canais" in normalized_question
    )


def _has_context_reference(normalized_question: str) -> bool:
    """Detect pronouns that must reuse the previous compared channel group."""

    return any(term in normalized_question for term in CONTEXT_REFERENCE_TERMS)


def _requested_metric(normalized_question: str) -> str | None:
    """Map a contextual follow-up question to the requested metric."""

    if any(term in normalized_question for term in REVENUE_TERMS):
        return "revenue"
    if any(term in normalized_question for term in CONVERSION_TERMS):
        return "conversion_rate"
    if any(term in normalized_question for term in VOLUME_TERMS):
        return "users"
    return None


def _intent_for_metric(metric: str) -> str:
    """Choose response metadata intent for a deterministic metric answer."""

    if metric == "users":
        return "traffic_volume_by_source"
    if metric == "revenue":
        return "revenue_by_source"
    return "best_channel_performance"


def _build_metric_winner_answer(
    channels: list[str],
    rows: dict[str, dict[str, float]],
    metric: str,
) -> str | None:
    """Build a concise deterministic answer for a metric winner."""

    winner = _metric_winner(channels, rows, metric)
    if winner is None:
        return None

    channel, value = winner
    group = _format_channel_group(channels)
    if metric == "users":
        return (
            f"Entre {group}, {channel} trouxe mais usuarios, "
            f"com {_format_integer(value)} usuarios."
        )
    if metric == "conversion_rate":
        return (
            f"Entre {group}, {channel} teve a maior taxa de conversao, "
            f"com {_format_percentage(value)}."
        )
    if metric == "revenue":
        return (
            f"Entre {group}, {channel} gerou mais receita, "
            f"com {_format_currency(value)}."
        )
    return None


def _build_metric_breakdown_answer(
    channels: list[str],
    rows: dict[str, dict[str, float]],
) -> str | None:
    """Build a deterministic summary split by volume, conversion and revenue."""

    volume = _metric_winner(channels, rows, "users")
    conversion = _metric_winner(channels, rows, "conversion_rate")
    revenue = _metric_winner(channels, rows, "revenue")
    if volume is None and conversion is None and revenue is None:
        return None

    group = _format_channel_group(channels)
    parts = []
    if volume is not None:
        parts.append(
            f"volume: {volume[0]} lidera com {_format_integer(volume[1])} usuarios"
        )
    if conversion is not None:
        parts.append(
            f"conversao: {conversion[0]} lidera com {_format_percentage(conversion[1])}"
        )
    if revenue is not None:
        parts.append(
            f"receita: {revenue[0]} lidera com {_format_currency(revenue[1])}"
        )

    return f"Entre {group}, " + "; ".join(parts) + "."


def _build_priority_answer(
    channels: list[str],
    rows: dict[str, dict[str, float]],
) -> str | None:
    """Choose a priority channel using revenue first, then scale and efficiency."""

    revenue = _metric_winner(channels, rows, "revenue")
    volume = _metric_winner(channels, rows, "users")
    conversion = _metric_winner(channels, rows, "conversion_rate")
    primary = revenue or volume or conversion
    if primary is None:
        return None

    channel = primary[0]
    reasons = []
    if revenue is not None and revenue[0] == channel:
        reasons.append(f"maior receita ({_format_currency(revenue[1])})")
    if volume is not None and volume[0] == channel:
        reasons.append(f"maior volume ({_format_integer(volume[1])} usuarios)")
    if conversion is not None and conversion[0] == channel:
        reasons.append(f"maior conversao ({_format_percentage(conversion[1])})")

    reason_text = " e ".join(reasons) if reasons else "melhor sinal no contexto"
    answer = (
        f"Entre {_format_channel_group(channels)}, eu priorizaria {channel} "
        f"para impacto comercial, porque ele tem {reason_text}."
    )
    if conversion is not None and conversion[0] != channel:
        answer += (
            f" Para eficiencia proporcional, {conversion[0]} merece acompanhamento "
            f"porque lidera em conversao com {_format_percentage(conversion[1])}."
        )
    return answer


def _metric_winner(
    channels: list[str],
    rows: dict[str, dict[str, float]],
    metric: str,
) -> tuple[str, float] | None:
    """Return the channel with the highest available value for a metric."""

    values = [
        (channel, rows[channel][metric])
        for channel in channels
        if channel in rows and metric in rows[channel]
    ]
    if not values:
        return None
    return max(values, key=lambda item: item[1])


def _format_channel_group(channels: list[str]) -> str:
    """Format a channel list in natural pt-BR prose."""

    if len(channels) <= 1:
        return channels[0] if channels else "os canais analisados"
    return ", ".join(channels[:-1]) + f" e {channels[-1]}"


def _format_integer(value: float) -> str:
    """Format integer metrics with Brazilian thousands separators."""

    return f"{round(value):,}".replace(",", ".")


def _format_percentage(value: float) -> str:
    """Format conversion rates as percentages."""

    percent = value * 100 if value <= 1 else value
    return _format_decimal(percent) + "%"


def _format_currency(value: float) -> str:
    """Format revenue in Brazilian reais."""

    return "R$ " + _format_decimal(value, thousands=True)


def _format_decimal(value: float, *, thousands: bool = False) -> str:
    """Format a decimal value using Brazilian separators."""

    if thousands:
        formatted = f"{value:,.2f}"
        return formatted.replace(",", "#").replace(".", ",").replace("#", ".")
    return f"{value:.2f}".replace(".", ",")


def _normalize_text(value: str) -> str:
    """Normalize accents, punctuation and whitespace for rule checks."""

    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents)
    return " ".join(without_punctuation.split())
