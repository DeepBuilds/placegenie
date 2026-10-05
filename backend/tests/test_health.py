from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_and_reports_database_block():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "connected" in body["database"]


def test_docs_available():
    assert client.get("/docs").status_code == 200
