# Generation job queue contract (Build 1.1.0)

RF983 MOTION now contains a provider-neutral SQLite job-store module at
`backend/app/job_store.py`. It is a durable queue primitive, not yet a live
generation API or worker scheduler.

## Lifecycle

`queued → running → succeeded | failed | cancelled`

- Workers claim jobs atomically using SQLite `BEGIN IMMEDIATE`.
- Each claim has a worker identity, expiry lease and bounded attempt budget.
- Workers may extend only their own unexpired lease.
- Only the currently leased worker may complete or fail a job.
- Expired leases return to the queue while retry budget remains; exhausted jobs fail.
- Payloads and result metadata are bounded JSON. Media bytes are never stored in SQLite.

## Local verification

From the repository root:

```bash
cd backend
pip install -r requirements.txt pytest
PYTHONPATH=. pytest -q tests/test_job_store.py
```

## Deliberate limitations

- The module is not connected to `POST /api/generate`, `GET /api/jobs/{id}`,
  the UI, or the worker process yet.
- No model is enabled and no render is claimed.
- There is no multi-host queue coordination, distributed lock service, worker
  sandbox, quota enforcement, user identity, or private artifact store.
- Do not expose this module directly to the public internet. Integrate it only
  behind authenticated API routes and a trusted worker protocol.

The next integration gate is an authenticated API/worker protocol with
idempotency, cancellation signalling, worker leases, artifact validation and
private result delivery. Generation remains fail-closed until a real render
passes acceptance tests.
