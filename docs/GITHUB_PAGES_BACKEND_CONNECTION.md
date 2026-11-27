# Connect the GitHub Pages studio to the Render API

RF983 MOTION is split across two services:

- GitHub Pages serves the static studio: https://rf983creativestudio.github.io/rf983-motion/
- Render runs the FastAPI backend and reverse-proxy container.

## 1. Deploy the backend

1. Sign in to Render and connect the GitHub account that can access this repository.
2. Choose **New → Blueprint**.
3. Select `rf983creativestudio/rf983-motion` and the `render.yaml` Blueprint.
4. Review the `rf983-motion` web service and apply it.
5. Wait until the service is live and its `/api/health` health check succeeds.
6. Copy the service's HTTPS origin, for example `https://your-service.onrender.com`. Do not append `/api`.

The Blueprint configures `RF983_ALLOWED_ORIGINS=https://rf983creativestudio.github.io` so the GitHub Pages browser app can call the API. If you change the Pages domain, update this environment variable and redeploy.

## 2. Connect the live studio

1. Open the GitHub Pages studio.
2. Open **Model Lab → System control centre**.
3. Paste the Render HTTPS origin into **Backend service URL**.
4. Select **Connect & verify API**.
5. A successful check should show the API as connected and report the backend version, candidate models and generation readiness.

The non-secret backend address is saved in this browser for convenience. The operations token is not saved. It remains in page memory only.

## 3. What this connection does and does not do

It enables browser-side checks of public API health, model catalog and readiness. With the operations token, the private diagnostics panel can also request protected machine status and history.

It does **not** enable video generation. `POST /api/generate` remains deliberately disabled (HTTP 503); the private queue is not a public render endpoint, no GPU worker is connected, and no private video storage or user login exists yet.

## Free-tier note

Render's free web service may sleep when idle and take time to wake. Its configured SQLite path is ephemeral, so operational history may be lost after restarts or redeploys. No GPU compute is included.
