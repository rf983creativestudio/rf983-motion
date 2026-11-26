# RF983 MOTION 0.9.0 — QA checklist

## Automated checks (GitHub Actions)
- [ ] Backend API tests pass, including private operations token enforcement.
- [ ] Worker engine contract tests pass.
- [ ] Python worker compile check passes.
- [ ] Frontend JavaScript syntax check passes.
- [ ] Root Docker deployment image builds.
- [ ] Deployment manifest and entrypoint files exist.

## Local Docker QA
- [ ] Copy `.env.example` to `.env`.
- [ ] Set distinct strong values for `RF983_WORKER_TOKEN` and `RF983_OPERATIONS_TOKEN`.
- [ ] Run `docker compose up --build`.
- [ ] Open `http://localhost:8080` and confirm the Studio loads.
- [ ] Open Model Lab; confirm API address defaults to the current origin.
- [ ] Run system check without an operations token: public health/model data should load, private machine information should remain locked.
- [ ] Enter the operations token and run system check: protected diagnostics/history should load.
- [ ] Confirm generation still remains disabled.
- [ ] Confirm worker heartbeat still requires the separate worker token.

## Render deployment QA (manual)
- [ ] Create Render Blueprint from the private GitHub repository.
- [ ] Confirm generated environment secrets exist and are not committed.
- [ ] Wait for `/api/health` health check.
- [ ] Open the public HTTPS URL on desktop and mobile.
- [ ] Confirm browser requests use the same-origin `/api/` route.
- [ ] Confirm private operations endpoints return 401 without the operations token.
- [ ] Confirm private operations endpoints work with the correct token.
- [ ] Confirm no worker IDs or machine diagnostics appear in public `/api/capabilities`.
- [ ] Confirm generation endpoint returns 503 until real inference infrastructure exists.

## Known deployment limitation
Render free-tier container filesystem is ephemeral. SQLite history stored under `/tmp` can be lost on restart/redeploy. A durable disk or external database is required for durable hosted operations history. This deployment does not include a GPU or real AI inference.
