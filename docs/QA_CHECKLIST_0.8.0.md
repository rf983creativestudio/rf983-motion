# RF983 MOTION 0.8.0 — persistent operations acceptance checklist

## Persistent diagnostics
- [ ] Configure RF983_STATE_DB to a writable local path.
- [ ] Send an authenticated worker heartbeat and confirm it appears in /api/worker/history.
- [ ] Restart the API and confirm old history remains available.
- [ ] Confirm only the latest 250 heartbeat records are retained.
- [ ] Confirm limit accepts 1–50 and rejects values outside that range.
- [ ] Confirm oversized diagnostics are rejected and no secret/token field is stored.
- [ ] Confirm /api/operations/summary reports SQLite persistence and generation disabled.

## Docker persistence
- [ ] Run docker compose up --build.
- [ ] Send a worker heartbeat and confirm the history is visible.
- [ ] Recreate the API container without deleting volumes; confirm history remains.
- [ ] Do not use docker compose down -v unless intentionally deleting local state.

## Model Lab
- [ ] Run the system check and verify API, worker, GPU and model status rows.
- [ ] Confirm worker history shows timestamps and machine preflight facts.
- [ ] Confirm no prompt, project, reference image or generated video is shown in history.
- [ ] Confirm generation stays disabled even when a GPU is detected.

## Safety boundary
- [ ] /api/generate still returns 503 INFERENCE_NOT_CONFIGURED.
- [ ] /api/jobs/{job_id} still reports that the job service is not configured.
- [ ] No model weights, secrets, or user media are committed to Git.

## Verification status
This checklist defines acceptance tests; it is not evidence that they have run. Inspect the GitHub Actions run and test a local Docker restart before claiming runtime verification.
