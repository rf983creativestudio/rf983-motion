from fastapi.testclient import TestClient
from app.main import app, _worker

client = TestClient(app)

def setup_function():
    _worker.update(connected=False, engine_ready=False, engine=None, worker_id=None, last_seen=None, capabilities=[], diagnostics={})

def test_health_reports_inference_offline():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["inference"] == "offline"
    assert response.json()["version"] == "2.4.0"

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
    assert data["api_version"] == "2.4.0"
    assert data["generation_enabled"] is False
    assert "verified_model_adapter" in data["production_blockers"]
    assert "creator_authentication" in data["production_blockers"]
    assert data["production_gates"]["successful_end_to_end_render"] is False

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
    assert data["api_version"]=="2.4.0" and data["persistent_state"]=="sqlite"
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


def test_engine_registry_is_provider_neutral_and_fail_closed():
    data = client.get("/api/engines").json()
    assert data["engine_count"] == 4
    assert data["configured_engine_count"] == 0
    assert data["verified_engine_count"] == 0
    assert data["generation_enabled"] is False
    assert data["provider_calls_enabled"] is False
    assert all(item["enabled"] is False for item in data["engines"])
    assert all("credential_env" in item for item in data["engines"])

def test_engine_detail_and_unknown_engine():
    found = client.get("/api/engines/custom-https")
    assert found.status_code == 200
    assert found.json()["engine"]["verified"] is False
    missing = client.get("/api/engines/not-real")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "ENGINE_NOT_FOUND"

def test_private_engine_status_requires_operations_token(monkeypatch):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN", "ops-secret")
    assert client.get("/api/operations/engine-status").status_code == 401
    response = client.get("/api/operations/engine-status", headers={"X-Operations-Token":"ops-secret"})
    assert response.status_code == 200
    assert response.json()["generation_enabled"] is False


def test_engine_evaluation_is_conservative_and_never_enables_generation():
    response = client.get("/api/engine-evaluation")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"]["decision"] == "hold"
    assert data["provider_calls_enabled"] is False
    assert data["generation_enabled"] is False
    assert data["benchmark_verified"] is False
    assert data["live_pricing_checked"] is False
    assert {item["id"] for item in data["engines"]} == {"replicate", "fal", "runpod", "custom-https"}


def test_control_room_requires_private_operations_token(monkeypatch):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN", "control-secret")
    response = client.get("/api/operations/control-room")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "OPERATIONS_AUTH_FAILED"


