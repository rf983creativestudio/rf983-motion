# RF983 MOTION — architecture plan

## Phase 1: foundation
- Private GitHub repository and static responsive studio frontend.
- FastAPI health endpoint and typed generation request.
- Generation endpoint deliberately disabled until inference is safely configured.
- No model weights, secrets, uploads or rendered media committed to Git.

## Phase 2: secure inference
- Select a GPU worker/provider only after checking actual free-tier limits and hardware.
- Add a queue and job states: queued → running → succeeded/failed.
- Add object storage, signed upload/download URLs, authentication, quotas and retention controls.
- Keep model adapters isolated so compatible model families can be evaluated.

## Phase 3: cinematic workflow
- Prompt planning and shot breakdown.
- Reference-image conditioning and seed capture.
- Model-native generation followed by optional interpolation, upscaling and audio.
- Preview/final render, generation history and reproducibility metadata.

## Zero-budget reality
A static site and small API prototype may fit free hosting limits. Sustained high-quality video inference is not realistically free: GPU compute, storage and bandwidth are scarce. Do not promise free unlimited generation. Start with local inference only if suitable hardware is already available, or wait until a genuinely free GPU allocation is confirmed.

## Model evaluation
- Wan: https://github.com/Wan-Video/Wan2.2
- LTX: https://github.com/Lightricks/LTX-2
Review the exact checkpoint license, hardware needs and permitted use before deployment. Model weights and source code can have different licenses.
