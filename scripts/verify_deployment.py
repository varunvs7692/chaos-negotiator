"""Lightweight verification script for local or public deployments."""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx


def check(response: httpx.Response, label: str) -> None:
    status = "PASS" if response.status_code == 200 else "FAIL"
    print(f"[{status}] {label}: {response.status_code}")
    if response.status_code != 200:
        print(response.text[:500])


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    evaluate_payload: dict[str, Any] = {
        "deployment_id": "verify-demo-001",
        "service_name": "verification-service",
        "environment": "production",
        "version": "v1.0.0",
        "changes": [
            {
                "file_path": "src/api/verify.py",
                "change_type": "modify",
                "lines_changed": 12,
                "risk_tags": ["api", "verification"],
                "description": "Verification deployment payload",
            }
        ],
    }

    try:
        with httpx.Client(base_url=base_url, timeout=20.0, follow_redirects=True) as client:
            checks = [
                ("GET /health", client.get("/health")),
                ("GET /api", client.get("/api")),
                ("GET /docs", client.get("/docs")),
                ("GET /api/dashboard/risk", client.get("/api/dashboard/risk")),
                ("GET /api/dashboard/history", client.get("/api/dashboard/history")),
                ("GET /api/dashboard/canary", client.get("/api/dashboard/canary")),
                (
                    "POST /api/deployments/evaluate",
                    client.post("/api/deployments/evaluate", json=evaluate_payload),
                ),
                ("GET /api/deployments/pending", client.get("/api/deployments/pending")),
            ]

            for label, response in checks:
                check(response, label)

            risk_response = client.get("/api/dashboard/risk")
            if risk_response.status_code == 200:
                print("\nDashboard risk payload:")
                print(json.dumps(risk_response.json(), indent=2)[:1200])

            return 0
    except Exception as exc:
        print(f"[FAIL] verification error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
