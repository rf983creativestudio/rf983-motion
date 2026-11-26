# Local deployment guide

This Docker Compose stack is for local development, not public production.

## Requirements
- Docker Desktop or Docker Engine with Compose.
- Access to this private repository.
- A modern browser.

## Start
1. Copy `.env.example` to `.env`.
2. Replace `RF983_WORKER_TOKEN` with a long random value if testing worker registration.
3. Run `docker compose up --build`.
4. Open studio: `http://localhost:8080`.
5. Check API: `http://localhost:8000/api/health`.
6. Check readiness: `http://localhost:8000/api/system/ready`.

Ports bind to loopback only. Do not expose them publicly without TLS, authentication, firewall rules and rate limits.

## Stop
Run `docker compose down`. Browser drafts remain in that browser profile. No cloud project database or video storage is created.

## Troubleshooting
- Build error: ensure Docker is running, then retry.
- Port conflict: stop the other service or change the host-side mapping.
- Token missing: check root `.env` and restart Compose.
- Generation unavailable: expected. Worker heartbeat does not enable generation.
