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

def test_ingest_quota_limit(monkeypatch):
    from src.api.auth import user_manager, create_access_token
    import uuid
    email = f"test_quota_{uuid.uuid4().hex[:6]}@example.com"
    
    # Mock user_manager.get_user to simulate exceeded quota
    mock_user = {
        "user_id": "usr_test123",
        "email": email,
        "repos_indexed": 3,
        "repo_limit": 3,
        "tier": "free"
    }
    monkeypatch.setattr(user_manager, "get_user", lambda e: mock_user)
    
    token = create_access_token({"sub": email, "user_id": "usr_test123", "tier": "free"})
    
    response = client.post(
        "/api/v1/ingest",
        json={"repo_url": "https://github.com/pallets/click", "repo_path": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "limit" in response.json()["detail"].lower()

def test_incremental_indexing(tmp_path):
    repo_url = "https://github.com/mock-user/mock-repo"
    
    file1 = tmp_path / "foo.py"
    file1.write_text("def hello():\n    print('world')\n")
    
    file2 = tmp_path / "bar.py"
    file2.write_text("def goodbye():\n    print('bye')\n")
    
    from src.ingestion.indexer import index_repository
    # Index the repo first time
    res = index_repository(str(tmp_path), repo_url)
    assert res["total_found"] == 2
    assert res["indexed"] == 2
    assert res["skipped"] == 0

    # Index again with no changes: both should be skipped!
    res_skip = index_repository(str(tmp_path), repo_url)
    assert res_skip["total_found"] == 2
    assert res_skip["indexed"] == 0
    assert res_skip["skipped"] == 2
    
    # Modify one file and delete another
    file1.write_text("def hello_new():\n    print('new world!')\n")
    file2.unlink()
    
    res_inc = index_repository(str(tmp_path), repo_url)
    assert res_inc["total_found"] == 1
    assert res_inc["indexed"] == 1
    assert res_inc["skipped"] == 0

def test_user_repositories_endpoints():
    from src.api.auth import user_manager, create_access_token
    import uuid
    email = f"test_repos_{uuid.uuid4().hex[:6]}@example.com"
    user = user_manager.register_user(email, "pass1234")
    token = create_access_token({"sub": email, "user_id": user["user_id"], "tier": "free"})
    
    # 1. Add repository manually to user's database
    user_manager.add_user_repository(email, "https://github.com/pallets/click")
    
    # 2. Query endpoint
    response = client.get(
        "/api/v1/user/repositories",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "repositories" in data
    assert "https://github.com/pallets/click" in data["repositories"]
    
    # 3. Delete endpoint
    del_res = client.delete(
        "/api/v1/user/repositories?repo_url=https://github.com/pallets/click",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res.status_code == 200
    
    # 4. Verify unlinked
    response2 = client.get(
        "/api/v1/user/repositories",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert "https://github.com/pallets/click" not in response2.json()["repositories"]


def test_query_stream_endpoint(monkeypatch):
    def fake_stream(question, repo_url, top_k=8):
        yield {"type": "metadata", "sources": ["src/main.py"], "chunks": []}
        yield {"type": "token", "token": "Hello "}
        yield {"type": "token", "token": "world!"}
        yield {"type": "done", "latency_ms": 120, "tokens": 2}

    monkeypatch.setattr("src.query.query_codelens_stream", fake_stream)

    response = client.post(
        "/api/v1/query/stream",
        json={"question": "How does it work?", "repo_url": "https://github.com/pallets/flask"}
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "data: {\"type\": \"metadata\"" in content
    assert "data: {\"type\": \"token\", \"token\": \"Hello \"}" in content
    assert "data: {\"type\": \"done\"" in content
