"""Build the dashboard overview contract consumed by the frontend."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.repositories.analytics_repository import (
    AnalyticsRepository,
    AnalyticsRepositoryError,
)
from app.repositories.local_cache_repository import (
    LocalCacheRepository,
    LocalCacheSnapshotNotFoundError,
)
from app.schemas.api import (
    DashboardConversionPoint,
    DashboardInsight,
    DashboardOverviewResponse,
    DashboardOverviewSummary,
    DashboardTrafficChannelMetric,
    DashboardTrafficPoint,
)
from app.services.bigquery_service import BigQueryServiceError

DEFAULT_PERIOD_DAYS = 30


class DashboardOverviewService:
    """Compose dashboard-ready analytics from the available read sources."""

    def __init__(
        self,
        *,
        local_cache_repository: LocalCacheRepository | None = None,
        analytics_repository: AnalyticsRepository | None = None,
    ) -> None:
        self._local_cache_repository = local_cache_repository or LocalCacheRepository()
        self._analytics_repository = analytics_repository or AnalyticsRepository()

    def build_overview(
        self,
        *,
        period: str = "30d",
        channel: str = "all",
    ) -> DashboardOverviewResponse:
        """Return the dashboard overview contract."""

        try:
            latest_sync = self._local_cache_repository.get_latest_sync_status()
        except LocalCacheSnapshotNotFoundError:
            return DashboardOverviewResponse(
                status="online",
                period=period,
                channel=channel,
                lastSnapshotAt=None,
                summary=None,
                trafficBySource=[],
                conversionByChannel=[],
                insights=[
                    DashboardInsight(
                        type="info",
                        title="Aguardando primeira sincronizacao",
                        message=(
                            "Nenhum snapshot local esta disponivel ainda. Execute a rotina de "
                            "sincronizacao para validar os dados reais do dashboard."
                        ),
                    )
                ],
            )

        last_snapshot_at = _parse_snapshot_datetime(latest_sync.get("snapshot_at"))

        try:
            channel_rows = self._local_cache_repository.get_channel_performance_summary()
        except LocalCacheSnapshotNotFoundError:
            return DashboardOverviewResponse(
                status="online",
                period=period,
                channel=channel,
                lastSnapshotAt=last_snapshot_at,
                summary=None,
                trafficBySource=[],
                conversionByChannel=[],
                insights=[
                    DashboardInsight(
                        type="warning",
                        title="Snapshot incompleto",
                        message=(
                            "O ultimo sync foi registrado, mas o materialized view de performance "
                            "por canal ainda nao esta disponivel."
                        ),
                    )
                ],
            )

        total_users = sum(int(row["users"]) for row in channel_rows)
        total_orders = sum(int(row["orders"]) for row in channel_rows)
        total_revenue = sum(float(row["revenue"]) for row in channel_rows)
        top_channel = channel_rows[0]["traffic_source"] if channel_rows else "Indisponivel"
        traffic_by_source = self.build_traffic_by_source(period=period)

        return DashboardOverviewResponse(
            status="online",
            period=period,
            channel=channel,
            lastSnapshotAt=last_snapshot_at,
            summary=DashboardOverviewSummary(
                totalUsers=total_users,
                totalOrders=total_orders,
                revenue=round(total_revenue, 2),
                conversionRate=_percentage_from_ratio(total_orders / total_users)
                if total_users > 0
                else 0.0,
                topChannel=top_channel,
            ),
            trafficBySource=traffic_by_source,
            conversionByChannel=[
                DashboardConversionPoint(
                    channel=row["traffic_source"],
                    conversionRate=_percentage_from_ratio(float(row["conversion_rate"])),
                )
                for row in channel_rows
            ],
            insights=_build_dashboard_insights(channel_rows, traffic_by_source),
        )

    def build_traffic_by_source(self, *, period: str) -> list[DashboardTrafficPoint]:
        """Build the daily traffic series from the real analytics source."""

        start_date, end_date = _resolve_period(period)
        try:
            rows = self._analytics_repository.get_daily_users_by_source(
                start_date=start_date,
                end_date=end_date,
            )
        except (AnalyticsRepositoryError, BigQueryServiceError):
            return []

        grouped: dict[str, list[DashboardTrafficChannelMetric]] = {}
        for row in rows:
            grouped.setdefault(row["date"], []).append(
                DashboardTrafficChannelMetric(
                    channel=row["channel"],
                    visits=int(row["visits"]),
                )
            )

        return [
            DashboardTrafficPoint(date=point_date, channels=channels)
            for point_date, channels in sorted(grouped.items())
        ]


def _resolve_period(period: str) -> tuple[date, date]:
    """Resolve a simple lookback period such as 30d into concrete dates."""

    lowered = period.strip().lower()
    if lowered.endswith("d") and lowered[:-1].isdigit():
        lookback_days = max(1, int(lowered[:-1]))
    else:
        lookback_days = DEFAULT_PERIOD_DAYS

    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days - 1)
    return start_date, end_date


def _parse_snapshot_datetime(value: str | None) -> datetime | None:
    """Parse a stored sync timestamp into a datetime."""

    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _percentage_from_ratio(value: float) -> float:
    """Normalize decimal ratios into human-readable percentage values."""

    if value <= 1:
        return round(value * 100, 2)
    return round(value, 2)


def _build_dashboard_insights(
    channel_rows: list[dict],
    traffic_by_source: list[DashboardTrafficPoint],
) -> list[DashboardInsight]:
    """Generate a small deterministic narrative from the latest snapshot."""

    if not channel_rows:
        return [
            DashboardInsight(
                type="info",
                title="Sem dados suficientes",
                message="O snapshot atual nao contem linhas para gerar insights.",
            )
        ]

    top_row = channel_rows[0]
    insights = [
        DashboardInsight(
            type="success",
            title=f"Melhor performance em {top_row['traffic_source']}",
            message=(
                f"{top_row['traffic_source']} lidera a conversao no snapshot atual com "
                f"{_percentage_from_ratio(float(top_row['conversion_rate'])):.1f}% de conversao."
            ),
        )
    ]

    for row in channel_rows:
        if row["traffic_source"] == "Facebook Ads" and float(row["conversion_rate"]) <= 0.02:
            insights.append(
                DashboardInsight(
                    type="warning",
                    title="Queda em Facebook Ads",
                    message=(
                        "Facebook Ads aparece com taxa de conversao baixa no snapshot atual. "
                        "Vale revisar eficiencia e qualidade do trafego pago."
                    ),
                )
            )
            break

    if not traffic_by_source:
        insights.append(
            DashboardInsight(
                type="info",
                title="Serie temporal pendente",
                message=(
                    "A estrutura de trafficBySource ja esta no contrato, mas ainda nao foi "
                    "possivel retornar a serie temporal real para este ambiente."
                ),
            )
        )

    return insights
