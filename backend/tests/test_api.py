from fastapi.testclient import TestClient
from app.main import app, _worker

client = TestClient(app)

def setup_function():
    _worker.update(connected=False, engine_ready=False, engine=None, worker_id=None, last_seen=None, capabilities=[])

def test_health_reports_inference_offline():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["inference"] == "offline"
    assert response.json()["version"] == "0.4.0"

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

def test_readiness_lists_production_gates():
    data = client.get("/api/system/ready").json()
    assert data["generation_enabled"] is False
    assert data["checks"]["durable_job_queue"] is False
    assert data["checks"]["user_authentication"] is False
    assert data["checks"]["successful_render_verified"] is False

def test_worker_registration_disabled_without_secret(monkeypatch):
    monkeypatch.setattr("app.main.WORKER_TOKEN", "")
    response = client.post("/api/worker/heartbeat", headers={"X-Worker-Token":"x"}, json={"worker_id":"gpu-node-1","engine":"test-engine"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WORKER_AUTH_NOT_CONFIGURED"

def test_worker_rejects_wrong_secret(monkeypatch):
    monkeypatch.setattr("app.main.WORKER_TOKEN", "right-secret")
    response = client.post("/api/worker/heartbeat", headers={"X-Worker-Token":"wrong"}, json={"worker_id":"gpu-node-1","engine":"test-engine"})
    assert response.status_code == 401

def test_worker_heartbeat_never_enables_generation(monkeypatch):
    monkeypatch.setattr("app.main.WORKER_TOKEN", "right-secret")
    response = client.post("/api/worker/heartbeat", headers={"X-Worker-Token":"right-secret"}, json={"worker_id":"gpu-node-1","engine":"test-engine","engine_ready":True,"capabilities":["text-to-video"]})
    assert response.status_code == 200
    assert response.json()["generation_enabled"] is False
    assert client.get("/api/capabilities").json()["generation_enabled"] is False
    assert client.get("/api/worker/status").json()["connected"] is True

def test_model_catalog_is_honest():
    data = client.get("/api/models").json()
    assert data["verified_model_count"] == 0
    assert data["generation_enabled"] is False
    assert all(model["status"] == "candidate" for model in data["models"])
    assert all(model["weights_present"] is False for model in data["models"])

def test_worker_preflight_does_not_claim_ready():
    data = client.get("/api/system/worker-preflight").json()
    assert data["generation_ready"] is False
    assert "gpu" in data
    assert "python_packages" in data

def test_security_headers_present():
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
