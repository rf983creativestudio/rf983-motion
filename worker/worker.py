"""RF983 MOTION 0.7 preflight agent. Reports hardware; never runs model inference."""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = os.getenv("RF983_API_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = os.getenv("RF983_WORKER_TOKEN", "")
WORKER_ID = os.getenv("RF983_WORKER_ID", socket.gethostname()[:70] or "local-worker")
INTERVAL = max(10, int(os.getenv("RF983_HEARTBEAT_SECONDS", "20")))


def command_output(args, timeout=5):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True)
        return result.stdout.strip()[:1600]
    except (OSError, subprocess.SubprocessError):
        return ""


def collect_diagnostics():
    tools = {name: shutil.which(name) is not None for name in ("git", "ffmpeg", "nvidia-smi")}
    packages = {name: importlib.util.find_spec(name) is not None for name in ("torch", "diffusers", "transformers", "safetensors")}
    gpu_text = command_output([
        "nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
        "--format=csv,noheader"
    ]) if tools["nvidia-smi"] else ""
    disk = shutil.disk_usage(Path.cwd())
    return {
        "protocol": "0.7",
        "platform": platform.platform()[:240],
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "tools": tools,
        "python_packages": packages,
        "gpu_detected": bool(gpu_text),
        "gpu_detail": gpu_text or ("nvidia-smi unavailable or no NVIDIA GPU detected"),
        "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        "inference_adapter": "none",
        "weights_present": False,
        "generation_capable": False,
        "reported_at": int(time.time()),
    }


def send_heartbeat():
    if not TOKEN:
        raise RuntimeError("RF983_WORKER_TOKEN is not set. Copy .env.example and configure a private token.")
    payload = {
        "worker_id": WORKER_ID,
        "engine": "rf983-preflight-agent/0.7",
        "engine_ready": False,
        "capabilities": ["hardware-preflight", "environment-diagnostics"],
        "diagnostics": collect_diagnostics(),
    }
    request = urllib.request.Request(
        API_BASE + "/api/worker/heartbeat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Worker-Token": TOKEN},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"API rejected heartbeat ({exc.code}): {detail}") from exc
    print(f"[{time.strftime('%H:%M:%S')}] Diagnostics sent to {API_BASE}; generation remains disabled.")
    print(json.dumps(payload["diagnostics"], indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="RF983 MOTION local hardware preflight agent")
    parser.add_argument("--once", action="store_true", help="Send one report and exit")
    args = parser.parse_args()
    print("RF983 MOTION preflight agent 0.7 — no model inference is performed.")
    if args.once:
        send_heartbeat()
        return
    while True:
        try:
            send_heartbeat()
        except Exception as exc:
            print(f"[{time.strftime('%H:%M:%S')}] Not connected: {exc}", file=sys.stderr)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
