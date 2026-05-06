"""HTTP tests for the Glacier AI FastAPI layer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_post_ask_returns_successful_response(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.run_agent_question",
        lambda question: {
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


def test_post_ask_returns_out_of_scope_response(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.routes.run_agent_question",
        lambda question: {
            "intent": "out_of_scope",
            "tool_name": None,
            "tool_result": None,
            "answer": "Essa pergunta esta fora do escopo atual da V1.",
            "error": None,
            "out_of_scope_reason": "unsupported_intent",
        },
    )

    response = client.post("/ask", json={"question": "Me fale sobre CAC"})

    assert response.status_code == 200
    assert response.json()["used_tool"] is None
    assert response.json()["data"] is None
    assert response.json()["error"] == "unsupported_intent"


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
        lambda question: {
            "intent": "traffic_volume_by_source",
            "tool_name": "get_users_by_source",
            "tool_result": None,
            "answer": "Unsupported traffic_source. Allowed values: Search, Organic.",
            "error": "Unsupported traffic_source. Allowed values: Search, Organic.",
        },
    )

    response = client.post("/ask", json={"question": "Volume de TikTok"})

    assert response.status_code == 400
    assert response.json()["error"].startswith("Unsupported traffic_source")


def test_post_ask_returns_internal_error_for_unexpected_failure(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    def raise_error(question: str) -> dict:
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
        lambda question: {
            "intent": "best_channel_performance",
            "tool_name": "get_channel_performance_summary",
            "tool_result": None,
            "answer": "No local cache snapshot is available yet. Run the cache sync first.",
            "error": "local_cache_snapshot_not_found",
        },
    )

    response = client.post("/ask", json={"question": "Qual canal teve melhor performance?"})

    assert response.status_code == 503
    assert response.json()["error"] == "local_cache_snapshot_not_found"


def test_get_health_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


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
