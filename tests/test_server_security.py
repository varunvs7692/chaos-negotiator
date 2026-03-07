"""Security-focused tests for HTTP server behavior."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from chaos_negotiator import server


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


def test_dashboard_endpoints_and_docs_return_json() -> None:
    """Dashboard endpoints and docs should be available for judges."""
    with TestClient(server.app) as client:
        risk_response = client.get("/api/dashboard/risk")
        history_response = client.get("/api/dashboard/history")
        canary_response = client.get("/api/dashboard/canary")
        docs_response = client.get("/docs")

    assert risk_response.status_code == 200
    risk_data = risk_response.json()
    assert {"risk_score", "risk_level", "confidence_percent"} <= set(risk_data.keys())

    assert history_response.status_code == 200
    history_data = history_response.json()
    assert {"total", "outcomes"} <= set(history_data.keys())
    assert isinstance(history_data["outcomes"], list)

    assert canary_response.status_code == 200
    canary_data = canary_response.json()
    assert {"deployment_id", "risk_score", "stages"} <= set(canary_data.keys())

    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]


def test_risk_websocket_streams_json_payload() -> None:
    """WebSocket risk stream should accept connections and send risk payloads."""
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws/risk") as websocket:
            message = websocket.receive_json()

    assert {"risk_score", "risk_level", "confidence_percent", "timestamp"} <= set(message.keys())
