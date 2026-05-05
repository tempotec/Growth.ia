"""Reusable BigQuery access service."""

from __future__ import annotations

from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

from app.core.config import get_settings


class BigQueryServiceError(Exception):
    """Raised when a BigQuery operation fails."""


class BigQueryService:
    """Thin wrapper around the official BigQuery client."""

    def __init__(self, client: bigquery.Client | None = None) -> None:
        if client is None:
            # Force settings validation before the client is created.
            get_settings()
        self._client = client or bigquery.Client()

    def run_query(
        self,
        query: str,
        parameters: list[bigquery.ScalarQueryParameter] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and normalize rows to dictionaries."""

        job_config = bigquery.QueryJobConfig(query_parameters=parameters or [])

        try:
            query_job = self._client.query(query, job_config=job_config)
            rows = query_job.result()
        except GoogleAPIError as exc:
            raise BigQueryServiceError("Failed to execute BigQuery query.") from exc
        except Exception as exc:
            raise BigQueryServiceError("Unexpected BigQuery execution failure.") from exc

        return [dict(row.items()) for row in rows]
