import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

APP_VERSION = "0.2.0"
ALLOWED_ORIGINS = [item.strip() for item in os.getenv("RF983_ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if item.strip()]

app = FastAPI(
    title="RF983 MOTION API",
    version=APP_VERSION,
    description="Private API foundation for the RF983 MOTION cinematic video studio.",
    docs_url="/api/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    negative_prompt: str = Field(default="", max_length=1200)
    mode: str = Field(default="text", pattern="^(text|image)$")
    model_route: str = Field(default="auto", max_length=40)
    aspect_ratio: str = Field(default="16:9", pattern="^(16:9|9:16|1:1|4:3|21:9)$")
    resolution: str = Field(default="720p", pattern="^(720p|1080p|4k)$")
    duration_seconds: int = Field(default=5, ge=1, le=20)
    fps: int = Field(default=24, ge=12, le=60)
    quality_profile: str = Field(default="cinematic", pattern="^(cinematic|balanced|draft)$")
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    audio: bool = False
    refine: bool = True
    shots: list[dict] = Field(default_factory=list, max_length=12)

    @field_validator("prompt")
    @classmethod
    def prompt_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Prompt cannot be blank.")
        return value

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "rf983-motion-api",
        "version": APP_VERSION,
        "inference": "offline",
    }

@app.get("/api/capabilities")
def capabilities():
    return {
        "api_version": APP_VERSION,
        "generation_enabled": False,
        "reason": "No authenticated GPU worker or model runtime is configured.",
        "supported_request_modes": ["text", "image"],
        "planned_features": [
            "queued_generation_jobs",
            "reference_image_conditioning",
            "shot_level_prompting",
            "generation_history",
            "signed_result_delivery",
        ],
        "security_requirements": [
            "private_authentication",
            "per_user_quotas",
            "upload_validation",
            "signed_storage_urls",
            "worker_isolation",
        ],
    }

@app.post("/api/generate", status_code=503)
def generate(request: GenerateRequest):
    # Intentionally fail closed. This endpoint must not pretend to create a job.
    raise HTTPException(
        status_code=503,
        detail={
            "code": "INFERENCE_NOT_CONFIGURED",
            "message": "RF983 MOTION has no connected GPU worker. No generation job was created.",
            "api_version": APP_VERSION,
        },
    )

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    raise HTTPException(
        status_code=503,
        detail={
            "code": "JOB_SERVICE_NOT_CONFIGURED",
            "message": "The persistent job queue and render storage are not configured.",
            "job_id": job_id,
        },
    )
