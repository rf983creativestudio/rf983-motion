# RF983 MOTION — private cinematic studio

RF983 MOTION is a private, self-hostable foundation for a cinematic AI video-generation workspace.

## Build 0.3.0 — Operations and worker-readiness foundation
- Studio, Storyboard, My Projects and Model Lab creative workspace.
- Structured prompt controls, shot planning, local drafts and JSON export.
- FastAPI health, capability and system-readiness diagnostics.
- Authenticated worker heartbeat contract with 45-second expiry.
- Request-size guard and baseline response security headers.
- GitHub Actions API tests and frontend syntax checks.
- Docker Compose local development stack for API and studio UI.
- Generation remains disabled until a verified model adapter, durable queue, user authentication and private storage exist.

## Quick start — Docker Compose
Copy `.env.example` to `.env`, set a long random `RF983_WORKER_TOKEN`, then run:
```bash
docker compose up --build
```
Studio: `http://localhost:8080`; API: `http://localhost:8000`.

The included Compose stack binds to loopback and is for local development, not public production. See [Local deployment](docs/DEPLOYMENT.md).

## Run without Docker
Open `frontend/index.html` locally. To run the API:
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Health: `/api/health`; capabilities: `/api/capabilities`; readiness: `/api/system/ready`; docs: `/api/docs`.

## Worker contract
Workers may send an authenticated heartbeat to `POST /api/worker/heartbeat` using the `X-Worker-Token` header. This reports connectivity only; it does not create jobs or prove a model can render. See [Worker contract](docs/WORKER_CONTRACT.md).

## Honest capability boundary
This build is a creative-planning and service-readiness platform, not yet a functioning AI video generator. Generate remains blocked. There is no real model inference, GPU scheduler, durable queue, user login, billing, cloud sync or render storage. A worker heartbeat is not a successful generation test.

## Model candidates
- [Wan 2.2](https://github.com/Wan-Video/Wan2.2) — includes a 5B text/image-to-video path targeting 720p at 24 fps; hardware must be tested.
- [LTX-2.5](https://github.com/Lightricks/LTX-2) — advanced audio/video pipelines; review exact checkpoint and dependency licensing.

## Security
- Keep this repository private.
- Never commit API keys, worker tokens, model weights, user images, generated videos or private logs.
- Keep inference credentials server-side.
- Configure exact allowed origins; default CORS is localhost only.
- Add user authentication, quotas, upload inspection, worker isolation and signed private result URLs before public access.
- Do not promise unlimited free generation: GPU compute, model storage and delivery bandwidth have real costs.

Project JSON exports do not embed reference-image files. Re-select a reference after importing or restoring a project.
