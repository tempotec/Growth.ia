"""Deterministic multi-criteria answers for channel performance."""

from __future__ import annotations

from typing import Any

METRICS = ("users", "converted_users", "orders", "revenue", "conversion_rate")


def build_best_performance_answer(
    tool_result: Any,
    *,
    short_answer: bool = False,
) -> str | None:
    """Build a multi-criteria answer for best channel performance."""

    rows = _performance_rows(tool_result)
    if not rows:
        return None

    volume = _metric_winner(rows, "users")
    conversion = _metric_winner(rows, "conversion_rate")
    revenue = _metric_winner(rows, "revenue")
    orders = _metric_winner(rows, "orders")
    converted_users = _metric_winner(rows, "converted_users")
    if volume is None and conversion is None and revenue is None:
        return None

    commercial = revenue or orders or converted_users or volume or conversion
    efficiency = conversion or revenue or orders or volume
    if commercial is None or efficiency is None:
        return None

    if short_answer:
        return _build_short_answer(
            volume=volume,
            conversion=conversion,
            revenue=revenue,
            commercial=commercial,
            efficiency=efficiency,
        )

    return _build_full_answer(
        rows=rows,
        volume=volume,
        conversion=conversion,
        revenue=revenue,
        orders=orders,
        commercial=commercial,
        efficiency=efficiency,
    )


def _performance_rows(tool_result: Any) -> list[dict[str, float | str]]:
    """Normalize a performance summary result into rows with numeric metrics."""

    if not isinstance(tool_result, list):
        return []

    rows: list[dict[str, float | str]] = []
    for row in tool_result:
        if not isinstance(row, dict):
            continue
        source = row.get("traffic_source")
        if not isinstance(source, str):
            continue

        normalized_row: dict[str, float | str] = {"traffic_source": source}
        for metric in METRICS:
            value = row.get(metric)
            if isinstance(value, bool):
                continue
            if isinstance(value, int | float):
                normalized_row[metric] = float(value)
        if len(normalized_row) > 1:
            rows.append(normalized_row)

    return rows


def _build_short_answer(
    *,
    volume: tuple[str, float] | None,
    conversion: tuple[str, float] | None,
    revenue: tuple[str, float] | None,
    commercial: tuple[str, float],
    efficiency: tuple[str, float],
) -> str:
    """Build a compact multi-criteria answer."""

    criteria = _criteria_summary(volume=volume, conversion=conversion, revenue=revenue)
    return (
        f"Depende do critério: {criteria}. "
        f"Para impacto comercial total, {commercial[0]} é o principal; "
        f"para eficiência proporcional, {efficiency[0]} é o melhor."
    )


def _build_full_answer(
    *,
    rows: list[dict[str, float | str]],
    volume: tuple[str, float] | None,
    conversion: tuple[str, float] | None,
    revenue: tuple[str, float] | None,
    orders: tuple[str, float] | None,
    commercial: tuple[str, float],
    efficiency: tuple[str, float],
) -> str:
    """Build a concise full answer with explicit criteria."""

    criteria = _criteria_summary(volume=volume, conversion=conversion, revenue=revenue)
    answer = (
        f"Depende do critério: {criteria}. "
        f"Para impacto comercial total, {commercial[0]} é o principal; "
        f"para eficiência proporcional, {efficiency[0]} é o melhor."
    )

    evidence_parts = []
    if volume is not None:
        evidence_parts.append(f"volume: {volume[0]} com {_format_integer(volume[1])} usuários")
    if conversion is not None:
        evidence_parts.append(
            f"conversão: {conversion[0]} com {_format_percentage(conversion[1])}"
        )
    if revenue is not None:
        evidence_parts.append(f"receita: {revenue[0]} com {_format_currency(revenue[1])}")
    if orders is not None:
        evidence_parts.append(f"pedidos: {orders[0]} com {_format_integer(orders[1])}")

    if evidence_parts:
        answer += " Nos dados, " + "; ".join(evidence_parts) + "."

    if len(rows) > 1:
        answer += (
            " Assim, não há um vencedor absoluto sem definir o objetivo: escala e "
            "receita favorecem impacto, enquanto conversão favorece eficiência."
        )
    return answer


def _criteria_summary(
    *,
    volume: tuple[str, float] | None,
    conversion: tuple[str, float] | None,
    revenue: tuple[str, float] | None,
) -> str:
    """Summarize metric leaders in one sentence fragment."""

    parts = []
    if conversion is not None:
        parts.append(f"{conversion[0]} lidera em conversão")
    if volume is not None:
        parts.append(f"{volume[0]} lidera em volume")
    if revenue is not None:
        parts.append(f"{revenue[0]} lidera em receita")
    return ", ".join(parts) if parts else "não há métricas suficientes"


def _metric_winner(
    rows: list[dict[str, float | str]],
    metric: str,
) -> tuple[str, float] | None:
    """Return the channel with the highest available value for a metric."""

    values = [
        (row["traffic_source"], row[metric])
        for row in rows
        if isinstance(row.get("traffic_source"), str)
        and isinstance(row.get(metric), int | float)
    ]
    if not values:
        return None
    channel, value = max(values, key=lambda item: item[1])
    return str(channel), float(value)


def _format_integer(value: float) -> str:
    """Format integer metrics with Brazilian thousands separators."""

    return f"{round(value):,}".replace(",", ".")


def _format_percentage(value: float) -> str:
    """Format conversion rates as percentages."""

    percent = value * 100 if value <= 1 else value
    return f"{percent:.2f}".replace(".", ",") + "%"


def _format_currency(value: float) -> str:
    """Format revenue in Brazilian reais."""

    formatted = f"{value:,.2f}"
    return "R$ " + formatted.replace(",", "#").replace(".", ",").replace("#", ".")
