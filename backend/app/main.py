from enum import Enum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="RF983 MOTION API", version="0.1.0")

class Mode(str, Enum):
    text = "text"
    image = "image"

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=1800)
    mode: Mode = Mode.text
    aspect_ratio: str = "16:9"
    duration_seconds: int = Field(default=5, ge=1, le=10)
    quality_profile: str = "max"
    seed: int | None = None

@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "not_connected", "version": "0.1.0"}

@app.post("/api/generate")
def generate(request: GenerateRequest):
    # Fail closed until a secured GPU worker, queue and storage are configured.
    raise HTTPException(
        status_code=503,
        detail="Video inference is not configured. Connect an authorized GPU worker before enabling generation."
    )
