"""Unit tests for analytics schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.analytics import (
    ChannelPerformance,
    ChannelPerformanceSummaryResult,
    DateRange,
    ParsedQuestion,
    RevenueBySourceResult,
    UsersBySourceResult,
)


def test_date_range_accepts_valid_dates(
    valid_date_range_payload: dict[str, str],
) -> None:
    date_range = DateRange(**valid_date_range_payload)

    assert date_range.start_date.isoformat() == "2026-04-01"
    assert date_range.end_date.isoformat() == "2026-04-30"


def test_date_range_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        DateRange(start_date="2026-05-01", end_date="2026-04-30")


def test_parsed_question_accepts_supported_intent(
    valid_parsed_question_payload: dict,
) -> None:
    parsed = ParsedQuestion(**valid_parsed_question_payload)

    assert parsed.intent == "traffic_volume_by_source"
    assert parsed.traffic_source == "Search"
    assert parsed.needs_data is True


def test_parsed_question_accepts_out_of_scope_and_forces_needs_data_false(
    valid_date_range_payload: dict[str, str],
) -> None:
    parsed = ParsedQuestion(
        intent="out_of_scope",
        traffic_source=None,
        date_range=valid_date_range_payload,
        needs_data=True,
        out_of_scope_reason="unsupported_intent",
    )

    assert parsed.intent == "out_of_scope"
    assert parsed.needs_data is False
    assert parsed.out_of_scope_reason == "unsupported_intent"


def test_parsed_question_rejects_invalid_traffic_source(
    valid_date_range_payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        ParsedQuestion(
            intent="traffic_volume_by_source",
            traffic_source="TikTok",
            date_range=valid_date_range_payload,
            needs_data=True,
            out_of_scope_reason=None,
        )

    assert "traffic_source" in str(exc_info.value)


def test_channel_performance_accepts_valid_payload(
    valid_channel_performance_payload: dict,
) -> None:
    performance = ChannelPerformance(**valid_channel_performance_payload)

    assert performance.traffic_source == "Organic"
    assert performance.conversion_rate == 0.08


def test_users_by_source_result_accepts_valid_payload(
    valid_date_range_payload: dict[str, str],
) -> None:
    result = UsersBySourceResult(
        traffic_source="Search",
        users=1234,
        date_range=valid_date_range_payload,
    )

    assert result.users == 1234


def test_revenue_by_source_result_accepts_valid_payload(
    valid_date_range_payload: dict[str, str],
) -> None:
    result = RevenueBySourceResult(
        traffic_source="Organic",
        revenue=12345.67,
        date_range=valid_date_range_payload,
    )

    assert result.revenue == 12345.67


def test_channel_performance_summary_result_accepts_valid_payload(
    valid_date_range_payload: dict[str, str],
    valid_channel_performance_payload: dict,
) -> None:
    summary = ChannelPerformanceSummaryResult(
        date_range=valid_date_range_payload,
        channels=[valid_channel_performance_payload],
    )

    assert len(summary.channels) == 1
    assert summary.ranking_basis == "conversion_rate_then_revenue"
