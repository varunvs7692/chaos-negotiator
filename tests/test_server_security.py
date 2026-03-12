"""Security-focused tests for HTTP server behavior."""

import asyncio
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from chaos_negotiator import server
from chaos_negotiator.metrics.opentelemetry import (
    resolve_applicationinsights_connection_string,
)


def test_require_api_key_skips_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """When API_AUTH_KEY is unset, protected endpoints should not require a key."""
    monkeypatch.delenv("API_AUTH_KEY", raising=False)
    server._require_api_key_if_configured(None)


def test_require_api_key_rejects_missing_or_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """When API_AUTH_KEY is configured, missing/wrong key should be rejected."""
    monkeypatch.setenv("API_AUTH_KEY", "top-secret")

    with pytest.raises(HTTPException) as missing_key:
        server._require_api_key_if_configured(None)
    assert missing_key.value.status_code == 401

    with pytest.raises(HTTPException) as wrong_key:
        server._require_api_key_if_configured("wrong")
    assert wrong_key.value.status_code == 401


def test_require_api_key_accepts_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid API key should pass when protection is enabled."""
    monkeypatch.setenv("API_AUTH_KEY", "top-secret")
    server._require_api_key_if_configured("top-secret")


def test_security_headers_present() -> None:
    """Core security headers should be added to API responses."""
    with TestClient(server.app) as client:
        response = client.get("/api")

    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "no-referrer"


def test_health_endpoint_matches_judge_contract() -> None:
    """Health endpoint should expose the fixed public verification payload."""
    with TestClient(server.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "chaos-negotiator",
        "version": "1.0",
    }


def test_hackathon_proof_endpoint_exposes_core_requirement_mapping() -> None:
    """Submission proof endpoint should expose verifiable core requirement details."""
    with TestClient(server.app) as client:
        response = client.get("/api/hackathon/proof")

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "Chaos Negotiator"
    assert data["working_project"] is True
    assert data["azure_deployable"] is True
    assert "GitHub Actions CI/CD" in data["required_developer_tools"]
    assert "Azure Container Apps" in data["hero_technologies"]
    assert "Deployment risk evaluation API" in data["working_features"]


def test_resolve_applicationinsights_connection_string_prefers_explicit_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenTelemetry should use a provided connection string when available."""
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=abc;IngestionEndpoint=https://eastus.example",
    )
    monkeypatch.delenv("APPINSIGHTS_INSTRUMENTATIONKEY", raising=False)
    monkeypatch.delenv("APPINSIGHTS_INSTRUMENTATION_KEY", raising=False)

    assert (
        resolve_applicationinsights_connection_string()
        == "InstrumentationKey=abc;IngestionEndpoint=https://eastus.example"
    )