def test_control_room_returns_safe_queue_snapshot_without_prompt_payload(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.OPERATIONS_TOKEN", "control-secret")
    monkeypatch.setattr("app.main.STATE_DB", str(tmp_path / "control.sqlite3"))
    headers = {"X-Operations-Token": "control-secret"}
    created = client.post(
        "/api/operations/queue/jobs",
        headers=headers,
        json={"prompt": "Private cinematic test prompt"},
    )
    assert created.status_code == 202
    response = client.get("/api/operations/control-room", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["generation_enabled"] is False
    assert data["provider_calls_enabled"] is False
    assert data["creative_payloads_included"] is False
    assert data["queue"]["counts"]["queued"] == 1
    assert data["queue"]["items"][0]["status"] == "queued"
    assert "payload" not in data["queue"]["items"][0]
    assert "Private cinematic test prompt" not in response.text
    assert data["storage"]["ephemeral"] is True
    assert data["queue_storage"]["kind"] == "sqlite"
    assert data["queue_storage"]["ephemeral"] is True


def test_queue_database_can_be_configured_separately_from_worker_history(monkeypatch, tmp_path):
    from app.main import _jobs
    queue_path = str(tmp_path / "queue-only.sqlite3")
    monkeypatch.setattr("app.main.QUEUE_DB", queue_path)
    monkeypatch.setattr("app.main.STATE_DB", str(tmp_path / "history-only.sqlite3"))
    item = _jobs().enqueue({"prompt": "A cinematic test"})
    assert _jobs().get(item["id"])["status"] == "queued"
    assert _jobs().storage_info()["kind"] == "sqlite"


def test_private_artifact_upload_and_authenticated_retrieval(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-artifact-secret")
    monkeypatch.setattr(api,"OPERATIONS_TOKEN","ops-artifact-secret")
    monkeypatch.setattr(api,"ARTIFACT_DB",str(tmp_path/"artifacts.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DIR",str(tmp_path/"private-artifacts"))
    monkeypatch.setattr(api,"_probe_mp4",lambda path:{"width":1280,"height":720,"duration_seconds":4.5,"video_codec":"h264"})
    response=client.post("/api/worker/artifacts",content=b"test-mp4-bytes",headers={"Content-Type":"video/mp4","X-Worker-Token":"worker-artifact-secret","X-Worker-ID":"gpu-worker-01"})
    assert response.status_code==201
    item=response.json()["artifact"]
    assert item["size_bytes"]==len(b"test-mp4-bytes")
    assert item["width"]==1280 and item["video_codec"]=="h264"
    assert response.json()["public_url"] is None
    headers={"X-Operations-Token":"ops-artifact-secret"}
    listed=client.get("/api/operations/artifacts",headers=headers)
    assert listed.status_code==200 and listed.json()["count"]==1
    downloaded=client.get(f"/api/operations/artifacts/{item['id']}/download",headers=headers)
    assert downloaded.status_code==200 and downloaded.content==b"test-mp4-bytes"
    assert downloaded.headers["cache-control"]=="no-store"


def test_artifact_routes_require_their_private_tokens(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-secret")
    monkeypatch.setattr(api,"OPERATIONS_TOKEN","ops-secret")
    monkeypatch.setattr(api,"ARTIFACT_DB",str(tmp_path/"artifacts.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DIR",str(tmp_path/"private-artifacts"))
    upload=client.post("/api/worker/artifacts",content=b"data",headers={"Content-Type":"video/mp4","X-Worker-ID":"worker-01"})
    assert upload.status_code==401
    listing=client.get("/api/operations/artifacts")
    assert listing.status_code==401


def test_artifact_upload_rejects_non_mp4_and_unknown_job(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-secret")
    monkeypatch.setattr(api,"ARTIFACT_DB",str(tmp_path/"artifacts.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DIR",str(tmp_path/"private-artifacts"))
    headers={"X-Worker-Token":"worker-secret","X-Worker-ID":"worker-01","Content-Type":"application/octet-stream"}
    wrong_type=client.post("/api/worker/artifacts",content=b"nope",headers=headers)
    assert wrong_type.status_code==415
    headers["Content-Type"]="video/mp4"
    headers["X-Job-ID"]="missing-job"
    missing_job=client.post("/api/worker/artifacts",content=b"fake",headers=headers)
    assert missing_job.status_code==404


def test_control_room_reports_private_artifact_storage(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"OPERATIONS_TOKEN","ops-secret")
    monkeypatch.setattr(api,"ARTIFACT_DB",str(tmp_path/"artifacts.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DIR",str(tmp_path/"artifacts"))
    data=client.get("/api/operations/control-room",headers={"X-Operations-Token":"ops-secret"}).json()
    assert data["artifact_storage"]["kind"]=="private-local-filesystem"
    assert data["artifacts"]["count"]==0
    assert data["generation_enabled"] is False


def test_mp4_probe_rejects_unverified_video(monkeypatch):
    import app.main as api
    monkeypatch.setattr(api.shutil,"which",lambda name:"/usr/bin/ffprobe")
    class Failed:
        stdout='{"streams":[],"format":{"format_name":"wav","duration":"2"}}'
    monkeypatch.setattr(api.subprocess,"run",lambda *args,**kwargs:Failed())
    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException) as error:
        api._probe_mp4("/tmp/not-a-video.mp4")
    assert error.value.status_code==422


def test_worker_execution_claim_hides_payload_from_unauthenticated_clients(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-secret")
    monkeypatch.setattr(api,"OPERATIONS_TOKEN","ops-secret")
    monkeypatch.setattr(api,"STATE_DB",str(tmp_path/"execution.sqlite3"))
    queued=client.post("/api/operations/queue/jobs",headers={"X-Operations-Token":"ops-secret"},json={"prompt":"A cinematic mountain sunrise"})
    job_id=queued.json()["job"]["id"]
    denied=client.post("/api/worker/jobs/claim",headers={"X-Worker-ID":"gpu-node-01"})
    assert denied.status_code==401
    claimed=client.post("/api/worker/jobs/claim",headers={"X-Worker-Token":"worker-secret","X-Worker-ID":"gpu-node-01"})
    assert claimed.status_code==200
    assert claimed.json()["claimed"] is True
    assert claimed.json()["job"]["id"]==job_id
    assert claimed.json()["job"]["payload"]["prompt"]=="A cinematic mountain sunrise"
    assert claimed.json()["generation_enabled"] is False

def test_worker_execution_lease_renewal_and_expiry_guard(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-secret")
    monkeypatch.setattr(api,"STATE_DB",str(tmp_path/"lease.sqlite3"))
    job=api._jobs().enqueue({"prompt":"A cinematic ocean scene"})
    claimed=api._jobs().claim("gpu-node-01",lease_seconds=30)
    headers={"X-Worker-Token":"worker-secret","X-Worker-ID":"gpu-node-01"}
    renewed=client.post(f"/api/worker/jobs/{job['id']}/heartbeat",headers=headers)
    assert renewed.status_code==200 and renewed.json()["renewed"] is True
    wrong=client.post(f"/api/worker/jobs/{job['id']}/heartbeat",headers={"X-Worker-Token":"worker-secret","X-Worker-ID":"other-node"})
    assert wrong.status_code==409

def test_worker_cannot_complete_without_matching_validated_artifact(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-secret")
    monkeypatch.setattr(api,"OPERATIONS_TOKEN","ops-secret")
    monkeypatch.setattr(api,"STATE_DB",str(tmp_path/"complete.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DB",str(tmp_path/"artifacts.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DIR",str(tmp_path/"artifacts"))
    job=api._jobs().enqueue({"prompt":"A cinematic forest scene"})
    api._jobs().claim("gpu-node-01")
    headers={"X-Worker-Token":"worker-secret","X-Worker-ID":"gpu-node-01"}
    missing=client.post(f"/api/worker/jobs/{job['id']}/complete",headers=headers,json={"artifact_id":"a"*32})
    assert missing.status_code==404
    assert api._jobs().get(job["id"])["status"]=="running"

def test_worker_artifact_upload_requires_active_job_lease(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-secret")
    monkeypatch.setattr(api,"STATE_DB",str(tmp_path/"upload-lease.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DB",str(tmp_path/"upload-artifacts.sqlite3"))
    monkeypatch.setattr(api,"ARTIFACT_DIR",str(tmp_path/"artifacts"))
    job=api._jobs().enqueue({"prompt":"A cinematic city scene"})
    headers={"X-Worker-Token":"worker-secret","X-Worker-ID":"gpu-node-01","X-Job-ID":job["id"],"Content-Type":"video/mp4"}
    response=client.post("/api/worker/artifacts",headers=headers,content=b"video")
    assert response.status_code==409
    assert response.json()["detail"]["code"]=="JOB_LEASE_REQUIRED"

def test_worker_failure_endpoint_retries_only_with_valid_lease(monkeypatch,tmp_path):
    import app.main as api
    monkeypatch.setattr(api,"WORKER_TOKEN","worker-secret")
    monkeypatch.setattr(api,"STATE_DB",str(tmp_path/"failure.sqlite3"))
    job=api._jobs().enqueue({"prompt":"A cinematic desert scene"},max_attempts=2)
    api._jobs().claim("gpu-node-01")
    response=client.post(f"/api/worker/jobs/{job['id']}/fail",headers={"X-Worker-Token":"worker-secret","X-Worker-ID":"gpu-node-01"},json={"error_code":"ENGINE_NOT_READY","message":"No verified model adapter is configured.","retry":False})
    assert response.status_code==200
    assert response.json()["job"]["status"]=="failed"
