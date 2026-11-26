"""Read-only local worker preflight; it never downloads weights or starts inference."""
import importlib.util
import json
import os
import platform
import shutil
import subprocess


def inspect_worker():
    report = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "disk_free_bytes": None,
        "tools": {
            "git": shutil.which("git") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "nvidia_smi": shutil.which("nvidia-smi") is not None,
        },
        "python_packages": {
            name: importlib.util.find_spec(name) is not None
            for name in ("torch", "diffusers", "transformers", "safetensors")
        },
        "gpu": {"detected": False, "detail": "CUDA/GPU has not been verified."},
        "generation_ready": False,
        "reason": "No production model adapter is installed or verified.",
    }
    try:
        report["disk_free_bytes"] = shutil.disk_usage(os.getcwd()).free
    except OSError:
        pass
    if report["tools"]["nvidia_smi"]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                 "--format=csv,noheader"],
                check=True, capture_output=True, text=True, timeout=5,
            )
            report["gpu"] = {
                "detected": bool(result.stdout.strip()),
                "detail": result.stdout.strip()[:1000],
            }
        except (OSError, subprocess.SubprocessError):
            report["gpu"]["detail"] = "nvidia-smi exists but the GPU query failed."
    return report


if __name__ == "__main__":
    print(json.dumps(inspect_worker(), indent=2))
