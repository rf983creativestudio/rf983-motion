# RF983 MOTION 1.0.0 — Wan local engine bridge QA

## Automated checks
- [ ] Python compile check for worker modules.
- [ ] Unit tests for Wan CLI argument construction, input validation, seed validation, fail-closed hardware gate and output-path containment.
- [ ] Existing artifact validator tests remain green.
- [ ] Frontend JavaScript syntax check remains green.

## Compatible NVIDIA test machine (not available in CI)
- [ ] NVIDIA GPU and CUDA-enabled PyTorch each report at least 24 GB VRAM.
- [ ] Official Wan2.2 source and TI2V-5B checkpoint are installed locally.
- [ ] FFmpeg and ffprobe are available.
- [ ] `python wan22_engine.py --check` reports ready.
- [ ] Run a real 720p render, verify MP4 metadata with ffprobe, and play the file.
- [ ] Record actual runtime, peak VRAM, output size and any limitations.

## Current machine
The known Intel integrated-graphics laptop must fail the GPU readiness gate. This is expected and must not be reported as a test failure or a successful render.

## Release boundary
The local Wan CLI bridge is implemented, but it is not connected to the Studio button or API job system. Do not mark website generation as enabled until the full secure job pipeline and a real render acceptance test exist.
