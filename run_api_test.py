from fastapi.testclient import TestClient
from chaos_negotiator.agent import api

client = TestClient(api.app)
response = client.get("/api/deployments/latest")
print("status", response.status_code)
print(response.json())
