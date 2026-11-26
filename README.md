# RF983 MOTION — private cinematic studio

RF983 MOTION is a private, self-hostable foundation for a cinematic AI video-generation workspace.

## Build 0.2.0 — Studio expansion
- Multi-view workspace: Studio, Storyboard, My Projects and Model Lab.
- Structured director's notes and local prompt assembly.
- Editable shot list with framing, camera movement, action and duration.
- Film output configuration: aspect ratio, resolution, duration, frame rate, quality, seed, audio and refinement options.
- Reference-image preview with file type and 10 MB validation. The image stays in the browser and is not uploaded.
- Browser-local draft saving, project library and portable JSON export.
- FastAPI health and capability endpoints.
- Generation and job endpoints explicitly fail closed until a real GPU worker, private authentication, queue and storage are connected.

## Run the frontend
Open \`frontend/index.html\` locally. For static hosting, publish the contents of the \`frontend/\` folder. Browser local storage is local to that browser and device.

## Run the API locally
\`\`\`bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
\`\`\`
API docs: \`/api/docs\`; health: \`/api/health\`; capabilities: \`/api/capabilities\`.

Set \`RF983_ALLOWED_ORIGINS\` to a comma-separated list of exact trusted origins when deploying the API. The default is localhost only.

## Current limitations
This build is a functioning creative-planning frontend, not a functioning AI video generator. The prompt builder, shot planner, local drafts, project library and JSON export work in the browser. The Generate action is intentionally blocked. There is no GPU worker, persistent job queue, cloud render storage, user login, billing, or cloud sync.

## Model research
- [Wan 2.2](https://github.com/Wan-Video/Wan2.2) — includes a 5B text/image-to-video path targeting 720p at 24 fps; actual hardware needs must be tested.
- [LTX-2.5](https://github.com/Lightricks/LTX-2) — advanced audio/video pipelines; current model files are substantial and the exact model license is separate from the code license.

Review the license for the exact checkpoint and any dependent text encoder before use. Do not assume an open-source code license automatically covers model weights or commercial use.

## Security rules
- Keep this repository private.
- Never commit API keys, access tokens, model weights, user images, generated videos or private logs.
- Keep inference credentials on the server only.
- Before enabling inference, add private authentication, per-user quotas, upload validation, worker isolation, signed storage URLs, retention controls and audit logging.
- Do not promise unlimited free generation. GPU compute, model storage and delivery bandwidth have real costs.

## Project data
Project JSON exports include prompts, settings and shot plans, but do not embed reference image files. Re-select the reference image after importing or restoring a project.
