import sys, types
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from worker.cloud_worker import WorkerConfigError,load_config,load_adapter,CloudWorker

def valid_env(tmp_path):
    return {"RF983_API_BASE":"https://rf983-motion.onrender.com","RF983_WORKER_TOKEN":"x"*32,
        "RF983_WORKER_ID":"cloud-gpu-01","RF983_ENGINE_ADAPTER":"sample_adapter:create_adapter",
        "RF983_OUTPUT_DIR":str(tmp_path/"renders")}

def test_config_requires_https_and_secret(tmp_path):
    env=valid_env(tmp_path); env["RF983_API_BASE"]="http://example.com"
    with pytest.raises(WorkerConfigError,match="HTTPS"): load_config(env)
    env=valid_env(tmp_path); env["RF983_WORKER_TOKEN"]=""
    with pytest.raises(WorkerConfigError,match="TOKEN"): load_config(env)

def test_config_rejects_credentials_or_path_in_url(tmp_path):
    env=valid_env(tmp_path); env["RF983_API_BASE"]="https://user:password@example.com"
    with pytest.raises(WorkerConfigError): load_config(env)
    env=valid_env(tmp_path); env["RF983_API_BASE"]="https://example.com/prefix"
    with pytest.raises(WorkerConfigError): load_config(env)

def test_config_creates_output_directory(tmp_path):
    config=load_config(valid_env(tmp_path))
    assert config["worker_id"]=="cloud-gpu-01" and config["output_dir"].is_dir()
    assert config["lease_seconds"]==900

def test_adapter_must_be_explicit_and_available(monkeypatch):
    module=types.ModuleType("sample_adapter")
    class Adapter:
        model_id="test-only-adapter"
        def is_available(self): return True,"ready"
        def render(self,request,output_dir): raise AssertionError("test adapter must not render")
    module.create_adapter=Adapter
    monkeypatch.setitem(sys.modules,"sample_adapter",module)
    assert load_adapter("sample_adapter:create_adapter").model_id=="test-only-adapter"

def test_unavailable_adapter_fails_closed(monkeypatch):
    module=types.ModuleType("unavailable_adapter")
    class Adapter:
        model_id="not-ready"
        def is_available(self): return False,"model weights missing"
        def render(self,request,output_dir): pass
    module.create_adapter=Adapter
    monkeypatch.setitem(sys.modules,"unavailable_adapter",module)
    with pytest.raises(WorkerConfigError,match="not ready"): load_adapter("unavailable_adapter:create_adapter")

def test_image_and_audio_jobs_are_rejected(tmp_path):
    worker=CloudWorker(load_config(valid_env(tmp_path)),object())
    with pytest.raises(WorkerConfigError,match="text-to-video"):
        worker._render_request({"prompt":"A cinematic test","mode":"image"})
    with pytest.raises(WorkerConfigError,match="audio"):
        worker._render_request({"prompt":"A cinematic test","audio":True})
