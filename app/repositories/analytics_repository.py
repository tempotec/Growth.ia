"""Analytics repository for Glacier AI V1 queries."""

from __future__ import annotations

from datetime import date, timedelta
from typing import get_args

from google.cloud import bigquery

from app.core.bigquery_tables import ORDER_ITEMS_TABLE, ORDERS_TABLE, USERS_TABLE
from app.schemas.analytics import AllowedTrafficSource
from app.services.bigquery_service import BigQueryService

DEFAULT_LOOKBACK_DAYS = 30
ALLOWED_TRAFFIC_SOURCES = tuple(get_args(AllowedTrafficSource))
TRAFFIC_SOURCE_MAP = {source.lower(): source for source in ALLOWED_TRAFFIC_SOURCES}


class AnalyticsRepositoryError(Exception):
    """Base repository exception."""


class InvalidTrafficSourceError(AnalyticsRepositoryError):
    """Raised when a traffic source is not supported in the V1 scope."""


class AnalyticsRepository:
    """Repository that centralizes V1 analytical queries."""

    def __init__(self, bigquery_service: BigQueryService | None = None) -> None:
        self._bigquery_service = bigquery_service or BigQueryService()

    def get_users_by_source(
        self,
        traffic_source: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Return the number of users acquired from a traffic source in a period."""

        normalized_source = self._normalize_traffic_source(traffic_source)
        resolved_start_date, resolved_end_date = self._resolve_date_range(
            start_date, end_date
        )
        query = f"""
            SELECT
              traffic_source,
              COUNT(DISTINCT id) AS users
            FROM `{USERS_TABLE}`
            WHERE traffic_source = @traffic_source
              AND DATE(created_at) BETWEEN @start_date AND @end_date
            GROUP BY traffic_source
        """
        parameters = [
            bigquery.ScalarQueryParameter(
                "traffic_source", "STRING", normalized_source
            ),
            bigquery.ScalarQueryParameter("start_date", "DATE", resolved_start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", resolved_end_date),
        ]
        rows = self._bigquery_service.run_query(query, parameters)

        users = int(rows[0]["users"]) if rows else 0
        return {
            "traffic_source": normalized_source,
            "users": users,
            "start_date": resolved_start_date.isoformat(),
            "end_date": resolved_end_date.isoformat(),
        }

    def get_revenue_by_source(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Return revenue aggregated by traffic source for a period."""

        resolved_start_date, resolved_end_date = self._resolve_date_range(
            start_date, end_date
        )
        query = f"""
            WITH order_revenue AS (
              SELECT
                order_id,
                SUM(sale_price) AS revenue
              FROM `{ORDER_ITEMS_TABLE}`
              GROUP BY order_id
            )
            SELECT
              u.traffic_source AS traffic_source,
              ROUND(SUM(orv.revenue), 2) AS revenue
            FROM `{ORDERS_TABLE}` AS o
            INNER JOIN `{USERS_TABLE}` AS u
              ON u.id = o.user_id
            INNER JOIN order_revenue AS orv
              ON orv.order_id = o.order_id
            WHERE u.traffic_source IN UNNEST(@traffic_sources)
              AND DATE(o.created_at) BETWEEN @start_date AND @end_date
            GROUP BY u.traffic_source
            ORDER BY revenue DESC
        """
        parameters = [
            bigquery.ArrayQueryParameter(
                "traffic_sources", "STRING", list(ALLOWED_TRAFFIC_SOURCES)
            ),
            bigquery.ScalarQueryParameter("start_date", "DATE", resolved_start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", resolved_end_date),
        ]
        rows = self._bigquery_service.run_query(query, parameters)
        return [
            {
                "traffic_source": row["traffic_source"],
                "revenue": float(row["revenue"] or 0),
                "start_date": resolved_start_date.isoformat(),
                "end_date": resolved_end_date.isoformat(),
            }
            for row in rows
        ]

    def get_channel_performance_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Return users, orders, revenue, and conversion rate by traffic source."""

        resolved_start_date, resolved_end_date = self._resolve_date_range(
            start_date, end_date
        )
        query = f"""
            WITH source_dim AS (
              SELECT traffic_source
              FROM UNNEST(@traffic_sources) AS traffic_source
            ),
            users_agg AS (
              SELECT
                traffic_source,
                COUNT(DISTINCT id) AS users
              FROM `{USERS_TABLE}`
              WHERE traffic_source IN UNNEST(@traffic_sources)
                AND DATE(created_at) BETWEEN @start_date AND @end_date
              GROUP BY traffic_source
            ),
            orders_agg AS (
              SELECT
                u.traffic_source AS traffic_source,
                COUNT(DISTINCT o.order_id) AS orders
              FROM `{ORDERS_TABLE}` AS o
              INNER JOIN `{USERS_TABLE}` AS u
                ON u.id = o.user_id
              WHERE u.traffic_source IN UNNEST(@traffic_sources)
                AND DATE(o.created_at) BETWEEN @start_date AND @end_date
              GROUP BY u.traffic_source
            ),
            order_revenue AS (
              SELECT
                order_id,
                SUM(sale_price) AS revenue
              FROM `{ORDER_ITEMS_TABLE}`
              GROUP BY order_id
            ),
            revenue_agg AS (
              SELECT
                u.traffic_source AS traffic_source,
                ROUND(SUM(orv.revenue), 2) AS revenue
              FROM `{ORDERS_TABLE}` AS o
              INNER JOIN `{USERS_TABLE}` AS u
                ON u.id = o.user_id
              INNER JOIN order_revenue AS orv
                ON orv.order_id = o.order_id
              WHERE u.traffic_source IN UNNEST(@traffic_sources)
                AND DATE(o.created_at) BETWEEN @start_date AND @end_date
              GROUP BY u.traffic_source
            )
            SELECT
              sd.traffic_source AS traffic_source,
              COALESCE(ua.users, 0) AS users,
              COALESCE(oa.orders, 0) AS orders,
              COALESCE(ra.revenue, 0) AS revenue,
              SAFE_DIVIDE(COALESCE(oa.orders, 0), NULLIF(COALESCE(ua.users, 0), 0)) AS conversion_rate
            FROM source_dim AS sd
            LEFT JOIN users_agg AS ua
              ON ua.traffic_source = sd.traffic_source
            LEFT JOIN orders_agg AS oa
              ON oa.traffic_source = sd.traffic_source
            LEFT JOIN revenue_agg AS ra
              ON ra.traffic_source = sd.traffic_source
            ORDER BY conversion_rate DESC, revenue DESC
        """
        parameters = [
            bigquery.ArrayQueryParameter(
                "traffic_sources", "STRING", list(ALLOWED_TRAFFIC_SOURCES)
            ),
            bigquery.ScalarQueryParameter("start_date", "DATE", resolved_start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", resolved_end_date),
        ]
        rows = self._bigquery_service.run_query(query, parameters)
        return [
            {
                "traffic_source": row["traffic_source"],
                "users": int(row["users"] or 0),
                "orders": int(row["orders"] or 0),
                "revenue": float(row["revenue"] or 0),
                "conversion_rate": float(row["conversion_rate"] or 0),
                "start_date": resolved_start_date.isoformat(),
                "end_date": resolved_end_date.isoformat(),
            }
            for row in rows
        ]

    def get_daily_users_by_source(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Return daily traffic grouped by source for the selected period."""

        resolved_start_date, resolved_end_date = self._resolve_date_range(
            start_date, end_date
        )
        query = f"""
            SELECT
              DATE(created_at) AS metric_date,
              traffic_source,
              COUNT(DISTINCT id) AS visits
            FROM `{USERS_TABLE}`
            WHERE traffic_source IN UNNEST(@traffic_sources)
              AND DATE(created_at) BETWEEN @start_date AND @end_date
            GROUP BY metric_date, traffic_source
            ORDER BY metric_date ASC, traffic_source ASC
        """
        parameters = [
            bigquery.ArrayQueryParameter(
                "traffic_sources", "STRING", list(ALLOWED_TRAFFIC_SOURCES)
            ),
            bigquery.ScalarQueryParameter("start_date", "DATE", resolved_start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", resolved_end_date),
        ]
        rows = self._bigquery_service.run_query(query, parameters)
        return [
            {
                "date": row["metric_date"].isoformat()
                if hasattr(row["metric_date"], "isoformat")
                else str(row["metric_date"]),
                "channel": row["traffic_source"],
                "visits": int(row["visits"] or 0),
            }
            for row in rows
        ]

    def _normalize_traffic_source(self, traffic_source: str) -> str:
        """Normalize and validate supported traffic source values."""

        normalized = TRAFFIC_SOURCE_MAP.get(traffic_source.strip().lower())
        if normalized is None:
            allowed_values = ", ".join(ALLOWED_TRAFFIC_SOURCES)
            raise InvalidTrafficSourceError(
                f"Unsupported traffic_source. Allowed values: {allowed_values}."
            )
        return normalized

    def _resolve_date_range(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date]:
        """Resolve the effective date range using a 30-day default window."""

        today = date.today()
        resolved_end_date = end_date or today
        default_delta = timedelta(days=DEFAULT_LOOKBACK_DAYS - 1)

        if start_date is None and end_date is None:
            resolved_start_date = resolved_end_date - default_delta
        elif start_date is None:
            resolved_start_date = resolved_end_date - default_delta
        else:
            resolved_start_date = start_date

        if end_date is None:
            resolved_end_date = max(resolved_end_date, resolved_start_date)

        if resolved_start_date > resolved_end_date:
            raise AnalyticsRepositoryError(
                "start_date must be less than or equal to end_date."
            )

        return resolved_start_date, resolved_end_date
