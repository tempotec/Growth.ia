"""Tool registry for Glacier AI V1."""

from app.tools.performance_tools import get_channel_performance_summary
from app.tools.revenue_tools import get_revenue_by_source
from app.tools.traffic_tools import get_users_by_source

TOOL_REGISTRY = {
    "get_users_by_source": get_users_by_source,
    "get_revenue_by_source": get_revenue_by_source,
    "get_channel_performance_summary": get_channel_performance_summary,
}

__all__ = [
    "TOOL_REGISTRY",
    "get_users_by_source",
    "get_revenue_by_source",
    "get_channel_performance_summary",
]
