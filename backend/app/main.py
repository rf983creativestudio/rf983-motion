"""RF983 MOTION API: diagnostics and fail-closed inference foundation."""
import hmac, importlib.util, os, platform, shutil, subprocess, time, sqlite3, json, hashlib, tempfile, math
from app.job_store import JobStore, JobStoreError, JobNotFound, InvalidJobTransition
from app.artifact_store import ArtifactStore, ArtifactNotFound
from app.engine_registry import list_engines, get_engine
from app.engine_evaluation import evaluate_engines
from contextlib import contextmanager
from threading import Lock
from typing import Any
from collections import deque
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, field_validator

APP_VERSION="2.4.0"
ALLOWED_ORIGINS=[x.strip() for x in os.getenv("RF983_ALLOWED_ORIGINS","http://localhost:8000,http://127.0.0.1:8000").split(",") if x.strip()]
WORKER_TOKEN=os.getenv("RF983_WORKER_TOKEN","")
OPERATIONS_TOKEN=os.getenv("RF983_OPERATIONS_TOKEN","")
MAX_BODY_BYTES=int(os.getenv("RF983_MAX_BODY_BYTES",str(256*1024)))
_started=time.time()
_lock=Lock()
_events: deque[dict[str,Any]]=deque(maxlen=100)
_worker={"connected":False,"engine_ready":False,"engine":None,"worker_id":None,"last_seen":None,"capabilities":[],"diagnostics":{}}

MODEL_CATALOG=[
 {"id":"wan-ti2v-5b","name":"Wan 2.2 TI2V 5B","tasks":["text-to-video","image-to-video"],"target":"720p","fps":24,"audio":False,"status":"candidate","adapter_installed":False,"weights_present":False,"license_review_required":True,"source":"https://github.com/Wan-Video/Wan2.2"},
 {"id":"wan-i2v-14b","name":"Wan 2.2 I2V 14B","tasks":["image-to-video"],"target":"hardware-dependent","fps":24,"audio":False,"status":"candidate","adapter_installed":False,"weights_present":False,"license_review_required":True,"source":"https://github.com/Wan-Video/Wan2.2"},
 {"id":"ltx-2.5","name":"LTX-2.5","tasks":["text-to-video","image-to-video","audio-video"],"target":"pipeline-dependent","fps":None,"audio":True,"status":"candidate","adapter_installed":False,"weights_present":False,"license_review_required":True,"source":"https://github.com/Lightricks/LTX-2"}
]

