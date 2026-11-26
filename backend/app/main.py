"""RF983 MOTION API: diagnostics and fail-closed inference foundation."""
import hmac, importlib.util, os, platform, shutil, subprocess, time
from threading import Lock
from typing import Any
from collections import deque
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

APP_VERSION="0.4.0"
ALLOWED_ORIGINS=[x.strip() for x in os.getenv("RF983_ALLOWED_ORIGINS","http://localhost:8000,http://127.0.0.1:8000").split(",") if x.strip()]
WORKER_TOKEN=os.getenv("RF983_WORKER_TOKEN","")
MAX_BODY_BYTES=int(os.getenv("RF983_MAX_BODY_BYTES",str(256*1024)))
_started=time.time()
_lock=Lock()
_events: deque[dict[str,Any]]=deque(maxlen=100)
_worker={"connected":False,"engine_ready":False,"engine":None,"worker_id":None,"last_seen":None,"capabilities":[]}

MODEL_CATALOG=[
 {"id":"wan-ti2v-5b","name":"Wan 2.2 TI2V 5B","tasks":["text-to-video","image-to-video"],"target":"720p","fps":24,"audio":False,"status":"candidate","adapter_installed":False,"weights_present":False,"license_review_required":True,"source":"https://github.com/Wan-Video/Wan2.2"},
 {"id":"wan-i2v-14b","name":"Wan 2.2 I2V 14B","tasks":["image-to-video"],"target":"hardware-dependent","fps":24,"audio":False,"status":"candidate","adapter_installed":False,"weights_present":False,"license_review_required":True,"source":"https://github.com/Wan-Video/Wan2.2"},
 {"id":"ltx-2.5","name":"LTX-2.5","tasks":["text-to-video","image-to-video","audio-video"],"target":"pipeline-dependent","fps":None,"audio":True,"status":"candidate","adapter_installed":False,"weights_present":False,"license_review_required":True,"source":"https://github.com/Lightricks/LTX-2"}
]
app=FastAPI(title="RF983 MOTION API",version=APP_VERSION,description="Private API and inference-readiness foundation.",docs_url="/api/docs",redoc_url=None)
app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS,allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Content-Type","Authorization","X-Worker-Token"])

class GenerateRequest(BaseModel):
    prompt:str=Field(min_length=5,max_length=4000)
    negative_prompt:str=Field(default="",max_length=1200)
    mode:str=Field(default="text",pattern="^(text|image)$")
    model_route:str=Field(default="auto",max_length=40)
    aspect_ratio:str=Field(default="16:9",pattern="^(16:9|9:16|1:1|4:3|21:9)$")
    resolution:str=Field(default="720p",pattern="^(720p|1080p|4k)$")
    duration_seconds:int=Field(default=5,ge=1,le=20)
    fps:int=Field(default=24,ge=12,le=60)
    quality_profile:str=Field(default="cinematic",pattern="^(cinematic|balanced|draft)$")
    seed:int|None=Field(default=None,ge=0,le=2147483647)
    audio:bool=False
    refine:bool=True
    shots:list[dict]=Field(default_factory=list,max_length=12)
    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls,v):
        v=v.strip()
        if not v: raise ValueError("Prompt cannot be blank.")
        return v

class WorkerHeartbeat(BaseModel):
    worker_id:str=Field(min_length=3,max_length=80,pattern="^[a-zA-Z0-9._-]+$")
    engine:str=Field(min_length=2,max_length=80)
    engine_ready:bool=False
    capabilities:list[str]=Field(default_factory=list,max_length=30)

def worker_fresh():
    return bool(_worker["last_seen"] and time.time()-_worker["last_seen"]<45)

def require_worker_token(token):
    if not WORKER_TOKEN:
        raise HTTPException(503,detail={"code":"WORKER_AUTH_NOT_CONFIGURED","message":"Set RF983_WORKER_TOKEN before registering a worker."})
    if not token or not hmac.compare_digest(token,WORKER_TOKEN):
        raise HTTPException(401,detail={"code":"WORKER_AUTH_FAILED","message":"Worker authentication failed."})

@app.middleware("http")
async def safety_headers(request:Request,call_next):
    if request.method in {"POST","PUT","PATCH"} and request.headers.get("content-length"):
        try:
            if int(request.headers["content-length"])>MAX_BODY_BYTES:
                return JSONResponse(413,content={"detail":{"code":"REQUEST_TOO_LARGE","message":"Request body exceeds configured limit."}})
        except ValueError:
            return JSONResponse(400,content={"detail":"Invalid Content-Length."})
    response=await call_next(request)
    response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Cache-Control":"no-store"})
    return response

