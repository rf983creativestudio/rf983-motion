# RF983 MOTION local compute tools

This folder contains two separate tools:

1. `worker.py` — lightweight diagnostics-only heartbeat agent for the RF983 API.
2. `wan22_engine.py` — guarded local execution bridge for official Wan 2.2 TI2V-5B text-to-video inference on a compatible NVIDIA GPU.

## Wan 2.2 local engine bridge

Read [Wan 2.2 engine setup](../docs/WAN22_ENGINE_SETUP.md) before installing anything.

Quick compatibility check (from this folder):

```sh
python wan22_engine.py --check
```

Only attempt a render after the check reports `"ready": true`:

```sh
python wan22_engine.py --prompt "A cinematic tracking shot through a rain-soaked neon city at night" --size 1280*704
```

The bridge calls the official Wan repository's `generate.py`, uses model offload options, saves to `worker/renders`, and validates the MP4 with ffprobe. It does not download weights, install CUDA/PyTorch, call an online provider or upload creative data.

**Hardware requirement:** Wan's official TI2V-5B guide specifies at least 24 GB NVIDIA VRAM for the single-GPU 720p path. Integrated Intel graphics and system RAM are not substitutes. The user's current Intel graphics laptop is not capable of this target.

## Diagnostics-only API heartbeat agent

This is a separate standard-library-only agent. It reports OS, Python version, CPU count, free disk, FFmpeg, NVIDIA tooling and selected Python package availability to the API. It never sends prompts, project contents or reference images.

### Requirements
- Python 3.11+
- A running RF983 MOTION API reachable from this computer
- The same private `RF983_WORKER_TOKEN` configured on the API and in `.env`

### Windows
1. Open the `worker` folder.
2. Double-click `start-windows.bat`.
3. Edit the created `.env` and set the same private token as the API.
4. Run the batch file again and keep its terminal open.

### Linux / macOS
Copy `.env.example` to `.env`, configure the token/API URL, then run `sh start-unix.sh`.

## Security
- Never commit a real `.env` file or share worker tokens.
- Keep the API on localhost or a trusted private network/VPN.
- Do not expose the worker token in browser JavaScript.
- Stop the heartbeat agent to stop reporting; the API marks it stale after 45 seconds.
