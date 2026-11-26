"""RF983 MOTION API: operational diagnostics; generation stays fail-closed."""
import hmac, os, time
from threading import Lock
from typing import Any
from collections import deque
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

APP_VERSION="0.3.0"
ALLOWED_ORIGINS=[x.strip() for x in os.getenv("RF983_ALLOWED_ORIGINS","http://localhost:8000,http://127.0.0.1:8000").split(",") if x.strip()]
WORKER_TOKEN=os.getenv("RF983_WORKER_TOKEN","")
MAX_BODY_BYTES=int(os.getenv("RF983_MAX_BODY_BYTES",str(256*1024)))
_started=time.time()
_lock=Lock()
_events: deque[dict[str,Any]]=deque(maxlen=100)
_worker={"connected":False,"engine_ready":False,"engine":None,"last_seen":None,"capabilities":[]}
app=FastAPI(title="RF983 MOTION API",version=APP_VERSION,description="Private API and worker-readiness foundation.",docs_url="/api/docs",redoc_url=None)
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
    return {"status":"ok","service":"rf983-motion-api","version":APP_VERSION,"inference":"ready" if worker_fresh() and _worker["engine_ready"] else "offline","uptime_seconds":int(time.time()-_started)}

@app.get("/api/system/ready")
def system_ready():
    connected=worker_fresh()
    return {"api":"ready","worker":"connected" if connected else "offline","engine":"ready" if connected and _worker["engine_ready"] else "not_configured","generation_enabled":False,"generation_reason":"A heartbeat is not a verified model adapter or successful render.","checks":{"worker_token_configured":bool(WORKER_TOKEN),"worker_heartbeat_fresh":connected,"model_adapter_verified":False,"persistent_job_queue":False,"private_result_storage":False,"user_authentication":False}}

@app.get("/api/capabilities")
def capabilities():
    fresh=worker_fresh()
    return {"api_version":APP_VERSION,"generation_enabled":False,"reason":"No verified inference adapter, durable queue, user authentication or private result storage is configured.","worker":{"connected":fresh,"engine":_worker["engine"] if fresh else None,"engine_ready":bool(_worker["engine_ready"]) if fresh else False,"capabilities":_worker["capabilities"] if fresh else []},"supported_request_modes":["text","image"],"planned_features":["verified_model_adapters","durable_generation_jobs","reference_image_conditioning","private_result_storage","authenticated_project_sync"]}

@app.post("/api/worker/heartbeat")
def worker_heartbeat(payload:WorkerHeartbeat,x_worker_token:str|None=Header(default=None)):
    require_worker_token(x_worker_token)
    with _lock:
        _worker.update(connected=True,worker_id=payload.worker_id,engine=payload.engine,engine_ready=payload.engine_ready,capabilities=payload.capabilities,last_seen=time.time())
        _events.append({"time":int(time.time()),"kind":"worker_heartbeat","detail":payload.worker_id})
    return {"accepted":True,"worker_id":payload.worker_id,"generation_enabled":False}

@app.post("/api/generate",status_code=503)
def generate(request:GenerateRequest):
    raise HTTPException(503,detail={"code":"INFERENCE_NOT_CONFIGURED","message":"No verified video-generation adapter is enabled. No generation job was created.","api_version":APP_VERSION})

@app.get("/api/jobs/{job_id}")
def get_job(job_id:str):
    raise HTTPException(503,detail={"code":"JOB_SERVICE_NOT_CONFIGURED","message":"Persistent job queue and private render storage are not configured.","job_id":job_id})
