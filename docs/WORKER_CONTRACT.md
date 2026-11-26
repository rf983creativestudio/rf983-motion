# RF983 MOTION worker contract (0.3.0)

## Purpose
This defines an authenticated connectivity handshake for a separately hosted worker. It is not an inference implementation and does not create jobs.

## Configuration
Set `RF983_WORKER_TOKEN` on the API host to a long random secret. Never put it in frontend JavaScript, a committed file, a browser URL or a public issue. If empty, registration is disabled.

## Heartbeat
Send `POST /api/worker/heartbeat` with header `X-Worker-Token: <server-side secret>` and JSON body:

```json
{
  "worker_id": "local-gpu-01",
  "engine": "wan-ti2v-5b-adapter",
  "engine_ready": false,
  "capabilities": ["text-to-video", "image-to-video"]
}
```

Worker identifiers and payloads are bounded. A heartbeat is fresh for 45 seconds and must be renewed before expiry.

## Safety boundary
- Heartbeat is a liveness signal only.
- `engine_ready: true` is a worker-reported claim, not independent verification.
- `generation_enabled` remains false after a heartbeat.
- No prompt, reference image, model weight or video is sent here.
- Do not expose the API publicly without user authentication, TLS, rate limiting and monitoring.

## Required before generation
Add authenticated job claiming, leases, cancellation, progress, idempotency, durable state, bounded retries, output validation, private object storage and signed downloads. Run a pinned adapter in an isolated environment. Acceptance requires producing and retrieving a real playable video.
