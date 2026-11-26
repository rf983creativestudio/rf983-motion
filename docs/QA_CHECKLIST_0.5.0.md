# RF983 MOTION 0.6.0 — Production desk acceptance checklist

Run these checks in a real browser after serving the frontend.

## Production audit
- [ ] Open Storyboard and confirm shot count, planned runtime, estimated frames and brief score appear.
- [ ] Change target FPS and confirm estimated frames update.
- [ ] Change a shot duration and confirm runtime and frame estimate update.
- [ ] Confirm warnings appear for a generic project title, short prompt, blank shot actions, duplicate shot names and identical camera movements.
- [ ] Confirm missing negative prompt and reference image are marked optional rather than fatal.
- [ ] Confirm audit output is refreshed after editing and with the Run checks button.

## Director brief export
- [ ] Export the director brief Markdown file.
- [ ] Confirm it includes creative brief, settings, director notes, every shot, planned runtime, frame estimate, checks and handoff limitations.
- [ ] Confirm reference image bytes are not embedded and the brief tells the recipient to share the image separately.

## Shot CSV export
- [ ] Export the shot CSV.
- [ ] Open it in a spreadsheet and verify columns, Unicode text, commas and quotation marks are preserved.
- [ ] Confirm each shot appears once and in storyboard order.

## Structured production JSON
- [ ] Export production JSON.
- [ ] Confirm it parses as JSON and contains project data, generated timestamp, runtime, target FPS, estimated frames and audit checks.
- [ ] Confirm no image data or remote upload is involved.

## Safety and claims
- [ ] Confirm all exports are generated locally in the browser.
- [ ] Confirm estimates are labeled as planning estimates and not actual model output.
- [ ] Confirm generation remains disabled until a verified inference adapter and required production infrastructure exist.

## Verification status
Source files were committed and retrieved from GitHub. This checklist is a manual test plan and has not been executed in a real browser. Do not treat it as a passed test report.
