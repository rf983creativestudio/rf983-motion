# RF983 MOTION 1.7.0 — Production Control Room

## What it delivers
A single authenticated operational snapshot for the private backend:
- Worker online/offline state.
- Candidate and verified model counts.
- Registered/configured/verified engine counts.
- Queue counts by lifecycle state and the latest 30 job metadata records.
- SQLite storage persistence classification.

The browser UI can refresh this snapshot and cancel a non-terminal queue job. It does not enqueue jobs, return prompt payloads, upload assets, configure provider credentials, or contact inference providers.

## API
`GET /api/operations/control-room` requires `X-Operations-Token`. The response deliberately excludes queue payloads and secrets.

## Storage limitation
If the configured SQLite database is under `/tmp`, the API reports it as ephemeral. Render's current free container uses `/tmp/rf983-motion.sqlite3`, so queue and worker-history records may be lost on restart or redeploy. This release does not claim durable hosted persistence.

## Generation gate
Generation and provider calls remain disabled. Queue visibility and cancellation are operations features, not a functioning video renderer.
