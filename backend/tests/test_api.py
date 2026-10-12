from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_valid_url_analysis():
    response = client.post(
        "/api/v1/analyze",
        json={"url": "https://example.com/login?redirect=dashboard"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted_url"] == "https://example.com/login?redirect=dashboard"
    assert payload["analysis_method"] in {"rule-based fallback"}
    assert payload["model_status"] == "fallback-mode-active"


def test_url_without_scheme_is_normalized():
    response = client.post("/api/v1/analyze", json={"url": "example.com/login?redirect=dashboard"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["submitted_url"] == "https://example.com/login?redirect=dashboard"


def test_invalid_url_rejected():
    response = client.post("/api/v1/analyze", json={"url": "ftp://example.com"})
    assert response.status_code == 422
    assert "Only HTTP and HTTPS" in response.json()["detail"]


def test_model_status_exposes_metadata():
    response = client.get("/api/v1/model/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_mode_active"] is True
    assert payload["model_loaded"] is False
