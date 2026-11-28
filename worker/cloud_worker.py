"""Cloud-hosted RF983 MOTION worker runtime."""
from __future__ import annotations
import argparse, http.client, importlib, json, os, ssl, sys, threading, time
from pathlib import Path
from urllib.parse import urlparse
try:
    from .engine_contract import RenderRequest, RenderResult, RenderArtifactValidator
except ImportError:
    from engine_contract import RenderRequest, RenderResult, RenderArtifactValidator

class WorkerConfigError(ValueError): pass
class LeaseLost(RuntimeError): pass

def load_config(env=None):
    env = env or os.environ
    base = env.get("RF983_API_BASE", "").strip().rstrip("/")
    token = env.get("RF983_WORKER_TOKEN", "")
    worker_id = env.get("RF983_WORKER_ID", "").strip()
    adapter_path = env.get("RF983_ENGINE_ADAPTER", "").strip()
    output = Path(env.get("RF983_OUTPUT_DIR", "./renders")).expanduser().resolve()
    poll = int(env.get("RF983_WORKER_POLL_SECONDS", "5"))
    lease = int(env.get("RF983_WORKER_LEASE_SECONDS", "900"))
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise WorkerConfigError("RF983_API_BASE must be an HTTPS origin without credentials, path, query or fragment.")
    if not token or len(token) < 16:
        raise WorkerConfigError("RF983_WORKER_TOKEN must be configured as a secret environment variable.")
    if not worker_id or not 3 <= len(worker_id) <= 80 or not all(c.isalnum() or c in "._-" for c in worker_id):
        raise WorkerConfigError("RF983_WORKER_ID must be 3–80 letters, numbers, dots, underscores or hyphens.")
    if not adapter_path or ":" not in adapter_path:
        raise WorkerConfigError("RF983_ENGINE_ADAPTER must be an installed module path in module:function format.")
    if not 1 <= poll <= 60 or not 15 <= lease <= 3600:
        raise WorkerConfigError("Polling interval or lease duration is outside the supported range.")
    output.mkdir(parents=True, exist_ok=True)
    return {"api_base":base,"token":token,"worker_id":worker_id,"adapter_path":adapter_path,"output_dir":output,"poll_seconds":poll,"lease_seconds":lease}

def load_adapter(adapter_path):
    module_name, factory_name = adapter_path.split(":", 1)
    if not module_name or not factory_name or not module_name.replace("_","").replace(".","").isalnum() or not factory_name.isidentifier():
        raise WorkerConfigError("Adapter path is invalid.")
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name, None)
    if not callable(factory):
        raise WorkerConfigError("Configured adapter factory is not callable.")
    adapter = factory()
    if not callable(getattr(adapter,"is_available",None)) or not callable(getattr(adapter,"render",None)):
        raise WorkerConfigError("Adapter must implement is_available() and render().")
    ready, reason = adapter.is_available()
    if not ready:
        raise WorkerConfigError("Configured adapter is not ready: " + str(reason)[:300])
    if not isinstance(getattr(adapter,"model_id",None),str) or not adapter.model_id.strip():
        raise WorkerConfigError("Adapter must expose a non-empty model_id.")
    return adapter

