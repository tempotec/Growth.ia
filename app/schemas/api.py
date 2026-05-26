"""API request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.analytics import AllowedTrafficSource, DateRange, SupportedIntent


class AnalyticsContextMetric(BaseModel):
    """Compact metric row kept for structured analytics follow-ups."""

    users: int | None = None
    converted_users: int | None = None
    orders: int | None = None
    revenue: float | None = None
    conversion_rate: float | None = None


class AnalyticsContext(BaseModel):
    """Structured context generated from the last analytics tool result."""

    last_intent: SupportedIntent | None = None
    last_channel: AllowedTrafficSource | None = None
    last_compared_channels: list[AllowedTrafficSource] = Field(default_factory=list)
    last_metric_context: str | None = None
    last_period: DateRange | None = None
    last_tool_result: dict[str, AnalyticsContextMetric] = Field(default_factory=dict)


class ConversationMessage(BaseModel):
    """One recent chat message used to resolve follow-up questions."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, description="Message text.")
    intent: SupportedIntent | None = None
    traffic_source: AllowedTrafficSource | None = None
    mentioned_traffic_sources: list[AllowedTrafficSource] = Field(default_factory=list)
    date_range: DateRange | None = None
    analytics_context: AnalyticsContext | None = None


class AskRequest(BaseModel):
    """Input payload for the /ask endpoint."""

    conversation_id: str = Field(
        default="default",
        min_length=1,
        description="Conversation identifier used to persist chat context.",
    )
    message: str = Field(..., min_length=1, description="User natural language query.")
    question: str = Field(..., min_length=1, description="User natural language query.")
    thinking_mode: bool = Field(
        default=False,
        description="When true, run one internal reflection pass before answering.",
    )
    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        description="Recent user/assistant messages for conversational context.",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_message_and_question(cls, data: object) -> object:
        """Support both the legacy question field and the new message contract."""

        if not isinstance(data, dict):
            return data

        payload = dict(data)
        question = payload.get("question")
        message = payload.get("message")
        if question is None and message is not None:
            payload["question"] = message
        if message is None and question is not None:
            payload["message"] = question
        return payload


class AskExecutionMetadata(BaseModel):
    """Internal execution metadata returned for observability."""

    tool_used: str | None = None
    reflection_used: bool = False
    reflection_score: int | None = None
    fallback_used: bool = False
    total_time_ms: float | None = None
    reflection_time_ms: float | None = None
    tokens_used: int | None = None
    cost_estimate: float | None = None


class ReflectionCritique(BaseModel):
    """Structured internal critique for the reflective answer pass."""

    score: int = Field(default=0, ge=0, le=10)
    issues: list[str] = Field(default_factory=list)
    recommendation: str = ""


class AskResponse(BaseModel):
    """Output payload for the /ask endpoint."""

    conversation_id: str | None = None
    answer: str
    thinking_mode: bool = False
    metadata: AskExecutionMetadata | None = None
    used_tool: str | None = None
    data: dict | list[dict] | None = None
    error: str | None = None
    intent: SupportedIntent | None = None
    traffic_source: AllowedTrafficSource | None = None
    mentioned_traffic_sources: list[AllowedTrafficSource] = Field(default_factory=list)
    date_range: DateRange | None = None
    analytics_context: AnalyticsContext | None = None


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
    totalConvertedUsers: int | None = None
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