def test_resolve_applicationinsights_connection_string_builds_from_instrumentation_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenTelemetry should fall back to the deployed instrumentation key env names."""
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    monkeypatch.setenv("APPINSIGHTS_INSTRUMENTATIONKEY", "abc123")

    assert resolve_applicationinsights_connection_string() == "InstrumentationKey=abc123"


def test_analyze_alias_matches_evaluate_shape() -> None:
    """Both evaluate and analyze endpoints should behave as compatible APIs."""
    payload = {
        "deployment_id": "compat-test-001",
        "service_name": "compat-service",
        "environment": "staging",
        "version": "v0.0.1",
        "changes": [
            {
                "file_path": "src/smoke.py",
                "change_type": "modify",
                "lines_changed": 1,
                "risk_tags": ["test"],
            }
        ],
    }

    with TestClient(server.app) as client:
        evaluate_resp = client.post("/api/deployments/evaluate", json=payload)
        analyze_resp = client.post("/analyze", json=payload)

    assert evaluate_resp.status_code == 200
    assert analyze_resp.status_code == 200

    evaluate_data = evaluate_resp.json()
    analyze_data = analyze_resp.json()

    assert set(evaluate_data.keys()) == set(analyze_data.keys())
    assert (
        evaluate_data["deployment_id"] == analyze_data["deployment_id"] == payload["deployment_id"]
    )
    assert set(evaluate_data.keys()) == {
        "deployment_id",
        "risk_score",
        "risk_level",
        "confidence_percent",
        "canary_strategy",
    }
    assert set(evaluate_data["canary_strategy"].keys()) == {
        "deployment_id",
        "risk_score",
        "confidence_percent",
        "error_rate_threshold",
        "latency_threshold_ms",
        "rollback_on_violation",
        "stages",
    }


def test_evaluate_persists_pending_approval_and_can_be_decided() -> None:
    """Evaluations should create a pending approval record that can be approved or rejected."""
    payload = {
        "deployment_id": "approval-test-001",
        "service_name": "payment-service",
        "environment": "production",
        "version": "v1.2.3",
        "changes": [
            {
                "file_path": "api/payment.py",
                "change_type": "modify",
                "lines_changed": 120,
                "risk_tags": ["api", "database"],
            }
        ],
    }

    with TestClient(server.app) as client:
        evaluate_response = client.post("/api/deployments/evaluate", json=payload)
        pending_response = client.get("/api/deployments/pending")
        get_response = client.get(f"/api/deployments/{payload['deployment_id']}")
        approve_response = client.post(
            f"/api/deployments/{payload['deployment_id']}/approve",
            json={"reason": "Reviewed by release manager"},
        )
        reject_response = client.post(
            f"/api/deployments/{payload['deployment_id']}/reject",
            json={"reason": "Rollback proof missing"},
        )

    assert evaluate_response.status_code == 200

    assert pending_response.status_code == 200
    pending_data = pending_response.json()["deployments"]
    assert any(item["deployment_id"] == payload["deployment_id"] for item in pending_data)

    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["approval_status"] == "pending"
    stored_record = server.approval_store.get(payload["deployment_id"])
    assert stored_record is not None
    assert (
        stored_record["contract"]["deployment_context"]["service_name"] == payload["service_name"]
    )
    assert (
        stored_record["contract"]["deployment_context"]["changes"][0]["file_path"]
        == "api/payment.py"
    )

    assert approve_response.status_code == 200
    approve_data = approve_response.json()
    assert approve_data["approval_status"] == "approved"
    assert approve_data["decision_reason"] == "Reviewed by release manager"

    assert reject_response.status_code == 200
    reject_data = reject_response.json()
    assert reject_data["approval_status"] == "rejected"
    assert reject_data["decision_reason"] == "Rollback proof missing"


def test_github_webhook_ingests_workflow_run_into_evaluation() -> None:
    """GitHub workflow events should be translated into deployment evaluations."""
    payload = {
        "action": "completed",
        "workflow_run": {
            "id": 987654,
            "name": "deploy.yml",
            "head_sha": "abc123def4567890",
            "conclusion": "success",
        },
        "repository": {
            "name": "chaos-negotiator",
        },
    }

    with TestClient(server.app) as client:
        response = client.post(
            "/api/webhooks/github",
            headers={"X-GitHub-Event": "workflow_run"},
            json=payload,
        )
        pending_response = client.get("/api/deployments/pending")

    assert response.status_code == 200
    data = response.json()
    assert data["event"] == "workflow_run"
    assert data["status"] == "ingested"
    assert set(data["evaluation"].keys()) == {
        "deployment_id",
        "risk_score",
        "risk_level",
        "confidence_percent",
        "canary_strategy",
    }

    pending_ids = {item["deployment_id"] for item in pending_response.json()["deployments"]}
    assert data["deployment_id"] in pending_ids


def test_dashboard_endpoints_and_docs_return_json() -> None:
    """Dashboard endpoints and docs should be available for judges."""
    with TestClient(server.app) as client:
        root_response = client.get("/")
        dashboard_response = client.get("/dashboard")
        dashboard_html_response = client.get("/dashboard.html")
        legacy_dashboard_response = client.get("/static/dashboard.html")
        risk_response = client.get("/api/dashboard/risk")
        history_response = client.get("/api/dashboard/history")
        canary_response = client.get("/api/dashboard/canary")
        docs_response = client.get("/docs")

    assert root_response.status_code == 200
    assert "text/html" in root_response.headers["content-type"]
    assert dashboard_response.status_code == 200
    assert dashboard_response.text == root_response.text
    assert dashboard_html_response.status_code == 200
    assert dashboard_html_response.text == root_response.text
    assert legacy_dashboard_response.status_code == 200
    assert legacy_dashboard_response.text == root_response.text
    assert risk_response.status_code == 200
    risk_data = risk_response.json()
    assert {"risk_score", "risk_level", "confidence_percent"} <= set(risk_data.keys())
    assert {"telemetry_source", "telemetry_status", "service_name"} <= set(risk_data.keys())

    assert history_response.status_code == 200
    history_data = history_response.json()
    assert {"total", "outcomes"} <= set(history_data.keys())
    assert isinstance(history_data["outcomes"], list)

    assert canary_response.status_code == 200
    canary_data = canary_response.json()
    assert {"deployment_id", "risk_score", "stages"} <= set(canary_data.keys())
    assert {"telemetry_source", "telemetry_status"} <= set(canary_data.keys())

    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]


def test_dashboard_telemetry_prefers_deployed_service_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live telemetry should query the deployed app service, not the latest saved demo record."""
    monkeypatch.setattr(
        server,
        "_get_latest_dashboard_record",
        lambda: {
            "deployment_id": "smoke-deploy",
            "service_name": "smoke-service",
            "environment": "staging",
            "version": "v0.0.1",
            "contract": {"deployment_context": {"service_name": "smoke-service"}},
        },
    )
    monkeypatch.setattr(server.telemetry_client, "default_service_name", "chaos-negotiator")

    captured: dict[str, str] = {}

    async def fake_get_current_metrics(
        resource_id: str | None, metric_names: list[str], time_window_minutes: int = 5
    ) -> dict[str, object]:
        captured["resource_id"] = resource_id or ""
        return {
            "available": False,
            "source": "azure_monitor_no_data",
            "message": "no data",
            "error_rate_percent": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "qps": 0.0,
        }

    monkeypatch.setattr(server.telemetry_client, "get_current_metrics", fake_get_current_metrics)

    context, _, _ = asyncio.run(server._build_live_dashboard_context())

    assert captured["resource_id"] == "chaos-negotiator"
    assert context is not None
    assert context.service_name == "chaos-negotiator"


def test_risk_websocket_streams_json_payload() -> None:
    """WebSocket risk stream should accept connections and send risk payloads."""
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws/risk") as websocket:
            message = websocket.receive_json()

    assert {"risk_score", "risk_level", "confidence_percent", "timestamp"} <= set(message.keys())


def test_static_route_serves_nested_frontend_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Built frontend assets under static/static should be served correctly."""
    asset_dir = tmp_path / "static" / "js"
    asset_dir.mkdir(parents=True)
    asset_path = asset_dir / "main.js"
    asset_path.write_text("console.log('ok');", encoding="utf-8")

    monkeypatch.setattr(server, "STATIC_DIR", tmp_path)

    with TestClient(server.app) as client:
        response = client.get("/static/js/main.js")

    assert response.status_code == 200
    assert "console.log('ok');" in response.text