STATE_DB=os.getenv("RF983_STATE_DB","./data/rf983-motion.sqlite3")
QUEUE_DB=os.getenv("RF983_QUEUE_DB")
ARTIFACT_DB=os.getenv("RF983_ARTIFACT_DB",STATE_DB)
ARTIFACT_DIR=os.getenv("RF983_ARTIFACT_DIR","/tmp/rf983-artifacts")
MAX_ARTIFACT_BYTES=int(os.getenv("RF983_MAX_ARTIFACT_BYTES",str(2*1024*1024*1024)))
def _state_connection():
    path=os.path.abspath(STATE_DB)
    os.makedirs(os.path.dirname(path),exist_ok=True)
    db=sqlite3.connect(path,timeout=8)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=8000")
    db.execute("""CREATE TABLE IF NOT EXISTS worker_history (id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id TEXT NOT NULL, engine TEXT NOT NULL, observed_at REAL NOT NULL, diagnostics_json TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_worker_history_time ON worker_history(observed_at DESC)")
    return db
@contextmanager
def _state_db():
    db=_state_connection()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _record_worker_heartbeat(worker_id,engine,diagnostics):
    payload=json.dumps(diagnostics,ensure_ascii=False,separators=(",",":"))
    if len(payload.encode("utf-8"))>16000:
        raise HTTPException(413,detail={"code":"DIAGNOSTICS_TOO_LARGE","message":"Worker diagnostics exceed the 16 KB history limit."})
    with _state_db() as db:
        db.execute("INSERT INTO worker_history(worker_id,engine,observed_at,diagnostics_json) VALUES(?,?,?,?)",(worker_id,engine,time.time(),payload))
        db.execute("DELETE FROM worker_history WHERE id NOT IN (SELECT id FROM worker_history ORDER BY observed_at DESC LIMIT 250)")
def _worker_history(limit):
    with _state_db() as db:
        rows=db.execute("SELECT worker_id,engine,observed_at,diagnostics_json FROM worker_history ORDER BY observed_at DESC LIMIT ?",(limit,)).fetchall()
    result=[]
    for row in rows:
        try: diag=json.loads(row["diagnostics_json"])
        except (TypeError,ValueError): diag={}
        result.append({"worker_id":row["worker_id"],"engine":row["engine"],"observed_at":int(row["observed_at"]),"diagnostics":diag})
    return result
app=FastAPI(title="RF983 MOTION API",version=APP_VERSION,description="Private API and inference-readiness foundation.",docs_url="/api/docs",redoc_url=None)
app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS,allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Content-Type","Authorization","X-Worker-Token","X-Operations-Token","X-Worker-ID","X-Job-ID"])

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
    diagnostics:dict[str,Any]=Field(default_factory=dict)

class WorkerFailure(BaseModel):
    error_code:str=Field(min_length=1,max_length=80,pattern="^[A-Z0-9_.-]+$")
    message:str=Field(min_length=1,max_length=500)
    retry:bool=True

class WorkerCompletion(BaseModel):
    artifact_id:str=Field(min_length=32,max_length=32,pattern="^[a-f0-9]{32}$")

def worker_fresh():
    return bool(_worker["last_seen"] and time.time()-_worker["last_seen"]<45)

def require_worker_token(token):
    if not WORKER_TOKEN:
        raise HTTPException(503,detail={"code":"WORKER_AUTH_NOT_CONFIGURED","message":"Set RF983_WORKER_TOKEN before registering a worker."})
    if not token or not hmac.compare_digest(token,WORKER_TOKEN):
        raise HTTPException(401,detail={"code":"WORKER_AUTH_FAILED","message":"Worker authentication failed."})

def require_operations_token(token):
    if not OPERATIONS_TOKEN:
        raise HTTPException(503,detail={"code":"OPERATIONS_AUTH_NOT_CONFIGURED","message":"Set RF983_OPERATIONS_TOKEN to protect private machine diagnostics."})
    if not token or not hmac.compare_digest(token,OPERATIONS_TOKEN):
        raise HTTPException(401,detail={"code":"OPERATIONS_AUTH_FAILED","message":"Operations access token is missing or invalid."})

@app.middleware("http")
async def safety_headers(request:Request,call_next):
    if request.url.path != "/api/worker/artifacts" and request.method in {"POST","PUT","PATCH"} and request.headers.get("content-length"):
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
    return {"status":"ok","service":"rf983-motion-api","version":APP_VERSION,"inference":"offline","worker_agent_protocol":"0.7","state_store":"sqlite","queue_store":"postgresql" if (QUEUE_DB or STATE_DB).startswith(("postgres://","postgresql://")) else "sqlite","persistent_worker_history":True,"uptime_seconds":int(time.time()-_started)}

@app.get("/api/system/ready")
def system_ready():
    connected=worker_fresh()
    checks = {
        "worker_token_configured": bool(WORKER_TOKEN),
        "worker_heartbeat_fresh": connected,
        "worker_diagnostics_received": bool(_worker.get("diagnostics")) if connected else False,
        "model_adapter_verified": False,
        "durable_job_queue": True,
        "durable_queue_storage": _jobs().storage_info()["durable"],
        "private_result_storage": True,
        "private_result_storage_durable": _artifacts().storage_info()["durability_verified"],
        "user_authentication": False,
        "successful_render_verified": False,
        "persistent_worker_history": True,
    }
    production_gates = {
        "verified_model_adapter": False,
        "worker_connected": connected,
        "durable_queue_storage": checks["durable_queue_storage"],
        "durable_artifact_storage": checks["private_result_storage_durable"],
        "creator_authentication": False,
        "successful_end_to_end_render": False,
    }
    return {
        "api": "ready",
        "api_version": APP_VERSION,
        "worker": "connected" if connected else "offline",
        "engine": "preflight_agent_connected" if connected else "not_configured",
        "generation_enabled": False,
        "generation_reason": "Generation remains disabled until every production gate passes and a real render is verified.",
        "checks": checks,
        "production_gates": production_gates,
        "production_blockers": [name for name, passed in production_gates.items() if not passed],
    }

@app.get("/api/capabilities")
def capabilities():
    fresh=worker_fresh()
    return {
        "api_version":APP_VERSION,
        "generation_enabled":False,
        "reason":"No verified inference adapter, creator authentication or successful end-to-end render is configured.",
        "worker":{
            "connected":fresh,
            "worker_connected":fresh,
            "engine_ready_reported":False,
            "capabilities":["creative-planning","project-export"]
        },
        "supported_request_modes":["text","image"],
        "planned_features":["verified_model_adapters","durable_generation_jobs","reference_image_conditioning","durable_private_artifact_storage","authenticated_project_sync"]
    }

@app.get("/api/models")
def models():
    """Candidate catalog; entries are never presented as installed or runnable."""
    return {"models":MODEL_CATALOG,"verified_model_count":0,"generation_enabled":False}

@app.get("/api/engines")
def engines():
    """Public metadata for provider-neutral engine connection options."""
    items = list_engines()
    return {
        "engines": items,
        "engine_count": len(items),
        "configured_engine_count": 0,
        "verified_engine_count": 0,
        "generation_enabled": False,
        "provider_calls_enabled": False,
        "security_note": "No provider credentials are accepted or transmitted by this registry endpoint."
    }


@app.get("/api/engine-evaluation")
def engine_evaluation():
    """Conservative architecture guidance; no provider requests or user data transfer."""
    return evaluate_engines()

@app.get("/api/engines/{engine_id}")
def engine_detail(engine_id: str):
    """Return one engine descriptor; never returns credential values."""
    item = get_engine(engine_id)
    if item is None:
        raise HTTPException(404, detail={"code":"ENGINE_NOT_FOUND","message":"Engine is not in the registry."})
    return {"engine": item, "generation_enabled": False, "provider_calls_enabled": False}

@app.get("/api/operations/engine-status")
def private_engine_status(x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    items = list_engines()
    return {
        "engines": items,
        "configured_engine_count": 0,
        "verified_engine_count": 0,
        "generation_enabled": False,
        "provider_calls_enabled": False,
        "message": "Registry only. Provider credentials and live endpoint verification are not configured."
    }

@app.get("/api/system/worker-preflight")
def worker_preflight(x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
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
        _record_worker_heartbeat(payload.worker_id,payload.engine,payload.diagnostics)
        _worker.update(connected=True,worker_id=payload.worker_id,engine=payload.engine,engine_ready=False,capabilities=payload.capabilities,diagnostics=payload.diagnostics,last_seen=time.time())
        _events.append({"time":int(time.time()),"kind":"worker_heartbeat","detail":payload.worker_id})
    return {"accepted":True,"worker_id":payload.worker_id,"generation_enabled":False}

@app.get("/api/worker/status")
def worker_status(x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    fresh=worker_fresh()
    return {"connected":fresh,"worker_id":_worker["worker_id"] if fresh else None,"engine":_worker["engine"] if fresh else None,"engine_ready_reported":False,"last_seen_seconds_ago":round(time.time()-_worker["last_seen"],1) if fresh else None,"diagnostics":_worker["diagnostics"] if fresh else {},"generation_enabled":False}

@app.get("/api/worker/history")
def worker_history(limit:int=12,x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    if limit<1 or limit>50:
        raise HTTPException(422,detail={"code":"INVALID_HISTORY_LIMIT","message":"History limit must be between 1 and 50."})
    items=_worker_history(limit)
    return {"items":items,"count":len(items),"retention_limit":250,"storage":"local-sqlite","generation_enabled":False}

@app.get("/api/operations/summary")
def operations_summary(x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    fresh=worker_fresh()
    with _state_db() as db:
        count=db.execute("SELECT COUNT(*) FROM worker_history").fetchone()[0]
    return {"api_version":APP_VERSION,"uptime_seconds":int(time.time()-_started),"worker_connected":fresh,
            "worker_id":_worker["worker_id"] if fresh else None,"worker_history_records":count,
            "generation_enabled":False,"production_state":"preflight-only","persistent_state":"sqlite"}


@app.get("/api/operations/control-room")
def operations_control_room(x_operations_token:str|None=Header(default=None)):
    """Authenticated operational snapshot; excludes prompts, assets and credentials."""
    require_operations_token(x_operations_token)
    fresh = worker_fresh()
    queue = _jobs().operations_snapshot(limit=30)
    engines = list_engines()
    storage_path = os.path.abspath(STATE_DB)
    ephemeral = storage_path == "/tmp" or storage_path.startswith("/tmp/")
    return {
        "api": {"version": APP_VERSION, "uptime_seconds": int(time.time() - _started)},
        "worker": {
            "connected": fresh,
            "worker_id": _worker["worker_id"] if fresh else None,
            "engine": _worker["engine"] if fresh else None,
            "last_seen_seconds_ago": round(time.time() - _worker["last_seen"], 1) if fresh else None,
        },
        "models": {"candidate_count": len(MODEL_CATALOG), "verified_count": 0},
        "engines": {
            "registered_count": len(engines),
            "configured_count": sum(1 for item in engines if item.get("enabled")),
            "verified_count": sum(1 for item in engines if item.get("verified")),
            "provider_calls_enabled": False,
        },
        "queue": queue,
        "storage": {
            "kind": "sqlite",
            "ephemeral": ephemeral,
            "description": "Worker-history SQLite file. Temporary container filesystem; records may be lost on restart or redeploy." if ephemeral else "Worker-history SQLite file; persistence depends on the hosting volume policy.",
        },
        "queue_storage": _jobs().storage_info(),
        "artifacts": _artifacts().snapshot(limit=20),
        "artifact_storage": _artifacts().storage_info(),
        "generation_enabled": False,
        "provider_calls_enabled": False,
        "creative_payloads_included": False,
    }



def _artifacts():
    return ArtifactStore(ARTIFACT_DB, ARTIFACT_DIR)


def _probe_mp4(path: str) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if not executable:
        raise HTTPException(503, detail={"code":"MEDIA_VALIDATOR_UNAVAILABLE","message":"ffprobe is not installed on the backend; the upload was not accepted."})
    try:
        result = subprocess.run(
            [executable, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,width,height",
             "-show_entries", "format=duration,format_name",
             "-of", "json", path],
            check=True, capture_output=True, text=True, timeout=20,
        )
        data = json.loads(result.stdout)
        streams = data.get("streams") or []
        fmt = data.get("format") or {}
        names = str(fmt.get("format_name") or "").split(",")
        if not streams or not any("mp4" in name for name in names):
            raise ValueError("No MP4 video stream was found.")
        stream = streams[0]
        width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
        duration = float(fmt.get("duration") or 0)
        if not (1 <= width <= 16384 and 1 <= height <= 16384 and math.isfinite(duration) and 0 < duration <= 7200):
            raise ValueError("Video dimensions or duration are outside accepted limits.")
        return {"width":width,"height":height,"duration_seconds":round(duration,3),"video_codec":str(stream.get("codec_name") or "unknown")}
    except HTTPException:
        raise
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(422, detail={"code":"INVALID_MP4","message":"The uploaded file did not pass MP4 stream validation."}) from exc


@app.post("/api/worker/artifacts", status_code=201)
async def upload_private_artifact(
    request: Request,
    x_worker_token: str | None = Header(default=None),
    x_worker_id: str = Header(min_length=3, max_length=80, pattern="^[a-zA-Z0-9._-]+$"),
    x_job_id: str | None = Header(default=None),
):
    """Stream a validated MP4 from an authenticated worker into private storage."""
    require_worker_token(x_worker_token)
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "video/mp4":
        raise HTTPException(415, detail={"code":"UNSUPPORTED_ARTIFACT_TYPE","message":"Only video/mp4 uploads are accepted."})
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > MAX_ARTIFACT_BYTES:
                raise HTTPException(413, detail={"code":"ARTIFACT_TOO_LARGE","message":"Artifact exceeds the configured upload limit."})
        except ValueError:
            raise HTTPException(400, detail={"code":"INVALID_CONTENT_LENGTH","message":"Content-Length is invalid."})
    if x_job_id:
        try:
            linked_job = _jobs().get(x_job_id)
        except JobNotFound:
            raise HTTPException(404, detail={"code":"JOB_NOT_FOUND","message":"The referenced queue job does not exist."})
        if linked_job["status"] != "running" or linked_job.get("worker_id") != x_worker_id or (linked_job.get("lease_expires_at") or 0) < time.time():
            raise HTTPException(409, detail={"code":"JOB_LEASE_REQUIRED","message":"The artifact must be uploaded by the worker holding the active job lease."})
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(prefix=".rf983-upload-", suffix=".mp4.part", dir=ARTIFACT_DIR)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(fd, "wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_ARTIFACT_BYTES:
                    raise HTTPException(413, detail={"code":"ARTIFACT_TOO_LARGE","message":"Artifact exceeds the configured upload limit."})
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(400, detail={"code":"EMPTY_ARTIFACT","message":"The uploaded artifact is empty."})
        probe = _probe_mp4(temporary_path)
        item = _artifacts().register(temporary_path, {
            **probe, "worker_id":x_worker_id, "job_id":x_job_id,
            "size_bytes":size, "sha256":digest.hexdigest(), "created_at":time.time(),
        })
        return {"accepted":True,"artifact":item,"generation_enabled":False,"public_url":None}
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


@app.get("/api/operations/artifacts")
def list_private_artifacts(limit: int = 25, x_operations_token: str | None = Header(default=None)):
    require_operations_token(x_operations_token)
    if limit < 1 or limit > 100:
        raise HTTPException(422, detail={"code":"INVALID_ARTIFACT_LIMIT","message":"Limit must be between 1 and 100."})
    snapshot = _artifacts().snapshot(limit)
    return {"items":snapshot["items"],"count":snapshot["count"],"total_bytes":snapshot["total_bytes"],"storage":_artifacts().storage_info(),"generation_enabled":False}


@app.get("/api/operations/artifacts/{artifact_id}")
def get_private_artifact(artifact_id: str, x_operations_token: str | None = Header(default=None)):
    require_operations_token(x_operations_token)
    try:
        return {"artifact":_artifacts().get(artifact_id),"storage":_artifacts().storage_info(),"generation_enabled":False}
    except ArtifactNotFound:
        raise HTTPException(404, detail={"code":"ARTIFACT_NOT_FOUND","message":"Private artifact was not found."})


@app.get("/api/operations/artifacts/{artifact_id}/download")
def download_private_artifact(artifact_id: str, x_operations_token: str | None = Header(default=None)):
    require_operations_token(x_operations_token)
    try:
        item = _artifacts().get(artifact_id)
        path = _artifacts().file_path(artifact_id)
    except ArtifactNotFound:
        raise HTTPException(404, detail={"code":"ARTIFACT_NOT_FOUND","message":"Private artifact was not found."})
    return FileResponse(path, media_type="video/mp4", filename="rf983-"+artifact_id[:8]+".mp4", headers={"Cache-Control":"no-store","X-Artifact-SHA256":item["sha256"]})


def _queue_database():
    return QUEUE_DB or STATE_DB

def _jobs():
    return JobStore(_queue_database())

@app.post("/api/worker/jobs/claim")
def claim_worker_job(
    x_worker_token:str|None=Header(default=None),
    x_worker_id:str=Header(min_length=3,max_length=80,pattern="^[a-zA-Z0-9._-]+$"),
    lease_seconds:int=300,
):
    """Claim one queued job and disclose its creative payload only to an authenticated worker."""
    require_worker_token(x_worker_token)
    try:
        item=_jobs().claim(x_worker_id,lease_seconds=lease_seconds)
    except JobStoreError as exc:
        raise HTTPException(422,detail={"code":"INVALID_JOB_CLAIM","message":str(exc)})
    if item is None:
        return {"claimed":False,"job":None,"worker_execution_protocol":"2.0","generation_enabled":False}
    return {"claimed":True,"job":{"id":item["id"],"payload":item["payload"],"attempts":item["attempts"],"lease_expires_at":item["lease_expires_at"]},"worker_execution_protocol":"2.0","generation_enabled":False}

@app.post("/api/worker/jobs/{job_id}/heartbeat")
def heartbeat_worker_job(
    job_id:str,
    x_worker_token:str|None=Header(default=None),
    x_worker_id:str=Header(min_length=3,max_length=80,pattern="^[a-zA-Z0-9._-]+$"),
    lease_seconds:int=300,
):
    require_worker_token(x_worker_token)
    try:
        item=_jobs().heartbeat(job_id,x_worker_id,lease_seconds=lease_seconds)
        return {"renewed":True,"job_id":item["id"],"lease_expires_at":item["lease_expires_at"],"generation_enabled":False}
    except JobNotFound:
        raise HTTPException(404,detail={"code":"JOB_NOT_FOUND","message":"Queue job was not found."})
    except (InvalidJobTransition,JobStoreError) as exc:
        raise HTTPException(409,detail={"code":"JOB_LEASE_LOST","message":str(exc)})

@app.post("/api/worker/jobs/{job_id}/complete")
def complete_worker_job(
    job_id:str,
    request:WorkerCompletion,
    x_worker_token:str|None=Header(default=None),
    x_worker_id:str=Header(min_length=3,max_length=80,pattern="^[a-zA-Z0-9._-]+$"),
):
    """Mark success only when this leased worker uploaded the matching validated MP4."""
    require_worker_token(x_worker_token)
    try:
        job=_jobs().get(job_id)
        artifact=_artifacts().get(request.artifact_id)
    except JobNotFound:
        raise HTTPException(404,detail={"code":"JOB_NOT_FOUND","message":"Queue job was not found."})
    except ArtifactNotFound:
        raise HTTPException(404,detail={"code":"ARTIFACT_NOT_FOUND","message":"Validated private artifact was not found."})
    if artifact.get("job_id") != job_id or artifact.get("worker_id") != x_worker_id:
        raise HTTPException(409,detail={"code":"ARTIFACT_JOB_MISMATCH","message":"The artifact must belong to this job and authenticated worker."})
    try:
        item=_jobs().complete(job_id,x_worker_id,{"artifact_id":artifact["id"],"sha256":artifact["sha256"],"size_bytes":artifact["size_bytes"],"duration_seconds":artifact["duration_seconds"],"width":artifact["width"],"height":artifact["height"],"video_codec":artifact["video_codec"]})
    except (InvalidJobTransition,JobStoreError) as exc:
        raise HTTPException(409,detail={"code":"JOB_COMPLETION_REJECTED","message":str(exc)})
    return {"completed":True,"job":_job_public(item),"artifact":artifact,"generation_enabled":False}

@app.post("/api/worker/jobs/{job_id}/fail")
def fail_worker_job(
    job_id:str,
    request:WorkerFailure,
    x_worker_token:str|None=Header(default=None),
    x_worker_id:str=Header(min_length=3,max_length=80,pattern="^[a-zA-Z0-9._-]+$"),
):
    require_worker_token(x_worker_token)
    try:
        item=_jobs().fail(job_id,x_worker_id,request.error_code,request.message,retry=request.retry)
        return {"accepted":True,"job":_job_public(item),"generation_enabled":False}
    except JobNotFound:
        raise HTTPException(404,detail={"code":"JOB_NOT_FOUND","message":"Queue job was not found."})
    except (InvalidJobTransition,JobStoreError) as exc:
        raise HTTPException(409,detail={"code":"JOB_FAILURE_REJECTED","message":str(exc)})

def _job_public(item, include_payload=False):
    data={key:item.get(key) for key in ("id","status","created_at","updated_at","attempts","max_attempts","worker_id","lease_expires_at","error_code","error_message")}
    if include_payload:
        data["payload"]=item.get("payload")
    data["result"]=item.get("result")
    return data

@app.post("/api/operations/queue/jobs", status_code=202)
def enqueue_private_job(request:GenerateRequest,x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    try:
        item=_jobs().enqueue(request.model_dump(),max_attempts=2)
    except JobStoreError as exc:
        raise HTTPException(422,detail={"code":"INVALID_QUEUE_JOB","message":str(exc)})
    return {"accepted":True,"generation_enabled":False,"job":_job_public(item)}

@app.get("/api/operations/queue/jobs")
def list_private_jobs(limit:int=25,x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    if limit<1 or limit>100:
        raise HTTPException(422,detail={"code":"INVALID_QUEUE_LIMIT","message":"Limit must be between 1 and 100."})
    return {"items":[_job_public(item) for item in _jobs().list(limit)],"limit":limit,"generation_enabled":False}

@app.get("/api/operations/queue/jobs/{job_id}")
def get_private_job(job_id:str,x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    try:
        return {"job":_job_public(_jobs().get(job_id),include_payload=True),"generation_enabled":False}
    except JobNotFound:
        raise HTTPException(404,detail={"code":"JOB_NOT_FOUND","message":"Queue job was not found."})

@app.post("/api/operations/queue/jobs/{job_id}/cancel")
def cancel_private_job(job_id:str,x_operations_token:str|None=Header(default=None)):
    require_operations_token(x_operations_token)
    try:
        item=_jobs().cancel(job_id)
        return {"cancelled":True,"job":_job_public(item),"generation_enabled":False}
    except JobNotFound:
        raise HTTPException(404,detail={"code":"JOB_NOT_FOUND","message":"Queue job was not found."})
    except InvalidJobTransition:
        raise HTTPException(409,detail={"code":"JOB_NOT_CANCELLABLE","message":"A terminal queue job cannot be cancelled."})


@app.post("/api/generate",status_code=503)
def generate(request:GenerateRequest):
    raise HTTPException(503,detail={"code":"INFERENCE_NOT_CONFIGURED","message":"No verified video-generation adapter is enabled. No generation job was created.","api_version":APP_VERSION})

@app.get("/api/jobs/{job_id}")
def get_job(job_id:str):
    raise HTTPException(503,detail={"code":"JOB_SERVICE_NOT_CONFIGURED","message":"Persistent job queue and private render storage are not configured.","job_id":job_id})
