"""Durable, lease-based generation job store (not yet exposed to public API).

The store is deliberately provider-neutral. It persists only bounded job metadata
and never stores prompts' reference-image bytes or rendered media.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}
TERMINAL = {"succeeded", "failed", "cancelled"}


class JobStoreError(ValueError):
    pass


class JobNotFound(JobStoreError):
    pass


class InvalidJobTransition(JobStoreError):
    pass


class JobStore:
    """SQLite queue with atomic claims, expiring leases and bounded retries."""

    def __init__(self, database: str | Path, max_payload_bytes: int = 32_000):
        self.database = str(database)
        self.max_payload_bytes = max_payload_bytes
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS generation_jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    worker_id TEXT,
                    lease_expires_at REAL,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_claim ON generation_jobs(status, created_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_worker ON generation_jobs(worker_id, status)")

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
        return item

    def enqueue(self, payload: dict[str, Any], max_attempts: int = 2) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise JobStoreError("Job payload must be a JSON object.")
        if not 1 <= max_attempts <= 5:
            raise JobStoreError("max_attempts must be between 1 and 5.")
        try:
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise JobStoreError("Job payload must contain finite JSON values only.") from exc
        if len(encoded.encode("utf-8")) > self.max_payload_bytes:
            raise JobStoreError("Job payload exceeds the configured size limit.")
        now = time.time()
        job_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO generation_jobs(id,status,payload_json,created_at,updated_at,max_attempts) VALUES(?,?,?,?,?,?)",
                (job_id, "queued", encoded, now, now, max_attempts),
            )
            row = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
            db.commit()
        return self._row(row)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
        item = self._row(row)
        if item is None:
            raise JobNotFound("Generation job was not found.")
        return item

    def list(self, limit: int = 25) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise JobStoreError("limit must be between 1 and 100.")
        with self._connect() as db:
            rows = db.execute("SELECT * FROM generation_jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(row) for row in rows]

    def claim(self, worker_id: str, lease_seconds: int = 300) -> dict[str, Any] | None:
        if not worker_id or len(worker_id) > 80:
            raise JobStoreError("worker_id must contain 1–80 characters.")
        if not 15 <= lease_seconds <= 3600:
            raise JobStoreError("lease_seconds must be between 15 and 3600.")
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Expired jobs are requeued unless their bounded attempt budget is spent.
            db.execute("""
                UPDATE generation_jobs
                SET status=CASE WHEN attempts >= max_attempts THEN 'failed' ELSE 'queued' END,
                    worker_id=NULL, lease_expires_at=NULL, updated_at=?,
                    error_code=CASE WHEN attempts >= max_attempts THEN 'LEASE_EXPIRED' ELSE error_code END,
                    error_message=CASE WHEN attempts >= max_attempts THEN 'Worker lease expired; retry budget exhausted.' ELSE error_message END
                WHERE status='running' AND lease_expires_at < ?
            """, (now, now))
            row = db.execute(
                "SELECT * FROM generation_jobs WHERE status='queued' AND attempts < max_attempts ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                db.commit()
                return None
            db.execute(
                "UPDATE generation_jobs SET status='running',worker_id=?,attempts=attempts+1,lease_expires_at=?,updated_at=? WHERE id=? AND status='queued'",
                (worker_id, now + lease_seconds, now, row["id"]),
            )
            claimed = db.execute("SELECT * FROM generation_jobs WHERE id=?", (row["id"],)).fetchone()
            db.commit()
        return self._row(claimed)

    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int = 300) -> dict[str, Any]:
        if not 15 <= lease_seconds <= 3600:
            raise JobStoreError("lease_seconds must be between 15 and 3600.")
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                "UPDATE generation_jobs SET lease_expires_at=?,updated_at=? WHERE id=? AND status='running' AND worker_id=? AND lease_expires_at>=?",
                (now + lease_seconds, now, job_id, worker_id, now),
            )
            if cursor.rowcount != 1:
                db.rollback()
                raise InvalidJobTransition("Job is not leased to this worker or its lease has expired.")
            row = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
            db.commit()
        return self._row(row)

    def complete(self, job_id: str, worker_id: str, result: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode("utf-8")) > self.max_payload_bytes:
            raise JobStoreError("Job result exceeds the configured size limit.")
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                "UPDATE generation_jobs SET status='succeeded',result_json=?,worker_id=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND status='running' AND worker_id=? AND lease_expires_at>=?",
                (encoded, now, job_id, worker_id, now),
            )
            if cursor.rowcount != 1:
                db.rollback()
                raise InvalidJobTransition("Only the currently leased worker can complete this job.")
            row = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
            db.commit()
        return self._row(row)

    def fail(self, job_id: str, worker_id: str, error_code: str, message: str, retry: bool = True) -> dict[str, Any]:
        if not error_code or len(error_code) > 80 or len(message) > 500:
            raise JobStoreError("Failure code or message is invalid.")
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                db.rollback()
                raise JobNotFound("Generation job was not found.")
            if row["status"] != "running" or row["worker_id"] != worker_id or (row["lease_expires_at"] or 0) < now:
                db.rollback()
                raise InvalidJobTransition("Only the currently leased worker can fail this job.")
            next_status = "queued" if retry and row["attempts"] < row["max_attempts"] else "failed"
            db.execute(
                "UPDATE generation_jobs SET status=?,worker_id=NULL,lease_expires_at=NULL,updated_at=?,error_code=?,error_message=? WHERE id=?",
                (next_status, now, error_code, message, job_id),
            )
            updated = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
            db.commit()
        return self._row(updated)

    def cancel(self, job_id: str) -> dict[str, Any]:
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                db.rollback()
                raise JobNotFound("Generation job was not found.")
            if row["status"] in TERMINAL:
                db.rollback()
                raise InvalidJobTransition("A terminal job cannot be cancelled.")
            db.execute(
                "UPDATE generation_jobs SET status='cancelled',worker_id=NULL,lease_expires_at=NULL,updated_at=? WHERE id=?",
                (now, job_id),
            )
            updated = db.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()
            db.commit()
        return self._row(updated)


    def operations_snapshot(self, limit: int = 30) -> dict[str, Any]:
        """Return queue counts and safe operational metadata, never job payloads."""
        if not 1 <= limit <= 100:
            raise JobStoreError("limit must be between 1 and 100.")
        with self._connect() as db:
            grouped = db.execute(
                "SELECT status, COUNT(*) AS amount FROM generation_jobs GROUP BY status"
            ).fetchall()
            rows = db.execute(
                """SELECT id,status,created_at,updated_at,attempts,max_attempts,
                          worker_id,lease_expires_at,error_code,error_message
                   FROM generation_jobs ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        counts = {status: 0 for status in STATUSES}
        for row in grouped:
            if row["status"] in counts:
                counts[row["status"]] = int(row["amount"])
        return {
            "counts": counts,
            "total": sum(counts.values()),
            "items": [dict(row) for row in rows],
            "limit": limit,
        }
