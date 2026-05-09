"""Shared metric projections for analytics contracts."""

from __future__ import annotations

from typing import Any


def derive_revenue_by_source(channel_performance_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project revenue rows from canonical channel performance metrics."""

    revenue_rows = [
        {
            "traffic_source": row["traffic_source"],
            "revenue": float(row["revenue"] or 0),
            "start_date": row.get("start_date"),
            "end_date": row.get("end_date"),
        }
        for row in channel_performance_rows
    ]
    return sorted(
        revenue_rows,
        key=lambda row: (-row["revenue"], row["traffic_source"]),
    )
