# RF983 MOTION 0.7.0 — worker bridge acceptance checklist

## API protocol
- [ ] Start the API with a unique secret configured as `RF983_WORKER_TOKEN`.
- [ ] Confirm `GET /api/health` reports API version 0.7.0 and worker protocol 0.7.
- [ ] Confirm `GET /api/worker/status` reports offline before the agent starts.
- [ ] Confirm a missing or incorrect worker token is rejected.
- [ ] Confirm a valid heartbeat reports diagnostics but always returns `generation_enabled: false`.
- [ ] Confirm diagnostics disappear after the 45-second heartbeat expiry.

## Local preflight agent
- [ ] Run the agent on Windows, Linux or macOS with Python 3.11+.
- [ ] Confirm it reports OS, Python, CPU count, disk free space, FFmpeg, NVIDIA tooling, GPU query and ML package presence.
- [ ] Confirm it sends only machine diagnostics and worker identity; no prompt, project or image data.
- [ ] Stop the agent and confirm the API marks it stale after 45 seconds.

## Model Lab UI
- [ ] Open Model Lab and run the system check against the local API.
- [ ] Confirm the GPU worker row reflects heartbeat state.
- [ ] Confirm the machine preflight row shows reported GPU, FFmpeg and PyTorch status.
- [ ] Confirm generation remains disabled even if a GPU is detected.

## Engine contract
- [ ] Run `PYTHONPATH=.. python -m pytest ../worker/test_engine_contract.py` from the backend directory.
- [ ] Confirm path escape, empty file, wrong extension and size limit tests pass.
- [ ] On a controlled test machine with ffprobe, validate a known-good MP4 and a corrupt MP4.
- [ ] Confirm no adapter is registered and no model weights are downloaded automatically.

## Verification status
Source code and workflow changes were committed and retrieved from GitHub. The CI workflow now includes API tests, worker contract tests, Python compile checks and frontend syntax checks. This checklist is not a test report; do not claim CI or real hardware tests passed until the run is inspected.
