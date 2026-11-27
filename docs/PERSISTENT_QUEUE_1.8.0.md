# RF983 MOTION 1.8.0 — Persistent Queue Foundation

## What changed
- The private generation queue can use SQLite for local development or PostgreSQL for a separately managed database.
- Configure the queue independently with RF983_QUEUE_DB; it accepts a PostgreSQL connection URL (postgresql://... or postgres://...) or a SQLite file path.
- RF983_STATE_DB remains the SQLite store for worker heartbeat history.
- The authenticated Production Control Room reports queue storage type, ephemeral status and the provider-dependent durability caveat.
- API health reports the configured queue backend. Generation and provider calls remain disabled.

## Enabling external PostgreSQL
1. Provision a PostgreSQL database with a provider of your choice. Check its current price, backup policy, storage limits and network access before creating it.
2. In the backend host's private environment settings, set RF983_QUEUE_DB to the provider's PostgreSQL connection URL. Do not commit the URL to Git or paste it into chat.
3. Redeploy the backend. The queue schema and indexes are created automatically on first connection.
4. Open Model Lab → Production Control Room and refresh. It should report POSTGRESQL QUEUE · EXTERNAL.

This repository does not provision a database, enable paid services, or transfer existing SQLite queue records. Existing SQLite data remains where it is. Migrate records only with a deliberate, backed-up migration plan.

## Important storage distinction
The PostgreSQL queue and worker-history SQLite are separate. On the current Render free configuration, worker-history records still use the ephemeral /tmp filesystem and can be lost on restart. A PostgreSQL queue is only as durable as the external provider's actual plan, backups and retention settings; the API cannot independently verify those guarantees.

## Safety and limitations
- No database URL, username, password or secret is returned by any API endpoint.
- PostgreSQL support is opt-in. The current Render configuration continues using its existing SQLite queue until RF983_QUEUE_DB is configured privately.
- No provider inference calls, GPU worker integration, model verification, user authentication, media storage or actual video generation is added by this release.
- POST /api/generate remains fail-closed with INFERENCE_NOT_CONFIGURED.
- Queue operations remain private and require X-Operations-Token.

## Tests
The automated suite covers SQLite queue lifecycle, PostgreSQL URL classification, storage reporting, authenticated queue access and the fail-closed generation boundary. A live PostgreSQL service test must be run after a real database URL is configured; URL recognition alone is not a live database verification.
