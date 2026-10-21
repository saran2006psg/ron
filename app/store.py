from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path

from .models import JobState


class JobStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.Lock()
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, request_json TEXT NOT NULL,
                state TEXT NOT NULL, progress INTEGER NOT NULL, error_json TEXT,
                results_json TEXT NOT NULL DEFAULT '{}', warnings_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        return db

    def create_or_get(self, key: str, request: dict) -> tuple[str, bool]:
        with self.lock, self._connect() as db:
            row = db.execute("SELECT id FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
            if row:
                return row["id"], True
            job_id = str(uuid.uuid4())
            db.execute("INSERT INTO jobs(id,idempotency_key,request_json,state,progress) VALUES(?,?,?,?,?)",
                       (job_id, key, json.dumps(request), JobState.queued.value, 0))
            return job_id, False

    def get(self, job_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        for key in ("request_json", "error_json", "results_json", "warnings_json"):
            data[key] = json.loads(data[key]) if data[key] else None
        return data

    def update(self, job_id: str, state: JobState | None = None, progress: int | None = None,
               error: dict | None = None, results: dict | None = None, warnings: list[str] | None = None) -> None:
        sets, values = ["updated_at=CURRENT_TIMESTAMP"], []
        for column, value in (("state", state.value if state else None), ("progress", progress),
                              ("error_json", json.dumps(error) if error else None),
                              ("results_json", json.dumps(results) if results is not None else None),
                              ("warnings_json", json.dumps(warnings) if warnings is not None else None)):
            if value is not None:
                sets.append(f"{column}=?")
                values.append(value)
        values.append(job_id)
        with self.lock, self._connect() as db:
            db.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", values)

