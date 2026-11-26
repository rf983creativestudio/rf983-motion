# RF983 MOTION — inference engine integration

## Current state

The repository contains an adapter interface and a candidate catalog only. There is no
installed model adapter, model checkpoint, GPU runtime, scheduler or render store.
The API must continue to report generation as disabled until those pieces are tested
together with an actual successful render.

## Adapter contract

Implement a class derived from `app.engine_contract.VideoEngine` and provide:

1. `capabilities()`: exact supported tasks, aspect ratios, resolutions and frame rates.
2. `readiness()`: verify imports, checkpoint files, license acceptance, device type,
   available VRAM and required system libraries. Return false on any uncertainty.
3. `generate()`: run one validated request in an isolated output directory and return
   a real video file plus metadata. Never return a placeholder file as success.

Keep model-specific imports inside the adapter implementation. Do not import PyTorch,
Diffusers or model packages in the API process. The API should remain lightweight.

## Candidate order

1. Wan 2.2 TI2V 5B: first candidate for a measured text/image-to-video proof of concept.
2. Wan 2.2 I2V 14B: evaluate only after actual GPU memory measurements.
3. LTX-2.5: evaluate audio/video workflows and review its checkpoint license independently.

A model appearing in the catalog does not mean its weights are downloaded, its license
has been approved, or it can run on the current machine.

## Proof-of-generation acceptance gate

Before enabling any user-facing generation route, record all of the following:

- exact repository commit and checkpoint identifier;
- checkpoint license and permitted use;
- Python, CUDA, driver and framework versions;
- GPU model, VRAM, peak memory and inference duration;
- input dimensions, output dimensions, duration and frame rate;
- successful MP4 decode with FFmpeg;
- output file size and checksum;
- failure handling for out-of-memory, timeout and corrupt output;
- repeatable seed behaviour where the model supports it.

Only a real end-to-end render should change an adapter from candidate to verified.
