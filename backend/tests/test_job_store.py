import time
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.job_store import JobStore, JobStoreError, JobNotFound, InvalidJobTransition


def store(tmp_path, **kwargs):
    return JobStore(tmp_path / "jobs.sqlite3", **kwargs)


def test_enqueue_persists_and_lists(tmp_path):
    q = store(tmp_path)
    job = q.enqueue({"prompt": "A cinematic mountain sunrise"})
    assert job["status"] == "queued"
    assert q.get(job["id"])["payload"]["prompt"].startswith("A cinematic")
    assert q.list()[0]["id"] == job["id"]


def test_atomic_claim_and_owner_only_completion(tmp_path):
    q = store(tmp_path)
    job = q.enqueue({"prompt": "A film"})
    claimed = q.claim("worker-a", lease_seconds=30)
    assert claimed["id"] == job["id"] and claimed["attempts"] == 1
    with pytest.raises(InvalidJobTransition):
        q.complete(job["id"], "worker-b", {"path": "movie.mp4"})
    done = q.complete(job["id"], "worker-a", {"verified": True})
    assert done["status"] == "succeeded" and done["result"]["verified"] is True


def test_heartbeat_extends_only_current_lease(tmp_path):
    q = store(tmp_path)
    job = q.enqueue({"prompt": "A film"})
    q.claim("worker-a", 30)
    assert q.heartbeat(job["id"], "worker-a", 60)["lease_expires_at"] > time.time()
    with pytest.raises(InvalidJobTransition):
        q.heartbeat(job["id"], "worker-b", 60)


def test_failure_retries_with_bounded_attempts(tmp_path):
    q = store(tmp_path)
    job = q.enqueue({"prompt": "A film"}, max_attempts=2)
    q.claim("worker-a", 30)
    retried = q.fail(job["id"], "worker-a", "TEMPORARY", "Worker restarted")
    assert retried["status"] == "queued"
    q.claim("worker-b", 30)
    failed = q.fail(job["id"], "worker-b", "MODEL_ERROR", "Render failed")
    assert failed["status"] == "failed"


def test_expired_lease_is_reclaimed(tmp_path):
    q = store(tmp_path)
    job = q.enqueue({"prompt": "A film"}, max_attempts=2)
    q.claim("worker-a", 15)
    with q._connect() as db:
        db.execute("UPDATE generation_jobs SET lease_expires_at=? WHERE id=?", (time.time()-1, job["id"]))
    reclaimed = q.claim("worker-b", 30)
    assert reclaimed["id"] == job["id"] and reclaimed["attempts"] == 2
    with pytest.raises(InvalidJobTransition):
        q.complete(job["id"], "worker-a", {"ok": True})


def test_cancel_and_terminal_transition_guard(tmp_path):
    q = store(tmp_path)
    job = q.enqueue({"prompt": "A film"})
    assert q.cancel(job["id"])["status"] == "cancelled"
    with pytest.raises(InvalidJobTransition):
        q.cancel(job["id"])


def test_payload_and_limits_are_bounded(tmp_path):
    q = store(tmp_path, max_payload_bytes=40)
    with pytest.raises(JobStoreError):
        q.enqueue({"prompt": "x" * 100})
    with pytest.raises(JobStoreError):
        q.enqueue({"prompt": "ok"}, max_attempts=99)
    with pytest.raises(JobStoreError):
        q.list(1000)


def test_unknown_job_is_explicit(tmp_path):
    q = store(tmp_path)
    with pytest.raises(JobNotFound):
        q.get("missing")


def test_postgresql_storage_is_recognized_without_connecting():
    q = JobStore.__new__(JobStore)
    q.database = "postgresql://user:password@db.example.invalid:5432/rf983"
    q.is_postgres = True
    info = q.storage_info()
    assert info["kind"] == "postgresql"
    assert info["durable"] is True
    assert info["ephemeral"] is False
    assert "provider" in info["description"].lower()


def test_sqlite_storage_reports_ephemeral_container_path():
    q = JobStore("/tmp/rf983-test-queue.sqlite3")
    info = q.storage_info()
    assert info["kind"] == "sqlite"
    assert info["ephemeral"] is True
    assert info["durable"] is False


@pytest.mark.skipif(not os.getenv("RF983_TEST_POSTGRES_URL"), reason="PostgreSQL integration service is not configured")
def test_postgresql_queue_concurrent_claims_and_completion():
    q = JobStore(os.environ["RF983_TEST_POSTGRES_URL"])
    with q._connect() as db:
        db.execute("DELETE FROM generation_jobs")
    first = q.enqueue({"prompt": "PostgreSQL queue integration A"})
    second = q.enqueue({"prompt": "PostgreSQL queue integration B"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda worker: q.claim(worker, lease_seconds=60), ["gpu-a", "gpu-b"]))
    assert all(claim is not None for claim in claims)
    assert {claim["id"] for claim in claims} == {first["id"], second["id"]}
    for claim in claims:
        completed = q.complete(claim["id"], claim["worker_id"], {"verified": True})
        assert completed["status"] == "succeeded"
        assert completed["result"]["verified"] is True
