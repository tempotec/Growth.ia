"""API request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Input payload for the /ask endpoint."""

    question: str = Field(..., min_length=1, description="User natural language query.")


class AskResponse(BaseModel):
    """Output payload for the /ask endpoint."""

    answer: str
    used_tool: str | None = None
    data: dict | list[dict] | None = None
    error: str | None = None


class CacheStatusResponse(BaseModel):
    """Operational status payload for the local cache layer."""

    status: str
    data_source_mode: str
    last_sync_status: str | None = None
    last_snapshot_at: datetime | None = None
    cache_age_minutes: int | None = None
    last_sync_started_at: datetime | None = None
    last_sync_completed_at: datetime | None = None
    last_sync_error_message: str | None = None


class DashboardOverviewSummary(BaseModel):
    """High-level KPI summary for the dashboard overview."""

    totalUsers: int
    totalOrders: int
    revenue: float
    conversionRate: float
    topChannel: str


class DashboardTrafficChannelMetric(BaseModel):
    """One channel metric inside a grouped traffic point."""

    channel: str
    visits: int


class DashboardTrafficPoint(BaseModel):
    """One grouped timeseries data point for traffic by source."""

    date: str
    channels: list[DashboardTrafficChannelMetric]


class DashboardConversionPoint(BaseModel):
    """One conversion rate entry by channel."""

    channel: str
    conversionRate: float


class DashboardInsight(BaseModel):
    """Narrative insight to surface on the dashboard."""

    type: str
    title: str
    message: str


class DashboardOverviewResponse(BaseModel):
    """Main dashboard overview contract consumed by the frontend."""

    status: str
    period: str
    channel: str
    lastSnapshotAt: datetime | None = None
    summary: DashboardOverviewSummary | None = None
    trafficBySource: list[DashboardTrafficPoint]
    conversionByChannel: list[DashboardConversionPoint]
    insights: list[DashboardInsight]
