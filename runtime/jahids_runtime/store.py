"""SQLite mission persistence; provider secrets are never stored."""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

class MissionStore:
    def __init__(self, path=None):
        self.path = path or os.getenv("JAHIDS_DB_PATH", "./data/jahids-runtime.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY, provider TEXT NOT NULL, prompt TEXT NOT NULL,
                category TEXT NOT NULL, payload_hash TEXT NOT NULL, status TEXT NOT NULL,
                approval_id TEXT, result TEXT, error TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    def create(self, mission):
        now = datetime.now(timezone.utc).isoformat()
        row = {**mission, "status":"pending_approval", "approval_id":None, "result":None, "error":None, "created_at":now, "updated_at":now}
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO missions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row["id"], row["provider"], row["prompt"], row["category"], row["payload_hash"], row["status"], None, None, None, now, now))
        return row
    def get(self, mission_id):
        with self.lock, self.connect() as db:
            row = db.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
        return dict(row) if row else None
    def list(self, limit=50):
        with self.lock, self.connect() as db:
            rows = db.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (min(max(limit,1),100),)).fetchall()
        return [dict(row) for row in rows]
    def update(self, mission_id, **fields):
        allowed = {"status", "approval_id", "result", "error"}
        if not fields or not set(fields).issubset(allowed):
            raise ValueError("invalid mission update fields")
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        assignments = ", ".join(key + "=?" for key in fields)
        values = [__import__("json").dumps(value) if key == "result" and value is not None else value for key,value in fields.items()]
        with self.lock, self.connect() as db:
            db.execute("UPDATE missions SET " + assignments + " WHERE id=?", (*values, mission_id))
        return self.get(mission_id)
