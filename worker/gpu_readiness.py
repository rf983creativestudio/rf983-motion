"Non-invasive, redacted preflight for RF983 MOTION cloud GPU hosts."
from __future__ import annotations
import argparse, json, os, shutil
from pathlib import Path
from urllib.parse import urlparse
from .wan22_engine import inspect_installation

def inspect_deployment(env=None, wan_repo=None, checkpoint=None):
    env = os.environ if env is None else env
    status = inspect_installation(Path(wan_repo or env.get("RF983_WAN_REPO", "third_party/Wan2.2")), Path(checkpoint or env.get("RF983_WAN_CHECKPOINT", "models/Wan2.2-TI2V-5B")))
    parsed = urlparse(env.get("RF983_API_BASE", "").strip())
    api_ok = parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
    worker_id = env.get("RF983_WORKER_ID", "").strip()
    worker_id_ok = 3 <= len(worker_id) <= 80 and all(c.isalnum() or c in "._-" for c in worker_id)
    adapter_ok = env.get("RF983_ENGINE_ADAPTER", "").strip() == "worker.wan22_adapter:create_adapter"
    cp = Path(checkpoint or env.get("RF983_WAN_CHECKPOINT", "models/Wan2.2-TI2V-5B"))
    count = total = 0
    if cp.is_dir():
        for item in cp.rglob("*"):
            if item.is_file():
                try: count += 1; total += item.stat().st_size
                except OSError: pass
    try: free = int(shutil.disk_usage(Path(env.get("RF983_OUTPUT_DIR", "./renders")).expanduser()).free)
    except OSError: free = None
    gpu = status.get("gpu", {})
    checks = {
      "https_api_origin_configured": api_ok, "worker_token_present": bool(env.get("RF983_WORKER_TOKEN", "").strip()),
      "worker_id_valid": worker_id_ok, "wan_adapter_selected": adapter_ok,
      "nvidia_gpu_detected": bool(gpu.get("detected")), "gpu_vram_target_met": gpu.get("memory_mib", 0) >= 23000,
      "cuda_pytorch_available": bool(status.get("torch_installed") and status.get("cuda_available")),
      "wan_repository_present": bool(status.get("wan_generate_script")),
      "checkpoint_files_present": bool(status.get("checkpoint_files_present") and count),
      "ffmpeg_available": bool(status.get("ffmpeg")), "ffprobe_available": bool(status.get("ffprobe")),
      "output_disk_accessible": free is not None}
    try:
        import torch
        cuda_version = getattr(getattr(torch, "version", None), "cuda", None)
    except Exception: cuda_version = None
    blockers = [key for key, passed in checks.items() if not passed]
    return {"report":"rf983-motion-gpu-preflight", "ready_for_worker_start":not blockers, "checks":checks, "blockers":blockers,
      "hardware":{"gpu_name":gpu.get("name"), "gpu_vram_mib":gpu.get("memory_mib"), "pytorch_cuda_available":bool(status.get("cuda_available")), "pytorch_cuda_version":cuda_version},
      "model":{"model_id":"wan2.2-ti2v-5b", "checkpoint_file_count":count, "checkpoint_total_bytes":total},
      "storage":{"output_disk_free_bytes":free}, "execution":{"inference_started":False,"jobs_claimed":False,"provider_contacted":False}}

def main():
    parser = argparse.ArgumentParser(description="Read-only RF983 MOTION GPU deployment preflight")
    parser.add_argument("--check", action="store_true", help="Run checks only; this command never starts a worker.")
    parser.parse_args()
    report = inspect_deployment()
    print(json.dumps(report, indent=2))
    return 0 if report["ready_for_worker_start"] else 2

if __name__ == "__main__": raise SystemExit(main())