class CloudWorker:
    def __init__(self, config, adapter):
        self.config, self.adapter = config, adapter
        self.validator = RenderArtifactValidator(config["output_dir"])

    def _json_request(self, method, path, payload=None):
        import urllib.request
        from urllib.error import HTTPError, URLError
        body = None if payload is None else json.dumps(payload,separators=(",",":")).encode()
        request = urllib.request.Request(self.config["api_base"]+path,data=body,method=method,headers={
            "X-Worker-Token":self.config["token"],"X-Worker-ID":self.config["worker_id"],"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(request,timeout=30) as response:
                raw=response.read(1024*1024)
                return json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as exc:
            detail=exc.read(4096).decode("utf-8","replace")
            raise RuntimeError(f"API returned HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise RuntimeError("Could not reach RF983 MOTION API: "+str(exc.reason)[:200]) from exc

    def claim(self):
        return self._json_request("POST","/api/worker/jobs/claim?lease_seconds="+str(self.config["lease_seconds"]))

    def _renew_lease(self,job_id,stop,lost):
        interval=max(5,self.config["lease_seconds"]//3)
        while not stop.wait(interval):
            try:
                self._json_request("POST",f"/api/worker/jobs/{job_id}/heartbeat?lease_seconds={self.config['lease_seconds']}")
            except Exception:
                lost.set()
                return

    @staticmethod
    def _render_request(payload):
        if payload.get("mode","text") != "text":
            raise WorkerConfigError("This worker runtime currently accepts text-to-video jobs only.")
        if payload.get("audio",False):
            raise WorkerConfigError("This worker runtime does not accept audio-generation jobs.")
        return RenderRequest(prompt=payload["prompt"],negative_prompt=payload.get("negative_prompt",""),mode="text",
            aspect_ratio=payload.get("aspect_ratio","16:9"),resolution=payload.get("resolution","720p"),
            duration_seconds=int(payload.get("duration_seconds",5)),fps=int(payload.get("fps",24)),seed=payload.get("seed"))

    def _upload(self,job_id,path):
        parsed=urlparse(self.config["api_base"])
        connection=http.client.HTTPSConnection(parsed.hostname,parsed.port or 443,timeout=120,context=ssl.create_default_context())
        size=path.stat().st_size
        try:
            connection.putrequest("POST","/api/worker/artifacts")
            for key,value in {"Host":parsed.netloc,"Content-Type":"video/mp4","Content-Length":str(size),
                "X-Worker-Token":self.config["token"],"X-Worker-ID":self.config["worker_id"],"X-Job-ID":job_id}.items():
                connection.putheader(key,value)
            connection.endheaders()
            with path.open("rb") as source:
                while True:
                    chunk=source.read(1024*1024)
                    if not chunk: break
                    connection.send(chunk)
            response=connection.getresponse()
            raw=response.read(1024*1024)
            if response.status != 201:
                raise RuntimeError(f"Artifact upload failed with HTTP {response.status}: {raw[:500].decode('utf-8','replace')}")
            return json.loads(raw.decode("utf-8"))
        finally:
            connection.close()

    def process(self,job):
        job_id=job["id"]; stop=threading.Event(); lost=threading.Event()
        heartbeat=threading.Thread(target=self._renew_lease,args=(job_id,stop,lost),daemon=True)
        heartbeat.start()
        try:
            request=self._render_request(job["payload"])
            result=self.adapter.render(request,self.config["output_dir"])
            if not isinstance(result,RenderResult):
                raise WorkerConfigError("Adapter render() must return a RenderResult.")
            if lost.is_set(): raise LeaseLost("Worker lease was lost during rendering; result will not be uploaded.")
            metadata=self.validator.validate(Path(result.output_path))
            if lost.is_set(): raise LeaseLost("Worker lease expired before artifact upload.")
            upload=self._upload(job_id,Path(metadata["path"]))
            artifact_id=upload["artifact"]["id"]
            return self._json_request("POST",f"/api/worker/jobs/{job_id}/complete",{"artifact_id":artifact_id})
        except Exception as exc:
            if not lost.is_set() and not isinstance(exc,LeaseLost):
                try:
                    self._json_request("POST",f"/api/worker/jobs/{job_id}/fail",{
                        "error_code":"WORKER_RENDER_FAILED","message":str(exc)[:450] or "Worker execution failed.","retry":True})
                except Exception: pass
            raise
        finally:
            stop.set(); heartbeat.join(timeout=2)

    def run_forever(self):
        print(f"RF983 cloud worker ready · worker={self.config['worker_id']} · model={self.adapter.model_id}",flush=True)
        while True:
            try:
                response=self.claim()
                if not response.get("claimed"):
                    time.sleep(self.config["poll_seconds"]); continue
                job=response["job"]
                print(f"Claimed job {job['id']} · attempt {job.get('attempts')}",flush=True)
                try:
                    result=self.process(job)
                    print(f"Job {job['id']} completed · {result.get('job',{}).get('status','accepted')}",flush=True)
                except Exception as exc:
                    print(f"Job {job['id']} did not complete: {str(exc)[:300]}",file=sys.stderr,flush=True)
            except KeyboardInterrupt:
                print("Worker shutdown requested.",flush=True); return
            except Exception as exc:
                print(f"Worker loop error: {str(exc)[:300]}",file=sys.stderr,flush=True)
                time.sleep(max(5,self.config["poll_seconds"]))

def main():
    parser=argparse.ArgumentParser(description="RF983 MOTION authenticated cloud GPU worker")
    parser.add_argument("--check",action="store_true",help="Validate configuration and adapter without claiming jobs")
    args=parser.parse_args()
    try:
        config=load_config(); adapter=load_adapter(config["adapter_path"])
        print(json.dumps({"ready":True,"worker_id":config["worker_id"],"api_origin":urlparse(config["api_base"]).netloc,
            "model_id":adapter.model_id,"output_dir":str(config["output_dir"]),"check_only":args.check},indent=2))
        if not args.check: CloudWorker(config,adapter).run_forever()
    except Exception as exc:
        print("Worker startup blocked: "+str(exc),file=sys.stderr); raise SystemExit(2)

if __name__=="__main__": main()