@app.get("/api/health")
def health():
    return {"status":"ok","service":"rf983-motion-api","version":APP_VERSION,"inference":"offline","uptime_seconds":int(time.time()-_started)}

@app.get("/api/system/ready")
def system_ready():
    connected=worker_fresh()
    return {"api":"ready","worker":"connected" if connected else "offline","engine":"reported_ready" if connected and _worker["engine_ready"] else "not_configured","generation_enabled":False,"generation_reason":"No verified model adapter, durable job queue, user authentication or private render storage is configured.","checks":{"worker_token_configured":bool(WORKER_TOKEN),"worker_heartbeat_fresh":connected,"model_adapter_verified":False,"durable_job_queue":False,"private_result_storage":False,"user_authentication":False,"successful_render_verified":False}}

@app.get("/api/capabilities")
def capabilities():
    fresh=worker_fresh()
    return {"api_version":APP_VERSION,"generation_enabled":False,"reason":"No verified inference adapter, durable queue, user authentication or private result storage is configured.","worker":{"connected":fresh,"worker_id":_worker["worker_id"] if fresh else None,"engine":_worker["engine"] if fresh else None,"engine_ready_reported":bool(_worker["engine_ready"]) if fresh else False,"capabilities":_worker["capabilities"] if fresh else []},"supported_request_modes":["text","image"],"planned_features":["verified_model_adapters","durable_generation_jobs","reference_image_conditioning","private_result_storage","authenticated_project_sync"]}

@app.get("/api/models")
def models():
    """Candidate catalog; entries are never presented as installed or runnable."""
    return {"models":MODEL_CATALOG,"verified_model_count":0,"generation_enabled":False}

@app.get("/api/system/worker-preflight")
def worker_preflight():
    tools={name:shutil.which(name) is not None for name in ("git","ffmpeg","nvidia-smi")}
    packages={name:importlib.util.find_spec(name) is not None for name in ("torch","diffusers","transformers","safetensors")}
    gpu={"detected":False,"detail":"No GPU has been verified."}
    if tools["nvidia-smi"]:
        try:
            result=subprocess.run(["nvidia-smi","--query-gpu=name,memory.total,driver_version","--format=csv,noheader"],check=True,capture_output=True,text=True,timeout=4)
            gpu={"detected":bool(result.stdout.strip()),"detail":result.stdout.strip()[:1000]}
        except (OSError,subprocess.SubprocessError):
            gpu={"detected":False,"detail":"nvidia-smi exists but GPU query failed."}
    return {"python":platform.python_version(),"platform":platform.platform(),"tools":tools,"python_packages":packages,"gpu":gpu,"generation_ready":False,"reason":"Preflight only detects environment components; a real adapter and successful render are still required."}

@app.post("/api/worker/heartbeat")
def worker_heartbeat(payload:WorkerHeartbeat,x_worker_token:str|None=Header(default=None)):
    require_worker_token(x_worker_token)
    with _lock:
        _worker.update(connected=True,worker_id=payload.worker_id,engine=payload.engine,engine_ready=payload.engine_ready,capabilities=payload.capabilities,last_seen=time.time())
        _events.append({"time":int(time.time()),"kind":"worker_heartbeat","detail":payload.worker_id})
    return {"accepted":True,"worker_id":payload.worker_id,"generation_enabled":False}

@app.get("/api/worker/status")
def worker_status():
    fresh=worker_fresh()
    return {"connected":fresh,"worker_id":_worker["worker_id"] if fresh else None,"engine":_worker["engine"] if fresh else None,"engine_ready_reported":bool(_worker["engine_ready"]) if fresh else False,"last_seen_seconds_ago":round(time.time()-_worker["last_seen"],1) if fresh else None,"generation_enabled":False}

@app.post("/api/generate",status_code=503)
def generate(request:GenerateRequest):
    raise HTTPException(503,detail={"code":"INFERENCE_NOT_CONFIGURED","message":"No verified video-generation adapter is enabled. No generation job was created.","api_version":APP_VERSION})

@app.get("/api/jobs/{job_id}")
def get_job(job_id:str):
    raise HTTPException(503,detail={"code":"JOB_SERVICE_NOT_CONFIGURED","message":"Persistent job queue and private render storage are not configured.","job_id":job_id})
