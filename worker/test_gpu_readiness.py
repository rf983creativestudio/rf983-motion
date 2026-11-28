from types import SimpleNamespace
from worker import gpu_readiness

def fake_status(*args):
    return {"gpu":{"detected":True,"name":"Test NVIDIA GPU","memory_mib":24576},"torch_installed":True,"cuda_available":True,"wan_generate_script":True,"checkpoint_files_present":True,"ffmpeg":True,"ffprobe":True}

def test_ready_report_is_redacted_and_does_not_execute(monkeypatch, tmp_path):
    checkpoint=tmp_path/"weights"; checkpoint.mkdir(); (checkpoint/"model.safetensors").write_bytes(b"weights")
    monkeypatch.setattr(gpu_readiness,"inspect_installation",fake_status)
    monkeypatch.setattr(gpu_readiness.shutil,"disk_usage",lambda p:SimpleNamespace(total=100,used=10,free=90))
    env={"RF983_API_BASE":"https://api.example.test","RF983_WORKER_TOKEN":"private-token-value","RF983_WORKER_ID":"gpu-worker-01","RF983_ENGINE_ADAPTER":"worker.wan22_adapter:create_adapter","RF983_OUTPUT_DIR":str(tmp_path)}
    report=gpu_readiness.inspect_deployment(env,tmp_path/"repo",checkpoint)
    assert report["ready_for_worker_start"]
    assert "private-token-value" not in str(report) and str(checkpoint) not in str(report)
    assert report["execution"]=={"inference_started":False,"jobs_claimed":False,"provider_contacted":False}
    assert report["model"]["checkpoint_file_count"]==1

def test_missing_host_prerequisites_block_readiness(monkeypatch,tmp_path):
    monkeypatch.setattr(gpu_readiness,"inspect_installation",lambda *a:{"gpu":{"detected":False,"memory_mib":0},"torch_installed":False,"cuda_available":False,"wan_generate_script":False,"checkpoint_files_present":False,"ffmpeg":False,"ffprobe":False})
    monkeypatch.setattr(gpu_readiness.shutil,"disk_usage",lambda p:SimpleNamespace(total=1,used=1,free=0))
    report=gpu_readiness.inspect_deployment({},tmp_path/"repo",tmp_path/"missing")
    assert not report["ready_for_worker_start"]
    assert "nvidia_gpu_detected" in report["blockers"] and "https_api_origin_configured" in report["blockers"]

def test_rejects_http_and_url_credentials(monkeypatch,tmp_path):
    monkeypatch.setattr(gpu_readiness,"inspect_installation",fake_status)
    monkeypatch.setattr(gpu_readiness.shutil,"disk_usage",lambda p:SimpleNamespace(total=1,used=0,free=1))
    env={"RF983_WORKER_TOKEN":"x"*32,"RF983_WORKER_ID":"gpu-worker-01","RF983_ENGINE_ADAPTER":"worker.wan22_adapter:create_adapter"}
    for url in ("http://api.example.test","https://user:pass@api.example.test"):
        report=gpu_readiness.inspect_deployment({**env,"RF983_API_BASE":url},tmp_path/"repo",tmp_path/"weights")
        assert not report["checks"]["https_api_origin_configured"]