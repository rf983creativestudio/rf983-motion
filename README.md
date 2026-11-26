# RF983 MOTION — private starter

A self-hostable foundation for a private AI cinematic video studio.

## Important
This repository contains a prototype UI and API contract only. It does not include model weights or GPU inference. GitHub Pages can host the frontend, but cannot run video generation. Do not promise free unlimited high-quality generation: GPU compute, storage and bandwidth have real limits and costs.

## Structure
- `frontend/`: static responsive studio interface
- `backend/`: FastAPI health endpoint and safely disabled generation endpoint
- `docs/`: architecture and deployment notes

## Run frontend
Open `frontend/index.html` locally, or publish the `frontend/` directory using GitHub Pages.

## Run API
```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Security
Never commit API keys, model weights, user uploads or generated videos. Keep secrets server-side. Add authentication, quotas, signed storage URLs and abuse protection before enabling generation.

## Model research
Evaluate the official Wan and LTX repositories and the exact checkpoint licenses/hardware requirements before deployment. Code and weights may have different licenses.
