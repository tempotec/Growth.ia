"""Reusable BigQuery access service."""

from __future__ import annotations

import logging
import os
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

from app.core.config import get_settings
from app.core.logging import elapsed_ms, get_logger, log_event, start_timer


class BigQueryServiceError(Exception):
    """Raised when a BigQuery operation fails."""


class BigQueryService:
    """Thin wrapper around the official BigQuery client."""

    def __init__(self, client: bigquery.Client | None = None) -> None:
        if client is None:
            settings = get_settings()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                settings.google_application_credentials
            )
        self._client = client or bigquery.Client()
        self._logger = get_logger(__name__)

    def run_query(
        self,
        query: str,
        parameters: list[bigquery.ScalarQueryParameter] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and normalize rows to dictionaries."""

        job_config = bigquery.QueryJobConfig(query_parameters=parameters or [])
        query_start = start_timer()
        parameter_count = len(parameters or [])
        query_preview = " ".join(query.split())[:80]
        log_event(
            self._logger,
            logging.INFO,
            "bigquery_query_started",
            parameter_count=parameter_count,
            query_preview=query_preview,
        )

        try:
            query_job = self._client.query(query, job_config=job_config)
            rows = query_job.result()
        except GoogleAPIError as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "bigquery_query_failed",
                duration_ms=elapsed_ms(query_start),
                error_type=type(exc).__name__,
            )
            raise BigQueryServiceError("Failed to execute BigQuery query.") from exc
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "bigquery_query_failed",
                duration_ms=elapsed_ms(query_start),
                error_type=type(exc).__name__,
            )
            raise BigQueryServiceError("Unexpected BigQuery execution failure.") from exc

        normalized_rows = [dict(row.items()) for row in rows]
        log_event(
            self._logger,
            logging.INFO,
            "bigquery_query_completed",
            duration_ms=elapsed_ms(query_start),
            row_count=len(normalized_rows),
        )
        return normalized_rows
