# RF983 MOTION — architecture and release plan

## Build 0.2.0: creative workflow foundation

### Browser application
- Static frontend with four views: Studio, Storyboard, My Projects and Model Lab.
- Structured prompt composition and a local prompt-writing guide.
- Shot list editor: up to 12 shots, framing, camera movement, action notes and planned duration.
- Film controls: model route, aspect ratio, resolution, duration, frame rate, quality profile, seed, audio and refinement flags.
- Reference image preview with type and size checks; no image upload endpoint exists.
- Draft persistence in browser local storage, saved-project library and JSON export.
- No analytics, external script dependencies or third-party runtime calls.

### API foundation
- FastAPI health and capability endpoints.
- Typed and bounded generation request schema.
- Explicit 503 response for generation and job lookup until infrastructure exists.
- CORS restricted to configured origins; default local origins only.
- API is not a substitute for authentication. Add private auth before exposing it publicly.

## Target production architecture

\`\`\`text
Private browser UI
      |
      | authenticated HTTPS
      v
API gateway / FastAPI
      |
      +---- Project metadata database
      |
      +---- Generation queue ---- Worker scheduler
      |                               |
      |                               v
      |                         Isolated GPU worker
      |                               |
      |                         Model adapter layer
      |                          /             \\
      |                      Wan 2.2         LTX-2.5
      |                               |
      +---- Signed upload/download URLs
                                      |
                               Private object storage
\`\`\`

## Job lifecycle (future implementation)
1. Validate user identity, quota, prompt size and reference file.
2. Create a durable job record with an idempotency key.
3. Enqueue the job and return a job identifier.
4. Worker claims the job and checks model availability and GPU capacity.
5. Worker generates output in isolated temporary storage.
6. Validate output metadata and scan the result.
7. Store the render privately and issue a short-lived signed URL.
8. Persist completion/failure metadata and enforce retention policy.

## Model adapter contract (future)
Each adapter should expose:
- supported tasks and conditioning inputs;
- supported aspect ratios, frame counts, fps and resolution;
- required weights and exact model/checkpoint license;
- VRAM estimate and runtime constraints;
- deterministic seed support;
- audio and refinement support;
- health/readiness state and structured error codes.

Do not route a job to a model solely because it appears in a dropdown. The worker must confirm that the exact checkpoint, dependencies, license and hardware are ready.

## Candidate research
- Wan 2.2: https://github.com/Wan-Video/Wan2.2
  - The 5B TI2V path supports text/image-to-video and a 720p, 24 fps target.
  - Do not generalize this hardware profile to the larger 14B variants.
- LTX-2.5: https://github.com/Lightricks/LTX-2
  - Offers multiple pipelines, including a production-quality DFR path.
  - The current quick-start model components total roughly 66 GiB; the standard training configuration recommends 80 GB+ VRAM. Verify inference-specific hardware guidance for the exact pipeline.

## Zero-budget constraints
GitHub can host source and a static UI. It is not a GPU inference service. Free allocations are variable and can be interrupted, rate-limited or unavailable. Do not build the product around an assumed permanent free GPU tier.

## Security and privacy gate before public inference
- Repository remains private.
- Authentication and authorization are mandatory.
- Secrets stay in environment variables or a secret manager.
- Validate MIME type, file signature, size, dimensions and ownership for uploads.
- Use private object storage and short-lived signed URLs.
- Apply per-user rate limits, job quotas and storage limits.
- Isolate GPU workers; never execute user-supplied code.
- Keep an audit trail and configurable deletion/retention.
- Do not store prompts or reference images unless the user explicitly saves a project.

## Next milestones
1. Run automated tests for the API contract and frontend smoke checks.
2. Choose one model route after hardware and licensing review.
3. Prototype a worker on genuinely available hardware or a confirmed compute allocation.
4. Add authentication, queue, persistent metadata and private result storage.
5. Enable generation only after an end-to-end test produces and retrieves a real render.
