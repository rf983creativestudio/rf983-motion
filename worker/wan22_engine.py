"""Safe local bridge to the official Wan 2.2 TI2V-5B inference CLI.

This adapter runs only on a compatible NVIDIA CUDA machine with local model
weights. It never downloads code/weights, calls a hosted API, or uploads prompts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from .engine_contract import ArtifactValidationError, RenderArtifactValidator
except ImportError:
    from engine_contract import ArtifactValidationError, RenderArtifactValidator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WAN_REPO = Path(os.getenv("RF983_WAN_REPO", str(ROOT / "third_party" / "Wan2.2")))
DEFAULT_CHECKPOINT = Path(os.getenv("RF983_WAN_CHECKPOINT", str(ROOT / "models" / "Wan2.2-TI2V-5B")))
DEFAULT_OUTPUT_ROOT = Path(os.getenv("RF983_RENDER_DIR", str(ROOT / "worker" / "renders")))
MIN_GPU_MEMORY_MIB = 23_000  # conservative floor for a marketed 24 GB GPU


class EngineNotReady(RuntimeError):
    pass


def probe_nvidia_gpu() -> dict:
    """Return first NVIDIA GPU name and total memory; never assumes Intel/AMD is CUDA."""
    if not shutil.which("nvidia-smi"):
        return {"detected": False, "reason": "nvidia-smi not found; an NVIDIA CUDA GPU is required."}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            check=True, capture_output=True, text=True, timeout=8,
        )
        first = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
        if not first:
            return {"detected": False, "reason": "No NVIDIA GPU was reported."}
        name, memory = [part.strip() for part in first.split(",", 1)]
        return {"detected": True, "name": name, "memory_mib": int(float(memory))}
    except (OSError, subprocess.SubprocessError, ValueError, StopIteration) as exc:
        return {"detected": False, "reason": "Could not query NVIDIA GPU: " + str(exc)[:180]}


def inspect_installation(wan_repo: Path, checkpoint: Path) -> dict:
    gpu = probe_nvidia_gpu()
    repo = wan_repo.expanduser().resolve()
    weights = checkpoint.expanduser().resolve()
    output = {
        "engine": "wan2.2-ti2v-5b",
        "gpu": gpu,
        "wan_repo": str(repo),
        "wan_generate_script": (repo / "generate.py").is_file(),
        "checkpoint_dir": str(weights),
        "checkpoint_files_present": weights.is_dir() and any(p.is_file() for p in weights.rglob("*")),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
        "python": sys.version.split()[0],
    }
    try:
        import torch
        output["torch_installed"] = True
        output["cuda_available"] = bool(torch.cuda.is_available())
        if output["cuda_available"]:
            output["cuda_device"] = torch.cuda.get_device_name(0)
            output["cuda_memory_mib"] = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
        else:
            output["cuda_device"] = None
            output["cuda_memory_mib"] = 0
    except Exception as exc:
        output["torch_installed"] = False
        output["cuda_available"] = False
        output["torch_error"] = str(exc)[:180]
        output["cuda_memory_mib"] = 0

    reasons = []
    if not gpu.get("detected"):
        reasons.append(gpu.get("reason", "NVIDIA GPU not detected."))
    elif gpu.get("memory_mib", 0) < MIN_GPU_MEMORY_MIB:
        reasons.append(f"GPU has {gpu.get('memory_mib', 0)} MiB; Wan TI2V-5B target is at least 24 GB VRAM.")
    if not output["wan_generate_script"]:
        reasons.append("Official Wan2.2 repository is missing generate.py.")
    if not output["checkpoint_files_present"]:
        reasons.append("Wan2.2-TI2V-5B checkpoint files are not installed.")
    if not output["ffmpeg"] or not output["ffprobe"]:
        reasons.append("FFmpeg and ffprobe must both be installed and on PATH.")
    if not output["torch_installed"] or not output["cuda_available"]:
        reasons.append("This Python environment needs a CUDA-enabled PyTorch installation.")
    if output.get("cuda_memory_mib", 0) < MIN_GPU_MEMORY_MIB:
        reasons.append("PyTorch does not report at least 24 GB of CUDA VRAM.")
    output["ready"] = not reasons
    output["reasons"] = reasons
    return output


def build_command(python_executable: str, wan_repo: Path, checkpoint: Path,
                  prompt: str, output: Path, size: str = "1280*704",
                  seed: int | None = None) -> list[str]:
    if size not in {"1280*704", "704*1280"}:
        raise ValueError("Wan TI2V-5B supports only the configured 720p landscape or portrait sizes here.")
    clean_prompt = prompt.strip()
    if not 5 <= len(clean_prompt) <= 4000:
        raise ValueError("Prompt must contain between 5 and 4000 characters.")
    command = [
        python_executable, str(wan_repo / "generate.py"),
        "--task", "ti2v-5B",
        "--size", size,
        "--ckpt_dir", str(checkpoint),
        "--offload_model", "True",
        "--convert_model_dtype",
        "--t5_cpu",
        "--prompt", clean_prompt,
        "--save_file", str(output),
    ]
    if seed is not None:
        if not 0 <= seed <= 2_147_483_647:
            raise ValueError("Seed must be between 0 and 2147483647.")
        command.extend(["--base_seed", str(seed)])
    return command


def run_generation(prompt: str, output: Path | None = None, size: str = "1280*704",
                   seed: int | None = None, wan_repo: Path = DEFAULT_WAN_REPO,
                   checkpoint: Path = DEFAULT_CHECKPOINT, dry_run: bool = False) -> dict:
    status = inspect_installation(wan_repo, checkpoint)
    if not status["ready"]:
        raise EngineNotReady("Wan engine is not ready: " + " ".join(status["reasons"]))
    output_root = DEFAULT_OUTPUT_ROOT.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = output_root / f"rf983-wan-{stamp}.mp4"
    output = output.expanduser().resolve()
    try:
        output.relative_to(output_root)
    except ValueError as exc:
        raise ValueError("Output must remain inside the private worker/renders directory.") from exc
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output filename must end in .mp4.")
    if output.exists():
        raise FileExistsError("Output already exists; choose a new filename.")
    command = build_command(sys.executable, wan_repo.resolve(), checkpoint.resolve(), prompt, output, size, seed)
    if dry_run:
        return {"dry_run": True, "command": command, "output": str(output), "engine": status}
    completed = subprocess.run(command, cwd=str(wan_repo.resolve()), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Official Wan2.2 process exited with code {completed.returncode}. See terminal output.")
    try:
        metadata = RenderArtifactValidator(output_root).validate(output)
    except ArtifactValidationError:
        raise
    return {"dry_run": False, "engine_id": "wan2.2-ti2v-5b", "artifact": metadata}


def main() -> int:
    parser = argparse.ArgumentParser(description="RF983 MOTION local Wan 2.2 TI2V-5B engine bridge")
    parser.add_argument("--check", action="store_true", help="Check GPU, CUDA, model files and FFmpeg; do not render.")
    parser.add_argument("--dry-run", action="store_true", help="Print the official inference command without running it.")
    parser.add_argument("--prompt", default="", help="Cinematic text-to-video prompt.")
    parser.add_argument("--output", type=Path, help="MP4 destination inside worker/renders.")
    parser.add_argument("--size", choices=["1280*704", "704*1280"], default="1280*704")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--wan-repo", type=Path, default=DEFAULT_WAN_REPO)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    args = parser.parse_args()
    if args.check:
        status = inspect_installation(args.wan_repo, args.checkpoint)
        print(json.dumps(status, indent=2))
        return 0 if status["ready"] else 2
    if not args.prompt.strip():
        parser.error("--prompt is required unless --check is used.")
    try:
        result = run_generation(args.prompt, args.output, args.size, args.seed,
                                args.wan_repo, args.checkpoint, args.dry_run)
        print(json.dumps(result, indent=2, default=str))
        return 0
    except Exception as exc:
        print(f"RF983 MOTION engine error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
