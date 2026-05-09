"""HTTP tests for the Glacier AI FastAPI layer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_post_ask_returns_successful_response(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.run_agent_question",
        lambda question, conversation_history=None: {
            "intent": "best_channel_performance",
            "tool_name": "get_channel_performance_summary",
            "tool_result": [{"traffic_source": "Organic", "conversion_rate": 0.08}],
            "answer": "Organic foi o canal com melhor performance nos ultimos 30 dias.",
            "error": None,
        },
    )

    response = client.post("/ask", json={"question": "Qual canal teve melhor performance?"})

    assert response.status_code == 200
    assert response.json()["used_tool"] == "get_channel_performance_summary"
    assert response.json()["error"] is None


def test_post_ask_forwards_conversation_history(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)
    captured_history = []

    def fake_run_agent_question(question: str, conversation_history=None) -> dict:
        captured_history.extend(conversation_history or [])
        return {
            "intent": "traffic_volume_by_source",
            "traffic_source": "Search",
            "date_range": {
                "start_date": "2026-02-01",
                "end_date": "2026-03-31",
            },
            "tool_name": "get_users_by_source",
            "tool_result": {"traffic_source": "Search", "users": 123},
            "answer": "Search trouxe 123 usuarios no periodo.",
            "error": None,
        }

    monkeypatch.setattr("app.api.routes.run_agent_question", fake_run_agent_question)

    response = client.post(
        "/ask",
        json={
            "question": "E em fevereiro e marco?",
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "Search teve 2478 usuarios nos ultimos 30 dias.",
                    "intent": "traffic_volume_by_source",
                    "traffic_source": "Search",
                    "date_range": {
                        "start_date": "2026-04-08",
                        "end_date": "2026-05-07",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    assert captured_history[0]["traffic_source"] == "Search"
    assert response.json()["intent"] == "traffic_volume_by_source"
    assert response.json()["date_range"]["start_date"] == "2026-02-01"


def test_post_ask_returns_out_of_scope_response(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.run_agent_question",
        lambda question, conversation_history=None: {
            "intent": "out_of_scope",
            "tool_name": None,
            "tool_result": None,
            "answer": "The current V1 scope covers analysis only.",
            "error": None,
            "out_of_scope_reason": "unsupported_intent",
        },
    )

    response = client.post("/ask", json={"question": "Me fale sobre CAC"})

    assert response.status_code == 200
    assert response.json()["used_tool"] is None
    assert response.json()["data"] is None
    assert response.json()["error"] == "unsupported_intent"
    assert response.json()["answer"].startswith("Essa pergunta está fora do escopo")
    assert "The current" not in response.json()["answer"]


def test_post_ask_handles_simple_greeting_without_agent(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    def fail_if_called(question: str, conversation_history=None) -> dict:
        raise AssertionError("Agent should not be called for simple greetings.")

    monkeypatch.setattr("app.api.routes.run_agent_question", fail_if_called)

    response = client.post("/ask", json={"question": "oi"})

    assert response.status_code == 200
    assert response.json()["answer"].startswith("Olá!")
    assert "tráfego, receita e performance por canal" in response.json()["answer"]
    assert response.json()["used_tool"] is None
    assert response.json()["data"] is None
    assert response.json()["error"] is None


def test_post_ask_rejects_invalid_payload() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post("/ask", json={"question": ""})

    assert response.status_code == 422


def test_post_ask_returns_bad_request_for_controlled_agent_error(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.run_agent_question",
        lambda question, conversation_history=None: {
            "intent": "traffic_volume_by_source",
            "tool_name": "get_users_by_source",
            "tool_result": None,
            "answer": "Unsupported traffic_source. Allowed values: Search, Organic.",
            "error": "Unsupported traffic_source. Allowed values: Search, Organic.",
        },
    )

    response = client.post("/ask", json={"question": "Volume de TikTok"})

    assert response.status_code == 400
    assert response.json()["answer"].startswith("Essa origem de tráfego")
    assert response.json()["error"].startswith("Essa origem de tráfego")


def test_post_ask_returns_internal_error_for_unexpected_failure(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    def raise_error(question: str, conversation_history=None) -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.api.routes.run_agent_question", raise_error)

    response = client.post("/ask", json={"question": "Qual canal teve mais receita?"})

    assert response.status_code == 500
    assert response.json()["error"] == "Nao foi possivel processar a solicitacao no momento."


def test_post_ask_returns_service_unavailable_for_missing_local_cache_snapshot(
    monkeypatch,
) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.run_agent_question",
        lambda question, conversation_history=None: {
            "intent": "best_channel_performance",
            "tool_name": "get_channel_performance_summary",
            "tool_result": None,
            "answer": "No local cache snapshot is available yet. Run the cache sync first.",
            "error": "local_cache_snapshot_not_found",
        },
    )

    response = client.post("/ask", json={"question": "Qual canal teve melhor performance?"})

    assert response.status_code == 503
    assert response.json()["answer"].startswith("Ainda não há um snapshot local")
    assert response.json()["error"] == "local_cache_snapshot_not_found"


def test_get_health_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_app_lifespan_starts_and_stops_cache_scheduler(monkeypatch) -> None:
    events = []

    class StubCacheScheduler:
        async def start(self) -> None:
            events.append("start")

        async def stop(self) -> None:
            events.append("stop")

    monkeypatch.setattr("app.main.CacheSchedulerService", StubCacheScheduler)

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert events == ["start", "stop"]


def test_health_preflight_allows_frontend_origin() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_get_cache_status_returns_latest_sync_metadata(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.get_cache_settings",
        lambda: type("Settings", (), {"data_source_mode": "local_cache"})(),
    )

    class StubRepository:
        def get_latest_sync_status(self):
            return {
                "started_at": "2026-05-05T23:40:00+00:00",
                "completed_at": "2026-05-05T23:44:00+00:00",
                "snapshot_at": "2026-05-05T23:44:13+00:00",
                "status": "success",
                "channel_performance_rows": 7,
                "revenue_by_source_rows": 5,
                "users_by_source_rows": 7,
                "error_message": None,
            }

    monkeypatch.setattr("app.api.routes.LocalCacheRepository", StubRepository)
    monkeypatch.setattr(
        "app.api.routes._compute_cache_age_minutes",
        lambda snapshot_at: 6,
    )

    response = client.get("/cache/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data_source_mode"] == "local_cache"
    assert payload["last_sync_status"] == "success"
    assert payload["cache_age_minutes"] == 6
    assert payload["last_snapshot_at"] == "2026-05-05T23:44:13Z"


def test_get_cache_status_returns_warning_when_no_sync_is_recorded(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.get_cache_settings",
        lambda: type("Settings", (), {"data_source_mode": "local_cache"})(),
    )

    class StubRepository:
        def get_latest_sync_status(self):
            from app.repositories.local_cache_repository import LocalCacheSnapshotNotFoundError

            raise LocalCacheSnapshotNotFoundError("No cache sync has been recorded yet.")

    monkeypatch.setattr("app.api.routes.LocalCacheRepository", StubRepository)

    response = client.get("/cache/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "warning"
    assert payload["last_sync_status"] is None
    assert payload["last_sync_error_message"] == "No cache sync has been recorded yet."


def test_get_dashboard_overview_returns_empty_contract_when_no_snapshot_exists(
    monkeypatch,
) -> None:
    app = create_app()
    client = TestClient(app)

    class StubDashboardOverviewService:
        def build_overview(self, *, period: str, channel: str):
            from app.schemas.api import DashboardInsight, DashboardOverviewResponse

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
                        message="Nenhum snapshot disponivel.",
                    )
                ],
            )

    monkeypatch.setattr(
        "app.api.routes.DashboardOverviewService",
        StubDashboardOverviewService,
    )

    response = client.get("/api/dashboard/overview?period=30d&channel=all")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "online"
    assert payload["period"] == "30d"
    assert payload["channel"] == "all"
    assert payload["summary"] is None
    assert payload["trafficBySource"] == []
    assert payload["conversionByChannel"] == []
    assert payload["insights"][0]["title"] == "Aguardando primeira sincronizacao"


def test_get_dashboard_overview_returns_summary_from_latest_snapshot(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    class StubDashboardOverviewService:
        def build_overview(self, *, period: str, channel: str):
            from app.schemas.api import (
                DashboardConversionPoint,
                DashboardInsight,
                DashboardOverviewResponse,
                DashboardOverviewSummary,
                DashboardTrafficChannelMetric,
                DashboardTrafficPoint,
            )

            return DashboardOverviewResponse(
                status="online",
                period=period,
                channel=channel,
                lastSnapshotAt="2026-05-05T23:44:13+00:00",
                summary=DashboardOverviewSummary(
                    totalUsers=3100,
                    totalOrders=112,
                    revenue=88400.0,
                    conversionRate=3.61,
                    topChannel="Organic Search",
                ),
                trafficBySource=[
                    DashboardTrafficPoint(
                        date="2026-04-01",
                        channels=[
                            DashboardTrafficChannelMetric(
                                channel="Organic Search",
                                visits=842,
                            ),
                            DashboardTrafficChannelMetric(
                                channel="Direct",
                                visits=420,
                            ),
                        ],
                    )
                ],
                conversionByChannel=[
                    DashboardConversionPoint(
                        channel="Organic Search",
                        conversionRate=4.8,
                    )
                ],
                insights=[
                    DashboardInsight(
                        type="success",
                        title="Melhor performance em Organic Search",
                        message="Organic Search lidera a conversao.",
                    )
                ],
            )

    monkeypatch.setattr(
        "app.api.routes.DashboardOverviewService",
        StubDashboardOverviewService,
    )

    response = client.get("/api/dashboard/overview?period=30d&channel=all")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["totalUsers"] == 3100
    assert payload["summary"]["totalOrders"] == 112
    assert payload["summary"]["revenue"] == 88400.0
    assert payload["summary"]["conversionRate"] == 3.61
    assert payload["summary"]["topChannel"] == "Organic Search"
    assert payload["trafficBySource"][0]["date"] == "2026-04-01"
    assert payload["trafficBySource"][0]["channels"] == [
        {"channel": "Organic Search", "visits": 842},
        {"channel": "Direct", "visits": 420},
    ]
    assert payload["conversionByChannel"][0] == {
        "channel": "Organic Search",
        "conversionRate": 4.8,
    }
    assert payload["insights"][0]["title"] == "Melhor performance em Organic Search"
