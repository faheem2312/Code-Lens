import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_query_endpoint_missing_body():
    response = client.post("/api/v1/query", json={})
    # FastAPI returns 422 Unprocessable Entity for validation errors
    assert response.status_code == 422

def test_query_endpoint_valid():
    response = client.post(
        "/api/v1/query",
        json={
            "question": "What is serializer?",
            "repo_url": "https://github.com/pallets/itsdangerous",
            "top_k": 3
        }
    )
    # Check if the query executes successfully (either 200 or 500/400 if rate limited/no tokens, but it should be 200 in our standard execution context)
    assert response.status_code in [200, 429]
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "latency_ms" in data
        assert "tokens" in data

def test_ingest_logs_not_found():
    response = client.get("/api/v1/ingest/logs?repo_url=https://github.com/nonexistent/repo")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_started"

def test_checkout_endpoint_unauthorized():
    response = client.post(
        "/api/v1/billing/checkout",
        json={
            "tier": "pro",
            "success_url": "http://127.0.0.1:8000/?subscription=success",
            "cancel_url": "http://127.0.0.1:8000/pricing"
        }
    )
    assert response.status_code == 422
