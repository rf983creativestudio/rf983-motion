from pathlib import Path
import pytest
from worker.engine_contract import RenderRequest,RenderResult
from worker import wan22_adapter as module

def test_adapter_reports_missing_model_as_unavailable(monkeypatch,tmp_path):
    monkeypatch.setattr(module,"inspect_installation",lambda repo,ckpt:{"ready":False,"reasons":["weights missing"]})
    ready,reason=module.Wan22Adapter(tmp_path,tmp_path/"weights").is_available()
    assert not ready and "weights missing" in reason

def test_adapter_refuses_unsupported_profiles_before_running(monkeypatch,tmp_path):
    adapter=module.Wan22Adapter(tmp_path,tmp_path/"weights")
    monkeypatch.setattr(adapter,"is_available",lambda:(True,"ready"))
    with pytest.raises(ValueError,match="720p"):
        adapter.render(RenderRequest(prompt="A cinematic sunrise",resolution="1080p"),tmp_path/"out")

def test_adapter_maps_portrait_and_returns_contract(monkeypatch,tmp_path):
    adapter=module.Wan22Adapter(tmp_path,tmp_path/"weights")
    monkeypatch.setattr(adapter,"is_available",lambda:(True,"ready"))
    seen={}
    def command(python,repo,ckpt,prompt,output,size,seed):
        seen.update(output=output,size=size,seed=seed); return ["python","fake-wan"]
    monkeypatch.setattr(module,"build_command",command)
    def run(cmd,cwd,check):
        Path(seen["output"]).write_bytes(b"fake mp4")
        return type("Proc",(),{"returncode":0})()
    monkeypatch.setattr(module.subprocess,"run",run)
    monkeypatch.setattr(module.RenderArtifactValidator,"validate",lambda self,path:{"duration_seconds":5.0,"width":704,"height":1280,"fps":24.0})
    result=adapter.render(RenderRequest(prompt="A cinematic portrait sunrise",aspect_ratio="9:16",seed=42),tmp_path/"out")
    assert isinstance(result,RenderResult) and seen["size"]=="704*1280" and seen["seed"]==42
    assert result.model_id=="wan2.2-ti2v-5b" and result.height==1280
