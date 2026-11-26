# RF983 MOTION local preflight worker (0.7)

This is a **diagnostics-only agent**. It reports your local operating system, Python version, CPU count, free disk space, FFmpeg availability, NVIDIA tooling, and selected Python ML package availability to your RF983 MOTION API.

It does **not** download model weights, install CUDA/PyTorch, run inference, create videos, or enable generation.

## Requirements
- Python 3.11+
- A running RF983 MOTION API reachable from this computer
- The same private `RF983_WORKER_TOKEN` configured on the API and in this worker's local `.env`

The agent uses only Python's standard library.

## Windows
1. Start your API using the existing backend instructions.
2. Open the `worker` folder.
3. Double-click `start-windows.bat`.
4. On first run, edit the created `.env` and paste the same secret used by the API.
5. Start the batch file again. Keep its terminal open while you want diagnostics reported.

## Linux / macOS
1. Start the API.
2. Copy `.env.example` to `.env` and edit the token/API URL.
3. Run `sh start-unix.sh`.

## One-shot report
After creating the Python environment and setting the environment variables, run:

```sh
python worker.py --once
```

## Security
- Never commit your real `.env` file or share your worker token.
- Keep the API bound to localhost or behind a trusted private network/VPN.
- Do not expose the worker token in the browser frontend.
- The API rejects missing or incorrect tokens.
- The worker only sends heartbeat metadata; no prompts, project contents or reference images are sent.
- Stop the worker process to stop reporting. The API marks its heartbeat stale after 45 seconds.

## Current limitation
A fresh worker heartbeat proves only that this diagnostics agent can reach the API. It does not prove model compatibility or rendering readiness. Generation stays disabled until a reviewed model adapter, verified weights, durable job handling, private render storage and successful render validation exist.
