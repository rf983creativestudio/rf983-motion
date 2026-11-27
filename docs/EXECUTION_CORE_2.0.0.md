# RF983 MOTION 2.0.0 — Authenticated Execution Core

## What this release adds
- Authenticated worker claim endpoint: `POST /api/worker/jobs/claim`.
- Worker-only delivery of the queued creative payload after claim.
- Lease renewal endpoint: `POST /api/worker/jobs/{job_id}/heartbeat`.
- Worker failure reporting with bounded retry behavior: `POST /api/worker/jobs/{job_id}/fail`.
- Success finalization only after the same worker uploads a validated MP4 linked to the active job: `POST /api/worker/jobs/{job_id}/complete`.
- Artifact uploads linked to jobs now require the uploader to hold the current, unexpired job lease.
- Worker protocol identifier: `2.0`.

## Worker request headers
Every worker endpoint requires `X-Worker-Token` and a validated `X-Worker-ID`. Keep the token in the worker's secret environment; never put it in frontend code or send it in chat.

## Claim flow
1. Call `POST /api/worker/jobs/claim` with the worker token and worker ID headers.
2. If `claimed=false`, wait and poll later. If claimed, the response contains the job payload and lease expiry.
3. Renew the lease while working using `POST /api/worker/jobs/{job_id}/heartbeat`.
4. Upload the finished MP4 to `POST /api/worker/artifacts` with `Content-Type: video/mp4`, `X-Job-ID`, worker ID and token. The API validates the MP4 with ffprobe.
5. Finalize using `POST /api/worker/jobs/{job_id}/complete` with the returned artifact ID.
6. If execution fails, use `POST /api/worker/jobs/{job_id}/fail` with a bounded error code/message and retry choice.

## Safety and current limitations
- Job payloads are never exposed by public endpoints; only authenticated workers can claim them.
- A worker cannot renew, fail or complete another worker's lease.
- A job cannot be marked successful without a validated private artifact that is associated with the same job and worker.
- This is an execution control plane, not a running inference engine.
- No GPU provider is configured, no model weights are verified, no worker is deployed, and no real render has been completed.
- Generation remains disabled. `POST /api/generate` remains fail-closed with HTTP 503.
- Render's current temporary filesystem remains ephemeral. Persistent queue and artifact storage still need a durable database/volume or private object storage.
- No paid GPU service is activated by this release.
