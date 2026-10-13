from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_returns_service_name():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "support-agent-api"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
    assert "version" in response.json()
