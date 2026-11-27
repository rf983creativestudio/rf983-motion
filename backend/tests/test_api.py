from fastapi.testclient import TestClient
from app.main import app, _worker

client = TestClient(app)

def setup_function():
    _worker.update(connected=False, engine_ready=False, engine=None, worker_id=None, last_seen=None, capabilities=[], diagnostics={})

def test_health_reports_inference_offline():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["inference"] == "offline"
    assert response.json()["version"] == "1.3.0"

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
    assert data["checks"]["durable_job_queue"] is True
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
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN", "ops-secret")
    response = client.post("/api/worker/heartbeat", headers={"X-Worker-Token":"right-secret"}, json={"worker_id":"gpu-node-1","engine":"rf983-preflight-agent/0.7","engine_ready":True,"capabilities":["hardware-preflight"],"diagnostics":{"gpu_detected":True,"gpu_detail":"Test GPU","generation_capable":False}})
    assert response.status_code == 200
    assert response.json()["generation_enabled"] is False
    assert client.get("/api/capabilities").json()["generation_enabled"] is False
    status = client.get("/api/worker/status",headers={"X-Operations-Token":"ops-secret"}).json()
    assert status["connected"] is True
    assert status["diagnostics"]["gpu_detected"] is True
    assert status["engine_ready_reported"] is False

def test_model_catalog_is_honest():
    data = client.get("/api/models").json()
    assert data["verified_model_count"] == 0
    assert data["generation_enabled"] is False
    assert all(model["status"] == "candidate" for model in data["models"])
    assert all(model["weights_present"] is False for model in data["models"])

def test_worker_preflight_does_not_claim_ready(monkeypatch):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","ops-secret")
    data = client.get("/api/system/worker-preflight",headers={"X-Operations-Token":"ops-secret"}).json()
    assert data["generation_ready"] is False
    assert "gpu" in data
    assert "python_packages" in data

def test_security_headers_present():
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_worker_status_hides_stale_diagnostics(monkeypatch):
    from app.main import _worker
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","ops-secret")
    _worker.update(connected=True, last_seen=0, diagnostics={"gpu_detected": True})
    data = client.get("/api/worker/status",headers={"X-Operations-Token":"ops-secret"}).json()
    assert data["connected"] is False
    assert data["diagnostics"] == {}


def test_health_exposes_worker_protocol_version():
    data = client.get("/api/health").json()
    assert data["worker_agent_protocol"] == "0.7"


def test_worker_heartbeat_is_persisted(monkeypatch,tmp_path):
    monkeypatch.setattr("app.main.STATE_DB",str(tmp_path/"state.sqlite3"))
    monkeypatch.setattr("app.main.WORKER_TOKEN","history-secret")
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","ops-secret")
    response=client.post("/api/worker/heartbeat",headers={"X-Worker-Token":"history-secret"},
        json={"worker_id":"local-gpu-01","engine":"rf983-preflight-agent/0.7","diagnostics":{"gpu_detected":True,"gpu_detail":"Example GPU"}})
    assert response.status_code==200
    data=client.get("/api/worker/history?limit=5",headers={"X-Operations-Token":"ops-secret"}).json()
    assert data["count"]==1 and data["items"][0]["worker_id"]=="local-gpu-01"
    assert data["items"][0]["diagnostics"]["gpu_detected"] is True
    assert data["generation_enabled"] is False

def test_worker_history_rejects_invalid_limit(monkeypatch):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","ops-secret")
    response=client.get("/api/worker/history?limit=500",headers={"X-Operations-Token":"ops-secret"})
    assert response.status_code==422
    assert response.json()["detail"]["code"]=="INVALID_HISTORY_LIMIT"

def test_operations_summary_keeps_generation_disabled(monkeypatch,tmp_path):
    monkeypatch.setattr("app.main.STATE_DB",str(tmp_path/"ops.sqlite3"))
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","ops-secret")
    data=client.get("/api/operations/summary",headers={"X-Operations-Token":"ops-secret"}).json()
    assert data["api_version"]=="1.1.0" and data["persistent_state"]=="sqlite"
    assert data["generation_enabled"] is False


def test_private_operations_endpoints_require_token(monkeypatch):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","ops-secret")
    for path in ["/api/system/worker-preflight","/api/worker/status","/api/worker/history","/api/operations/summary"]:
        response=client.get(path)
        assert response.status_code==401
        assert response.json()["detail"]["code"]=="OPERATIONS_AUTH_FAILED"


def test_private_operations_endpoints_accept_token(monkeypatch,tmp_path):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","ops-secret")
    monkeypatch.setattr("app.main.STATE_DB",str(tmp_path/"private.sqlite3"))
    headers={"X-Operations-Token":"ops-secret"}
    for path in ["/api/system/worker-preflight","/api/worker/status","/api/worker/history","/api/operations/summary"]:
        assert client.get(path,headers=headers).status_code==200


def test_public_capabilities_do_not_expose_machine_diagnostics(monkeypatch):
    from app.main import _worker
    _worker.update(connected=True,last_seen=__import__("time").time(),worker_id="secret-node",diagnostics={"gpu_detail":"Private GPU info"})
    data=client.get("/api/capabilities").json()
    assert data["worker"]["worker_connected"] is True
    assert "diagnostics" not in data["worker"]
    assert "worker_id" not in data["worker"]


def test_private_queue_endpoints_require_operations_token(monkeypatch):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","queue-secret")
    response=client.post("/api/operations/queue/jobs",json={"prompt":"A cinematic ocean scene"})
    assert response.status_code==401

def test_private_queue_lifecycle(monkeypatch,tmp_path):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","queue-secret")
    monkeypatch.setattr("app.main.STATE_DB",str(tmp_path/"queue.sqlite3"))
    headers={"X-Operations-Token":"queue-secret"}
    created=client.post("/api/operations/queue/jobs",headers=headers,json={"prompt":"A cinematic ocean scene","duration_seconds":8})
    assert created.status_code==202
    body=created.json()
    assert body["accepted"] is True and body["generation_enabled"] is False
    job_id=body["job"]["id"]
    listed=client.get("/api/operations/queue/jobs",headers=headers).json()
    assert listed["items"][0]["id"]==job_id
    detail=client.get(f"/api/operations/queue/jobs/{job_id}",headers=headers).json()
    assert detail["job"]["payload"]["duration_seconds"]==8
    cancelled=client.post(f"/api/operations/queue/jobs/{job_id}/cancel",headers=headers)
    assert cancelled.status_code==200 and cancelled.json()["job"]["status"]=="cancelled"
    again=client.post(f"/api/operations/queue/jobs/{job_id}/cancel",headers=headers)
    assert again.status_code==409

def test_private_queue_unknown_job_returns_404(monkeypatch,tmp_path):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN","queue-secret")
    monkeypatch.setattr("app.main.STATE_DB",str(tmp_path/"queue.sqlite3"))
    response=client.get("/api/operations/queue/jobs/missing",headers={"X-Operations-Token":"queue-secret"})
    assert response.status_code==404

def test_generate_endpoint_stays_disabled_after_queue_added():
    response=client.post("/api/generate",json={"prompt":"A cinematic ocean scene"})
    assert response.status_code==503
    assert response.json()["detail"]["code"]=="INFERENCE_NOT_CONFIGURED"
