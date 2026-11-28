# RF983 MOTION 2.2.0 — Wan 2.2 Cloud Adapter

Configure the worker with `RF983_ENGINE_ADAPTER=worker.wan22_adapter:create_adapter`, plus `RF983_WAN_REPO` and `RF983_WAN_CHECKPOINT` pointing to an already installed official Wan 2.2 TI2V-5B checkout and checkpoint directory.

The adapter uses the existing engine preflight and official CLI command builder. It supports 720p, 5-second, 24-fps text-to-video in 16:9 landscape or 9:16 portrait. Unsupported profiles fail rather than being silently approximated.

No repository or weights are downloaded and no hosted provider is contacted. The GPU host needs a compatible NVIDIA CUDA GPU, CUDA-enabled PyTorch, FFmpeg/ffprobe, the official Wan 2.2 source and full TI2V-5B weights.

The generic worker Docker image is only a CPU base. A GPU-specific runtime with compatible CUDA/PyTorch and model dependencies must be prepared separately. This code-level integration is not proof of an actual GPU render. No GPU, weights, provider account, or paid compute are provisioned by this release. Public Generate remains disabled until a real render and end-to-end delivery are verified.
