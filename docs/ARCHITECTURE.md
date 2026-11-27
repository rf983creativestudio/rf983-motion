# RF983 MOTION — architecture and release plan

## Build 0.4.0: engine integration foundation

### Browser application
- Studio, Storyboard, My Projects and Model Lab.
- Structured prompt composition, shot planning, local drafts and portable JSON export.
- Reference image preview is local only; there is no upload endpoint.

### API and operations
- FastAPI health, capability, readiness and model-catalog endpoints.
- Read-only worker preflight checks Python packages, FFmpeg, NVIDIA tooling and GPU query.
- Authenticated worker heartbeat with 45-second freshness window.
- Typed, bounded generation request schema and explicit 503 until inference is verified.
- CORS restricted to configured origins; request-size guard and security headers.
- Candidate catalog is explicitly separate from installed adapters and model weights.

## Target production architecture

```text
Private browser UI
      |
      | authenticated HTTPS
      v
API gateway / FastAPI
      |
      +---- Project metadata database
      |
      +---- Durable generation queue ---- Worker scheduler
      |                                      |
      |                                      v
      |                                Isolated GPU worker
      |                                      |
      |                                Model adapter layer
      |                                 /            \\
      |                             Wan 2.2        LTX-2.5
      |                                      |
      +---- Signed upload/download URLs
                                             |
                                      Private object storage
```

## Engine adapter contract
A future adapter must report exact task, aspect ratio, resolution, frame-rate and audio support; verify its checkpoint, dependencies, license and device; expose readiness; and return a real output file with metadata. Model imports belong in the isolated worker, not the API process.

## Candidate sequence
1. Wan 2.2 TI2V 5B for first hardware-tested text/image-to-video prototype.
2. Wan 2.2 I2V 14B only after real VRAM measurements.
3. LTX-2.5 for advanced audio/video evaluation with separate checkpoint-license review.

A dropdown selection or worker heartbeat never makes a model production-ready.

## Generation enablement gates
1. Verified adapter and exact checkpoint.
2. Hardware and dependency compatibility recorded.
3. Successful MP4 render validated with FFmpeg.
4. Durable job queue with leases, retries and cancellation.
5. Private result storage and retention policy.
6. User authentication, quotas, rate limits and audit trail.
7. Worker isolation, resource limits and safe upload handling.

Until every required gate is met, `/api/generate` must remain fail-closed.


## Build 1.1.0: durable queue primitive

The backend now includes a SQLite lease-based queue module. It provides atomic claims, worker ownership, lease renewal, bounded retries, expiry recovery, cancellation and terminal-state validation. Its payload/result records are bounded JSON metadata only.

This module is intentionally not wired to public generation routes or the local Wan CLI yet. It is not a distributed scheduler and does not enable generation. The next stage must add authenticated worker/API integration, cancellation signalling, idempotency, verified artifact registration and private result delivery before the API can accept real render jobs.
