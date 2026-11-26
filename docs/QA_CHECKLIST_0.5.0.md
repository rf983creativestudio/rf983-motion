# RF983 MOTION 0.5.0 — manual acceptance checklist

This release adds browser-side workflow features. Run this checklist in a real browser
after serving the frontend (preferably with the included local Docker Compose stack).

## Studio
- [ ] Enter a prompt and confirm the prompt count updates.
- [ ] Confirm prompt direction cues update as the prompt changes.
- [ ] Change every film setting and confirm the local draft survives a page reload.
- [ ] Confirm the autosave indicator changes from unsaved to saved.
- [ ] Select a reference image and confirm it is previewed locally.
- [ ] Confirm reference image bytes are not embedded in project JSON exports.

## Storyboard
- [ ] Add shots up to the 12-shot limit; confirm the limit is enforced.
- [ ] Duplicate a shot and verify its values are copied with a new identity.
- [ ] Move shots up and down and confirm the sequence timeline changes order.
- [ ] Change shot durations and confirm total runtime and timeline segment proportions update.
- [ ] Remove a shot and confirm at least one shot remains.

## Project portability
- [ ] Export a project JSON file.
- [ ] Import the exported file and confirm its prompt, settings and shots are restored.
- [ ] Confirm the imported reference image is not restored and must be selected again.
- [ ] Try a non-JSON file, oversized file, invalid project, and a project with 13 shots; each must fail safely.
- [ ] Confirm imports are limited to 1 MB and shot content is bounded.

## API and inference boundary
- [ ] Confirm Model Lab diagnostics work against a running API with correct CORS.
- [ ] Confirm the API remains generation-disabled without a verified model adapter and a successful render.
- [ ] Confirm no prompt or image is uploaded when the Generate button is clicked while inference is offline.

## Verification status

The GitHub repository update confirms source files were committed and retrieved. This
checklist has not yet been executed in a real browser or CI runner; do not treat it as
a passed test report.
