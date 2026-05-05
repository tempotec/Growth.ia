"""Unit tests for the BigQuery service wrapper."""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest
from google.api_core.exceptions import GoogleAPIError

from app.services.bigquery_service import BigQueryService, BigQueryServiceError


def test_bigquery_service_uses_injected_client() -> None:
    client = Mock()

    service = BigQueryService(client=client)

    assert service._client is client


def test_bigquery_service_initializes_default_client_with_settings(
    valid_env: dict[str, str],
) -> None:
    mock_client = Mock()
    mock_settings = Mock()
    mock_settings.google_application_credentials = valid_env[
        "GOOGLE_APPLICATION_CREDENTIALS"
    ]

    with patch("app.services.bigquery_service.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings
        with patch(
            "app.services.bigquery_service.bigquery.Client",
            return_value=mock_client,
        ) as mock_bigquery_client:
            service = BigQueryService()

    mock_get_settings.assert_called_once_with()
    mock_bigquery_client.assert_called_once_with()
    assert service._client is mock_client


def test_run_query_returns_rows_as_dicts() -> None:
    query_job = Mock()
    query_job.result.return_value = [{"traffic_source": "Search", "users": 10}]
    client = Mock()
    client.query.return_value = query_job
    service = BigQueryService(client=client)

    result = service.run_query("SELECT 1")

    assert result == [{"traffic_source": "Search", "users": 10}]
    client.query.assert_called_once()


def test_run_query_wraps_google_api_errors() -> None:
    client = Mock()
    client.query.side_effect = GoogleAPIError("boom")
    service = BigQueryService(client=client)

    with pytest.raises(BigQueryServiceError) as exc_info:
        service.run_query("SELECT 1")

    assert "Failed to execute BigQuery query" in str(exc_info.value)


def test_run_query_wraps_unexpected_errors() -> None:
    client = Mock()
    client.query.side_effect = RuntimeError("boom")
    service = BigQueryService(client=client)

    with pytest.raises(BigQueryServiceError) as exc_info:
        service.run_query("SELECT 1")

    assert "Unexpected BigQuery execution failure" in str(exc_info.value)


def test_run_query_emits_observability_logs(caplog) -> None:
    query_job = Mock()
    query_job.result.return_value = [{"total": 1}]
    client = Mock()
    client.query.return_value = query_job
    service = BigQueryService(client=client)

    with caplog.at_level(logging.INFO):
        service.run_query("SELECT COUNT(*) AS total FROM users")

    log_text = " ".join(caplog.messages)
    assert "event=bigquery_query_started" in log_text
    assert "event=bigquery_query_completed" in log_text
