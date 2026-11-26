# RF983 MOTION 0.9.0 — public deployment guide

## What this deployment contains
The root Dockerfile packages the static studio and FastAPI service into one Render web service. Nginx serves the frontend and reverse-proxies same-origin `/api/*` requests to the API. The API listens only on container loopback; the platform-facing Nginx listener uses Render's `PORT`.

## Deploy with Render Blueprint
1. Keep the GitHub repository private and sign in to Render with access to it.
2. In Render, choose **New → Blueprint** and select `rf983creativestudio/rf983-motion`.
3. Review the service named `rf983-motion` and apply the Blueprint.
4. Wait for the Docker build and health check at `/api/health` to pass.
5. Open the generated `https://...onrender.com` URL.
6. In Render's service Environment page, reveal/copy `RF983_OPERATIONS_TOKEN`. Paste it into Model Lab's private operations token field when you want to inspect machine diagnostics or worker history. Do not put it in a public issue, commit, screenshot or frontend source.
7. Keep `RF983_WORKER_TOKEN` private too; the local worker must use the exact same value.

## Free-tier limitations
- Render free web services may spin down after inactivity and take time to wake up.
- The Blueprint stores SQLite at `/tmp/rf983-motion.sqlite3`. This is ephemeral storage: reports can be lost when the service restarts or redeploys. Durable persistent disks are a separate hosting capability and may incur cost.
- This deployment does not provide a GPU, install model weights, or enable video generation.
- Public deployment is not a substitute for user accounts, project ownership, quotas, private media storage or abuse controls. Do not accept sensitive uploads or expose generation until those are built.

## Same-origin API
The frontend detects its current origin in the Model Lab. Nginx routes `/api/` to the local FastAPI process, so a separate browser CORS origin is not required for the bundled deployment.

## Local Docker Compose
The existing two-container local workflow remains available. Copy `.env.example` to `.env`, set both private tokens, then run `docker compose up --build`. The local frontend's Nginx proxy sends `/api/` requests to the API container. The named SQLite volume remains persistent until explicitly removed.

## Security boundaries
- Worker heartbeat writes require `X-Worker-Token`.
- Machine preflight, worker status, worker history and operations summary require `X-Operations-Token`.
- Public capabilities no longer return worker IDs or hardware diagnostics.
- Operations token is entered into the Model Lab page and is not stored in localStorage/sessionStorage.
- Generation remains disabled. Never set an environment flag to bypass this gate.
