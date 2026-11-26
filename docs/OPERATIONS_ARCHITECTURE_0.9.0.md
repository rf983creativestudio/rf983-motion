# RF983 MOTION 0.9.0 — public launch and operations security

## Single-service deployment
The root Dockerfile packages the static frontend, Nginx reverse proxy and FastAPI service into one container. Nginx listens on the hosting platform's `PORT`; FastAPI binds to container loopback on port 8000. Browser API calls are same-origin at `/api/*`.

## Access boundaries
- `RF983_WORKER_TOKEN` authenticates worker heartbeat writes via `X-Worker-Token`.
- `RF983_OPERATIONS_TOKEN` protects machine preflight, worker status, worker history and operations summary via `X-Operations-Token`.
- Tokens are separate and compared using constant-time `hmac.compare_digest`.
- CORS explicitly permits the operations header for trusted cross-origin local setups.
- Public capability output no longer contains worker IDs or machine diagnostic payloads.
- The frontend does not persist the operations token; it is held only in the current page's input and request flow.

## Public versus private endpoints
Public:
- `GET /api/health`
- `GET /api/capabilities` (sanitized worker state only)
- `GET /api/models` (candidate metadata only)
- `GET /api/system/ready` (production gates; never enables generation)

Private (operations token required):
- `GET /api/system/worker-preflight`
- `GET /api/worker/status`
- `GET /api/worker/history`
- `GET /api/operations/summary`

Worker write:
- `POST /api/worker/heartbeat` (worker token required)

## State durability
Local Docker Compose continues to mount a named SQLite volume. Render Blueprint uses `/tmp/rf983-motion.sqlite3` because the free service does not provision a persistent disk. Treat hosted history as temporary until a persistent disk or managed database is selected.

## Generation gate
No change enables video generation. A real production renderer still requires reviewed model licensing, verified weights, compatible hardware, a registered adapter, durable queue, user authentication and ownership, private result storage, resource limits, successful render validation and abuse controls.
