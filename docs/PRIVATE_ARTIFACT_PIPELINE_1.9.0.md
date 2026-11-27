# RF983 MOTION 1.9.0 — Private Artifact Pipeline

## What this release adds
- A worker-authenticated streaming upload endpoint for MP4 video artifacts.
- Server-side ffprobe validation of the MP4 container, video stream, codec, dimensions and duration.
- SHA-256 integrity metadata, file size, worker ID, optional queue job ID and creation timestamp.
- A private artifact metadata index and safe generated storage filenames.
- Operations-token-protected artifact inventory, metadata lookup and download endpoints.
- A Production Control Room inventory with private download actions and an explicit storage durability warning.

## API
- `POST /api/worker/artifacts`: raw `video/mp4` request body; requires `X-Worker-Token` and `X-Worker-ID`; optional `X-Job-ID`.
- `GET /api/operations/artifacts?limit=25`: inventory; requires `X-Operations-Token`.
- `GET /api/operations/artifacts/{artifact_id}`: metadata only; requires operations token.
- `GET /api/operations/artifacts/{artifact_id}/download`: private MP4 download; requires operations token.

Uploads are streamed to disk and bounded by `RF983_MAX_ARTIFACT_BYTES` (default 2 GiB). The backend rejects non-MP4 content, empty uploads, oversized bodies, invalid identifiers and files that fail ffprobe validation. No client-facing or public media URL is created.

## Configuration
- `RF983_ARTIFACT_DIR`: private file directory (default `/tmp/rf983-artifacts`).
- `RF983_ARTIFACT_DB`: metadata SQLite database (defaults to `RF983_STATE_DB`).
- `RF983_MAX_ARTIFACT_BYTES`: upload limit in bytes (default 2 GiB).
- The Docker image installs FFmpeg/ffprobe for validation.

For durable production retention, set `RF983_ARTIFACT_DIR` to a mounted persistent volume and configure `RF983_ARTIFACT_DB` to a durable SQLite volume or a separately managed metadata database. Confirm mount and backup behaviour yourself; the API intentionally reports durability as unverified. The current Render free filesystem path is under `/tmp` and is ephemeral. Files stored there can disappear on restart or redeploy.

## Safety boundary
- Uploads require the private worker token; inventory, metadata and downloads require the private operations token.
- Tokens are read from request headers and are never returned.
- Files are stored with random server-generated names; user-provided paths are never used.
- Downloads use private authenticated routes and `Cache-Control: no-store`; no public links are generated.
- The API validates files but does not run inference, create jobs, or mark jobs successful.
- No cloud object-storage provider has been connected. No external service is called.
- `POST /api/generate` remains disabled. A verified model, real worker integration, creator authentication, durable storage and an end-to-end successful render are still required before generation can be enabled.

## Verification
Automated tests cover worker-token upload protection, operations-token inventory/download protection, MP4 validation failure, unknown job rejection, metadata persistence and control-room reporting. Test fixtures replace ffprobe output; a successful CI test does not represent a real cinematic generation.
