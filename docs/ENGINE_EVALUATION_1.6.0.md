# RF983 MOTION 1.6.0 — Engine Evaluation & Selection

## Purpose
Build a conservative decision layer above the provider-neutral engine registry. The endpoint is informational only and makes no provider requests.

## Current assessment
- Do not activate a cloud engine until an explicit spending limit and data-transfer policy are approved.
- Replicate and fal.ai are possible managed-inference routes to compare later, model by model.
- RunPod is a cloud-GPU route that requires a deployed and maintained worker.
- Custom HTTPS requires an existing trusted endpoint implementing the RF983 adapter contract.

## Important limitations
- No live provider pricing is fetched.
- No quality benchmark or model comparison is claimed.
- No provider credentials are accepted.
- No prompts or assets are transmitted.
- Generation remains disabled.

## API
- `GET /api/engine-evaluation` returns the conservative profile, recommendation and per-engine requirements/trade-offs.
- `GET /api/engines` remains the provider registry.
