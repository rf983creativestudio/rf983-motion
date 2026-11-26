# RF983 MOTION — private cinematic studio

RF983 MOTION is a private, self-hostable foundation for a cinematic AI video-generation workspace.

## Build 0.4.0 — Engine integration and operations foundation
- Studio, Storyboard, My Projects and Model Lab creative workspace.
- Structured prompt controls, shot planning, local drafts and JSON export.
- FastAPI health, capabilities, readiness, model catalog and worker diagnostics.
- Authenticated worker heartbeat with 45-second expiry.
- Candidate model registry for Wan 2.2 TI2V 5B, Wan 2.2 I2V 14B and LTX-2.5.
- Read-only worker preflight for Python packages, FFmpeg, NVIDIA tooling and GPU query.
- Explicit provider-neutral engine adapter contract documented in the architecture plan.
- Request-size guard, baseline response security headers, Docker Compose local stack and API tests.

## Quick start — Docker Compose
Copy `.env.example` to `.env`, set a long random `RF983_WORKER_TOKEN`, then run:
```bash
docker compose up --build
```
Studio: `http://localhost:8080`; API: `http://localhost:8000`.

The included Compose stack binds to loopback and is for local development, not public production.

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

## Operations endpoints
- `GET /api/health` — API liveness.
- `GET /api/capabilities` — honest feature boundary and worker snapshot.
- `GET /api/system/ready` — production readiness gates.
- `GET /api/models` — candidate model catalog; not a claim that weights are installed.
- `GET /api/system/worker-preflight` — read-only environment diagnostics.
- `GET /api/worker/status` — heartbeat freshness.
- `POST /api/worker/heartbeat` — authenticated worker heartbeat using `X-Worker-Token`.
- `POST /api/generate` — deliberately returns 503 until inference is genuinely verified.

## Honest capability boundary
This build is a creative-planning and service-readiness platform, not yet a functioning AI video generator. There is no real model inference, GPU scheduler, durable job queue, user login, billing, cloud sync or render storage. A heartbeat or detected GPU is not a successful generation test.

## Model candidates
- [Wan 2.2](https://github.com/Wan-Video/Wan2.2) — includes a 5B text/image-to-video path targeting 720p at 24 fps; hardware must be tested.
- [LTX-2.5](https://github.com/Lightricks/LTX-2) — advanced audio/video pipelines; review exact checkpoint and dependency licensing.

## Security
- Keep this repository private.
- Never commit API keys, worker tokens, model weights, user images, generated videos or private logs.
- Keep inference credentials server-side; never put worker secrets in browser JavaScript.
- Configure exact allowed origins; default CORS is localhost only.
- Add user authentication, quotas, upload inspection, worker isolation and signed private result URLs before public access.
- Do not promise unlimited free generation: GPU compute, model storage and delivery bandwidth have real costs.

Project JSON exports do not embed reference-image files. Re-select a reference after importing or restoring a project.
