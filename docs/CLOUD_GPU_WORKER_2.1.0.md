# RF983 MOTION 2.1.0 — Cloud GPU Worker Runtime

## What this release adds

A standalone worker process for a separately hosted GPU machine. It connects to the RF983 MOTION API over HTTPS, authenticates with the existing worker token, claims private jobs, renews execution leases, validates MP4 output with ffprobe, streams the artifact upload, and marks the job complete only after the API accepts the artifact.

The runtime is provider-neutral. It does not create cloud machines, buy GPU time, call Replicate/fal.ai/RunPod, download model weights, or enable the public Generate endpoint.

## Required private environment variables

Set these as secret environment variables on the GPU worker host. Never put the worker token in GitHub source, frontend settings, or a chat message.

| Variable | Purpose |
|---|---|
| RF983_API_BASE | HTTPS API origin, e.g. https://rf983-motion.onrender.com |
| RF983_WORKER_TOKEN | Existing worker token from the API host's secret environment |
| RF983_WORKER_ID | Unique worker name, e.g. cloud-gpu-01 |
| RF983_ENGINE_ADAPTER | Installed Python adapter factory, module:function |
| RF983_OUTPUT_DIR | Private local render directory |

Optional: RF983_WORKER_POLL_SECONDS (default 5) and RF983_WORKER_LEASE_SECONDS (default 900; allowed 15–3600).

## Adapter contract

Install a reviewed Python module on the worker image and set RF983_ENGINE_ADAPTER to its factory. The factory must return an object with:

- model_id: non-empty string
- is_available() -> (bool, reason)
- render(RenderRequest, output_dir) -> RenderResult

Use shared definitions in worker/engine_contract.py. RenderResult.output_path must point to a completed MP4 inside output_dir. The runtime validates the file with ffprobe before upload.

The worker currently accepts text-to-video jobs only. Image conditioning and audio generation are rejected rather than silently ignored. An unavailable or missing adapter prevents startup, and the worker never claims jobs until startup checks pass.

## Runtime behavior and safety

- HTTPS API origin required; URL-embedded credentials and path prefixes are rejected.
- Worker token is sent only in request headers.
- Creative prompts are never written to worker logs.
- Job payloads are delivered only to the authenticated worker.
- Lease renewal runs during inference. If the lease is lost or the job is cancelled, the worker refuses to upload or complete the result.
- MP4 upload is streamed in 1 MiB chunks; large renders are not read into memory.
- ffprobe validation is mandatory.
- Errors are reported to the queue with bounded messages; retries remain bounded by the API queue.
- The runtime does not execute shell command strings or download arbitrary code.

## Build and check

Build the generic worker image:

```sh
docker build -f Dockerfile.worker -t rf983-motion-worker .
```

The image is a CPU-capable base image, not a GPU model image. A real model adapter and compatible CUDA/PyTorch stack must be installed into a GPU-specific image or environment. This base image does not contain CUDA, Wan weights, or a video model.

Check a configured worker without claiming jobs:

```sh
python -m worker.cloud_worker --check
```

Run it:

```sh
python -m worker.cloud_worker
```

## Current boundaries

- No cloud GPU provider is selected or provisioned.
- No real model adapter is included in this release.
- No GPU inference has been run or verified.
- No provider credential or billing account has been connected.
- Render's current API host still uses temporary storage unless a durable database and artifact volume are separately configured.
- The public Generate endpoint remains disabled until a real model render and end-to-end delivery test pass.
