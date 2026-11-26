# RF983 MOTION — private cinematic studio

RF983 MOTION is a private, self-hostable foundation for a cinematic AI video-generation workspace.

## Build 0.8.0 — Persistent operations and diagnostics history
- SQLite-backed worker preflight history, retained across API/container restarts when the Docker volume is kept.
- Bounded history retention (latest 250 reports) and 1–50 record query limit.
- Operations summary endpoint for uptime, worker state, history count and honest production-readiness state.
- Model Lab worker history timeline showing report time, worker ID, GPU detection, FFmpeg, Python and free disk.
- Docker named volume for persistent API state; no project prompts, images or videos are stored in this database.
- Generation remains disabled: persistent diagnostics are not a render queue or inference engine.

## Build 0.7.0 — Local compute bridge and render contract
- New standard-library-only local preflight agent for Windows, Linux and macOS.
- Token-authenticated worker heartbeat with machine, GPU, FFmpeg, Python package and disk diagnostics.
- Model Lab setup guide and live display of local machine preflight results.
- Strict engine adapter Protocol and render artifact validator: output-root containment, MP4 extension, non-empty file, size cap and ffprobe video-stream verification.
- Worker contract tests added to GitHub Actions.
- The worker is diagnostics-only. It does not install models or generate video; generation remains disabled.

## Connect a local worker
1. Start the API as described below and configure a strong `RF983_WORKER_TOKEN` in the root `.env`.
2. Copy `worker/.env.example` to `worker/.env` and use the same token. Keep both files private; they are git-ignored.
3. On Windows, run `worker/start-windows.bat`. On Linux/macOS, run `sh worker/start-unix.sh`.
4. Open Model Lab and run the system check. A fresh worker heartbeat should show machine diagnostics.

See [worker setup](worker/README.md) and [engine adapter contract](docs/ENGINE_ADAPTER_CONTRACT.md).

## Build 0.6.0 — Production desk and handoff exports
- Local pre-production audit for project identity, brief depth, shot actions, duplicate shot names, camera variety, negative prompt and reference-image status.
- Live planning metrics: shot count, storyboard runtime, frame estimate from runtime × target FPS, and checklist score.
- Director brief Markdown export with creative settings, director notes, shot-by-shot plan, pre-production findings and honest handoff limitations.
- Shot-list CSV export for spreadsheet review and production coordination.
- Structured production JSON export containing project metadata, planning estimates and audit findings.
- Exports are generated in the browser; no prompt, project or reference image is uploaded to a server.

## Build 0.5.0 — Creator workflow and portability
- Prompt direction heuristic with immediate writing cues (no AI API call).
- Visual sequence timeline driven by per-shot duration.
- Duplicate and reorder storyboard shots.
- Debounced local draft autosave while editing the prompt and storyboard.
- Import validated RF983 MOTION JSON project files; image files remain separate and must be re-selected.
- Existing export and local project library retained.

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
- `GET /api/worker/history?limit=12` — latest persisted worker preflight reports (maximum 50 per request; 250 retained).
- `GET /api/operations/summary` — operational summary and generation gate state.
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
