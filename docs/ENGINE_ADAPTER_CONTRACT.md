# RF983 MOTION — engine adapter contract (0.7)

## Purpose
RF983 MOTION now defines a boundary for future model adapters and output validation. This is an integration contract, not an installed model, a renderer, or an enabled generation path.

## Adapter requirements
A reviewed adapter implements `EngineAdapter` in `worker/engine_contract.py`:
- `model_id`: stable model identifier that matches a reviewed model registry entry.
- `is_available()`: checks dependencies, hardware, model weights and license/configuration prerequisites; it must not download weights implicitly.
- `render(request, output_dir)`: writes a candidate output only inside the supplied private output directory and returns a `RenderResult`.

The adapter must not accept arbitrary filesystem paths from a browser request, execute user-provided shell commands, or return a public URL to a local file.

## Render artifact acceptance
`RenderArtifactValidator`:
1. Resolves the output path and rejects files outside the configured output root (including symlink escapes).
2. Requires a regular, non-empty `.mp4` file.
3. Enforces a configurable maximum byte size.
4. Runs `ffprobe` with a fixed argument list and timeout.
5. Requires a video stream with positive duration and dimensions.
6. Returns verified metadata, including dimensions and frame rate.

This is a validation primitive only. No generation endpoint calls it yet; there is no durable queue, authenticated end-user identity, private media delivery or concrete model adapter in this release.

## Tests
Run from repository root:

```sh
python -m pytest backend/tests worker/test_engine_contract.py
```

The tests cover path containment, empty files, file type and size limits. They do not claim to validate a real rendered video.
