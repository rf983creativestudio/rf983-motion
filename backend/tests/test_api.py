from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_reports_inference_offline():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["inference"] == "offline"

def test_capabilities_do_not_claim_generation():
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    assert response.json()["generation_enabled"] is False

def test_generation_fails_closed():
    response = client.post("/api/generate", json={"prompt": "A cinematic ocean scene"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "INFERENCE_NOT_CONFIGURED"

def test_invalid_prompt_is_rejected():
    response = client.post("/api/generate", json={"prompt": " "})
    assert response.status_code == 422
