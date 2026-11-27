"""Private, metadata-indexed storage for validated video artifacts."""
from __future__ import annotations

import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any


class ArtifactNotFound(KeyError):
    pass


class ArtifactStore:
    def __init__(self, database: str | Path, root: str | Path):
        self.database = str(database)
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    worker_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    video_codec TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_job ON artifacts(job_id)")

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _item(row) -> dict[str, Any]:
        return dict(row)

    def register(self, temporary_path: str | Path, metadata: dict[str, Any]) -> dict[str, Any]:
        artifact_id = uuid.uuid4().hex
        final_path = self.root / (artifact_id + ".mp4")
        item = {
            "id": artifact_id,
            "job_id": metadata.get("job_id"),
            "worker_id": metadata["worker_id"],
            "filename": artifact_id + ".mp4",
            "content_type": "video/mp4",
            "size_bytes": int(metadata["size_bytes"]),
            "sha256": metadata["sha256"],
            "duration_seconds": float(metadata["duration_seconds"]),
            "width": int(metadata["width"]),
            "height": int(metadata["height"]),
            "video_codec": str(metadata["video_codec"])[:40],
            "created_at": float(metadata["created_at"]),
        }
        os.replace(str(temporary_path), final_path)
        try:
            with self._connect() as db:
                db.execute(
                    """INSERT INTO artifacts
                    (id,job_id,worker_id,filename,content_type,size_bytes,sha256,duration_seconds,width,height,video_codec,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    tuple(item[key] for key in ("id","job_id","worker_id","filename","content_type","size_bytes","sha256","duration_seconds","width","height","video_codec","created_at")),
                )
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
        return item

    def get(self, artifact_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{32}", artifact_id or ""):
            raise ArtifactNotFound(artifact_id)
        with self._connect() as db:
            row = db.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
        if row is None:
            raise ArtifactNotFound(artifact_id)
        return self._item(row)

    def list(self, limit: int = 25) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as db:
            rows = db.execute("SELECT * FROM artifacts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._item(row) for row in rows]

    def snapshot(self, limit: int = 20) -> dict[str, Any]:
        with self._connect() as db:
            count = db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            total = db.execute("SELECT COALESCE(SUM(size_bytes),0) FROM artifacts").fetchone()[0]
        return {"count": int(count), "total_bytes": int(total), "items": self.list(limit)}

    def file_path(self, artifact_id: str) -> Path:
        item = self.get(artifact_id)
        path = (self.root / item["filename"]).resolve()
        if path.parent != self.root or not path.is_file():
            raise ArtifactNotFound(artifact_id)
        return path

    def storage_info(self) -> dict[str, Any]:
        path = str(self.root)
        ephemeral = path == "/tmp" or path.startswith("/tmp/")
        return {
            "kind": "private-local-filesystem",
            "path_class": "temporary-container" if ephemeral else "configured-path",
            "ephemeral": ephemeral,
            "durability_verified": False,
            "description": "Private temporary container storage; artifacts may be lost on restart or redeploy." if ephemeral else "Private local storage path; mounted-volume durability and backups have not been verified.",
        }
