# Wan 2.2 TI2V-5B local engine bridge

## What this adds

RF983 MOTION now has a guarded local execution bridge for the official Wan 2.2 TI2V-5B command-line inference program. It is a real invocation path, not a mock render. The bridge:

- Checks for an NVIDIA GPU, CUDA-enabled PyTorch, local Wan source, local checkpoint files, FFmpeg and ffprobe.
- Refuses to render unless the environment passes the checks.
- Calls the official Wan `generate.py` using a fixed argument list (never a shell command string).
- Writes output only inside the private `worker/renders` directory.
- Validates the resulting MP4 with the existing ffprobe artifact validator.
- Does not download code, model weights, or call a hosted API.

It is intentionally not wired to the public `/api/generate` endpoint yet. That endpoint remains fail-closed until job isolation, user authentication, durable queueing and private media delivery are built.

## Hardware reality

The official Wan 2.2 TI2V-5B instructions describe 720p / 24 fps generation and say the single-GPU path can run with at least 24 GB of NVIDIA VRAM. This is not satisfied by integrated Intel graphics or 24 GB of system RAM. The user's current Intel integrated graphics (reported 128 MB dedicated graphics memory) cannot run this cinematic model locally.

Official instructions: [Wan-Video/Wan2.2](https://github.com/Wan-Video/Wan2.2). The documented low-memory command uses model offload, dtype conversion and T5 on CPU. This reduces VRAM pressure but does not remove the NVIDIA GPU requirement.

## Prepare a compatible NVIDIA computer

1. Install a current NVIDIA driver and verify `nvidia-smi` works.
2. Install Python 3.10/3.11 in a dedicated environment compatible with the official Wan2.2 requirements.
3. Clone the official source into `third_party/Wan2.2` (do not copy it into this repository's tracked source):
   ```powershell
   git clone https://github.com/Wan-Video/Wan2.2.git third_party/Wan2.2
   ```
4. Follow the official repository's exact installation instructions for PyTorch/CUDA and its requirements. Do not blindly install CUDA packages into the existing RF983 API environment.
5. Download the Wan-AI/Wan2.2-TI2V-5B checkpoint to `models/Wan2.2-TI2V-5B` using the official Hugging Face or ModelScope instructions. The files are large; check disk space first. We intentionally do not auto-download them.
6. Install FFmpeg and make both `ffmpeg` and `ffprobe` available on PATH.
7. From the repository's `worker` directory, run:
   ```powershell
   py -3 wan22_engine.py --check
   ```
8. If every check passes, run a first local test:
   ```powershell
   py -3 wan22_engine.py --prompt "A cinematic aerial tracking shot over a dramatic coastline at golden hour, realistic ocean movement, atmospheric haze, natural film grain" --size 1280*704
   ```
   For portrait, use `--size 704*1280`. Optional reproducibility: `--seed 12345`.

The bridge uses the official TI2V-5B task at its documented 720p dimensions. It currently uses the official model's default frame count and 24 fps; the Studio duration slider is not yet passed through to this CLI. The official CLI also does not receive RF983's negative-prompt field in this first adapter.

## Windows quick check

Run `worker/setup-wan22-windows.bat` to check whether `nvidia-smi` exists and display a reminder. It does not install large dependencies or model weights.

## Privacy and cost

Prompts, model weights and generated files remain on the local compatible GPU computer when you run this bridge. No external inference API is called. Downloading model weights uses bandwidth and disk; rendering uses GPU electricity and time. The Wan model license and upstream code license must be reviewed before any redistribution or commercial use.

## Current boundaries

- This is a local CLI bridge, not an integrated Studio/API job queue.
- It is not usable on the current Intel integrated-graphics laptop.
- It does not make cloud GPU access free.
- It does not upload results or expose them as public URLs.
- A successful local test still needs to be recorded before enabling generation in the website.
