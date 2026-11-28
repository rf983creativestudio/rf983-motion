# RF983 MOTION 2.3.0 — GPU Deployment Readiness

This release adds a read-only deployment preflight for a separately hosted cloud GPU machine. It never claims jobs, starts inference, contacts model providers, downloads weights, or prints credentials.

## Checks
- HTTPS API origin, worker-secret presence, valid worker ID, and explicit Wan adapter selection. Secret values are never printed.
- NVIDIA GPU visibility and a conservative 24 GB-class VRAM target (23,000 MiB floor), plus CUDA-enabled PyTorch visibility.
- Wan 2.2 repository entry point and checkpoint-file presence; FFmpeg/ffprobe; accessible output disk and free capacity.
- Redacted report with boolean checks, hardware metadata, checkpoint file count/size, and explicit no-execution flags.

The VRAM threshold is a deployment gate, not a guarantee. Real headroom depends on drivers, CUDA/PyTorch, model revision, resolution, offloading, and runtime configuration.

## Run
From the repository root on the intended GPU host, inject secrets through the host secret manager, then run:

```bash
python -m worker.gpu_readiness --check
python -m worker.cloud_worker --check
```

Required environment: RF983_API_BASE (HTTPS origin only), RF983_WORKER_TOKEN (secret), RF983_WORKER_ID, RF983_ENGINE_ADAPTER=worker.wan22_adapter:create_adapter, RF983_WAN_REPO, RF983_WAN_CHECKPOINT, and RF983_OUTPUT_DIR.

The generic Dockerfile.worker remains a CPU base. It does not include NVIDIA drivers, CUDA, CUDA-enabled PyTorch, Wan dependencies, or weights. Build a GPU image against the selected host's supported NVIDIA Container Toolkit/driver and a compatible CUDA/PyTorch combination. Pin and review those versions; this repository intentionally does not guess a universal image tag or download multi-gigabyte model files.

A successful preflight is necessary but not sufficient. It does not prove a real render, worker/API connectivity, durable queue/artifact storage, creator authentication, or private artifact delivery. No GPU host or provider is provisioned. Public generation remains disabled until production gates and an end-to-end render are verified.