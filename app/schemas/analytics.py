"""Analytics schemas shared across the agent and tools layers."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


SupportedIntent = Literal[
    "traffic_volume_by_source",
    "revenue_by_source",
    "best_channel_performance",
    "channel_performance_by_source",
    "recommendation",
    "out_of_scope",
]

AllowedTrafficSource = Literal[
    "Search",
    "Organic",
    "Facebook",
    "Email",
    "Direct",
    "Display",
    "Referral",
]


class DateRange(BaseModel):
    """Normalized date interval used by analytics queries."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_order(self) -> "DateRange":
        """Ensure the start date is not after the end date."""

        if self.start_date > self.end_date:
            raise ValueError("start_date must be less than or equal to end_date")
        return self


class ParsedQuestion(BaseModel):
    """Structured output produced by the question parsing step."""

    intent: SupportedIntent
    traffic_source: AllowedTrafficSource | None = None
    mentioned_traffic_sources: list[AllowedTrafficSource] = Field(default_factory=list)
    date_range: DateRange
    needs_data: bool = True
    out_of_scope_reason: str | None = None

    @model_validator(mode="after")
    def validate_out_of_scope_contract(self) -> "ParsedQuestion":
        """Keep the parser contract consistent for out-of-scope questions."""

        if self.intent == "out_of_scope":
            self.needs_data = False
        return self


class UsersBySourceResult(BaseModel):
    """Structured payload for traffic volume queries."""

    traffic_source: AllowedTrafficSource
    users: int = Field(ge=0)
    date_range: DateRange


class RevenueBySourceResult(BaseModel):
    """Structured payload for revenue queries."""

    traffic_source: AllowedTrafficSource
    revenue: float = Field(ge=0)
    date_range: DateRange


class ChannelPerformance(BaseModel):
    """Aggregated channel performance metrics."""

    traffic_source: AllowedTrafficSource
    users: int = Field(ge=0)
    converted_users: int = Field(ge=0)
    orders: int = Field(ge=0)
    revenue: float = Field(ge=0)
    conversion_rate: float = Field(ge=0, le=1)


class ChannelPerformanceSummaryResult(BaseModel):
    """Structured payload for channel performance comparisons."""

    date_range: DateRange
    channels: list[ChannelPerformance]
    ranking_basis: str = "conversion_rate_then_revenue"


class ChannelPerformanceBySourceResult(BaseModel):
    """Structured payload for one channel performance query."""

    traffic_source: AllowedTrafficSource
    users: int = Field(ge=0)
    converted_users: int = Field(ge=0)
    orders: int = Field(ge=0)
    revenue: float = Field(ge=0)
    conversion_rate: float = Field(ge=0, le=1)
    date_range: DateRange
