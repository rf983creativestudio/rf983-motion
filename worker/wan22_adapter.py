"""Concrete adapter for an already-installed official Wan 2.2 TI2V-5B checkout."""
from __future__ import annotations
import os, subprocess
from datetime import datetime, timezone
from pathlib import Path
from .engine_contract import RenderRequest, RenderResult, RenderArtifactValidator
from .wan22_engine import DEFAULT_CHECKPOINT, DEFAULT_WAN_REPO, build_command, inspect_installation

class Wan22Adapter:
    model_id = "wan2.2-ti2v-5b"
    def __init__(self, wan_repo=None, checkpoint=None):
        self.wan_repo=Path(wan_repo or os.getenv("RF983_WAN_REPO",str(DEFAULT_WAN_REPO))).expanduser().resolve()
        self.checkpoint=Path(checkpoint or os.getenv("RF983_WAN_CHECKPOINT",str(DEFAULT_CHECKPOINT))).expanduser().resolve()
    def is_available(self):
        status=inspect_installation(self.wan_repo,self.checkpoint)
        if status.get("ready"): return True,"Wan 2.2 TI2V-5B, CUDA and checkpoint preflight passed."
        return False," ".join(str(x) for x in (status.get("reasons") or ["Wan preflight did not pass."]))[:700]
    def render(self,request:RenderRequest,output_dir:Path)->RenderResult:
        ready,reason=self.is_available()
        if not ready: raise RuntimeError("Wan adapter is not ready: "+reason)
        if request.resolution!="720p": raise ValueError("Wan 2.2 adapter currently supports the 720p profile only.")
        sizes={"16:9":"1280*704","9:16":"704*1280"}
        if request.aspect_ratio not in sizes: raise ValueError("Wan 2.2 adapter supports 16:9 and 9:16 only.")
        if request.duration_seconds!=5: raise ValueError("Wan TI2V-5B adapter currently supports the 5-second profile only.")
        if request.fps!=24: raise ValueError("Wan TI2V-5B adapter currently targets 24 fps output.")
        root=Path(output_dir).expanduser().resolve(); root.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output=root/("rf983-wan-"+stamp+".mp4")
        command=build_command(os.getenv("PYTHON","python"),self.wan_repo,self.checkpoint,request.prompt,output,sizes[request.aspect_ratio],request.seed)
        completed=subprocess.run(command,cwd=str(self.wan_repo),check=False)
        if completed.returncode!=0: raise RuntimeError("Wan 2.2 inference process failed with exit code "+str(completed.returncode))
        metadata=RenderArtifactValidator(root).validate(output)
        return RenderResult(output_path=output,model_id=self.model_id,duration_seconds=metadata["duration_seconds"],width=metadata["width"],height=metadata["height"],fps=metadata["fps"])

def create_adapter(): return Wan22Adapter()
