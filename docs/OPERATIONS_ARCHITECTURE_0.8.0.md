# RF983 MOTION 0.8.0 — Operations architecture

## Persistent preflight ledger
The API stores authenticated worker heartbeat snapshots in a local SQLite database. WAL mode and a busy timeout support concurrent request handling. The ledger retains the latest 250 reports and exposes bounded reads (1–50 records).

Stored fields are worker ID, agent identifier, observation timestamp and JSON machine diagnostics. The worker protocol does not send creative prompts, project files or reference images. The API rejects a diagnostics JSON payload larger than 16 KB.

## Docker persistence
Docker Compose mounts a named volume at /app/runtime and points RF983_STATE_DB to that volume. Recreating containers preserves the ledger. Removing the named volume intentionally deletes it.

## Endpoints
- GET /api/worker/history?limit=12: bounded preflight history.
- GET /api/operations/summary: uptime, worker freshness, history count and generation state.

These endpoints are designed for local/private deployment. Keep the API loopback-bound or behind a trusted private network; do not expose machine diagnostics publicly.

## Explicit non-goals
SQLite history is not a generation queue, model registry, user account system, billing service, cloud storage or video renderer. /api/generate remains fail-closed until verified model inference, authenticated user ownership, durable job execution, private artifact storage and successful render validation are all implemented.
