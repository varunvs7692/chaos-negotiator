from fastapi.testclient import TestClient

from chaos_negotiator.agent import api


def test_latest_deployment_endpoint_returns_structure():
    client = TestClient(api.app)
    # include Origin to trigger CORS middleware
    response = client.get("/api/deployments/latest", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    data = response.json()

    # ensure expected keys are present and values have correct types
    expected_keys = [
        "service",
        "risk_percent",
        "confidence_percent",
        "risk_level",
        "canary_stage",
        "traffic_percent",
    ]
    assert all(k in data for k in expected_keys)

    assert isinstance(data["service"], str)
    assert isinstance(data["risk_percent"], (int, float))
    assert isinstance(data["confidence_percent"], (int, float))
    assert isinstance(data["risk_level"], str)
    assert isinstance(data["canary_stage"], str)
    assert isinstance(data["traffic_percent"], (int, float))

    # risk value should not be zero for our demo context
    assert data["risk_percent"] > 0
    # initial stage should match one of expected names
    assert data["canary_stage"] in ["smoke", "light", "half", "majority", "full"]

    # because we may call from the React dev server, CORS middleware should echo Origin header
    assert response.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")
