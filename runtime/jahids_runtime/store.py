"""SQLite mission persistence; provider secrets are never stored."""
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

class MissionStore:
    def __init__(self, path=None):
        self.path = path or os.getenv("JAHIDS_DB_PATH", "./data/jahids-runtime.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY, provider TEXT NOT NULL, prompt TEXT NOT NULL,
                category TEXT NOT NULL, payload_hash TEXT NOT NULL, status TEXT NOT NULL,
                approval_id TEXT, approval_expires_at TEXT, result TEXT, error TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(missions)")}
            if "approval_expires_at" not in columns:
                db.execute("ALTER TABLE missions ADD COLUMN approval_expires_at TEXT")
            db.execute("""CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                mission_id TEXT,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload_hash TEXT,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_mission_created_id ON audit_events(mission_id, created_at DESC, id DESC)")
        # Mission prompts/results can contain private data; restrict the database file.
        os.chmod(self.path, 0o600)
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    @staticmethod
    def decode(row):
        if not row: return None
        result = dict(row)
        if result.get("result"): result["result"] = json.loads(result["result"])
        return result
    def create(self, mission):
        now = datetime.now(timezone.utc).isoformat()
        row = {**mission,"status":"pending_approval","approval_id":None,"approval_expires_at":None,"result":None,"error":None,"created_at":now,"updated_at":now}
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO missions (id,provider,prompt,category,payload_hash,status,approval_id,approval_expires_at,result,error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (row["id"],row["provider"],row["prompt"],row["category"],row["payload_hash"],row["status"],None,None,None,None,now,now))
        return row
    def get(self, mission_id):
        with self.lock, self.connect() as db:
            row=db.execute("SELECT * FROM missions WHERE id=?",(mission_id,)).fetchone()
        return self.decode(row)
    def list(self, limit=50):
        with self.lock, self.connect() as db:
            rows=db.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?",(min(max(limit,1),100),)).fetchall()
        return [self.decode(row) for row in rows]
    def update(self, mission_id, **fields):
        allowed={"status","approval_id","approval_expires_at","result","error"}
        if not fields or not set(fields).issubset(allowed): raise ValueError("invalid mission update fields")
        fields["updated_at"]=datetime.now(timezone.utc).isoformat()
        assignments=", ".join(key+"=?" for key in fields)
        values=[json.dumps(value) if key=="result" and value is not None else value for key,value in fields.items()]
        with self.lock, self.connect() as db:
            db.execute("UPDATE missions SET "+assignments+" WHERE id=?",(*values,mission_id))
        return self.get(mission_id)
    def claim_approved(self, mission_id, approval_id):
        now=datetime.now(timezone.utc).isoformat()
        with self.lock, self.connect() as db:
            cursor=db.execute("UPDATE missions SET status='running',updated_at=? WHERE id=? AND status='approved' AND approval_id=? AND approval_expires_at>?",
                (now,mission_id,approval_id,now))
            if cursor.rowcount != 1: return None
        return self.get(mission_id)

    @staticmethod
    def _insert_audit_event(db, event_type, mission_id=None, actor="system", payload_hash=None, details=None):
        """Validate and insert one bounded audit event using the caller's transaction."""
        if not isinstance(event_type, str) or not event_type or len(event_type) > 80:
            raise ValueError("event_type must contain 1-80 characters")
        if not isinstance(actor, str) or not actor or len(actor) > 120:
            raise ValueError("actor must contain 1-120 characters")
        if mission_id is not None and (not isinstance(mission_id, str) or len(mission_id) > 80):
            raise ValueError("mission_id must be a string of at most 80 characters")
        if payload_hash is not None and (
            not isinstance(payload_hash, str)
            or len(payload_hash) != 64
            or any(char not in "0123456789abcdef" for char in payload_hash.lower())
        ):
            raise ValueError("payload_hash must be a SHA-256 hex digest")
        if details is None:
            details = {}
        if not isinstance(details, dict):
            raise ValueError("details must be an object")
        encoded = json.dumps(details, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > 8192:
            raise ValueError("audit details exceed 8192 bytes")
        event = {
            "id": str(uuid.uuid4()),
            "mission_id": mission_id,
            "event_type": event_type,
            "actor": actor,
            "payload_hash": payload_hash,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.execute(
            "INSERT INTO audit_events (id,mission_id,event_type,actor,payload_hash,details,created_at) VALUES (?,?,?,?,?,?,?)",
            (event["id"], mission_id, event_type, actor, payload_hash, encoded, event["created_at"]),
        )
        return event

    def record_audit_event(self, event_type, mission_id=None, actor="system", payload_hash=None, details=None):
        """Append a bounded, non-secret audit event."""
        with self.lock, self.connect() as db:
            return self._insert_audit_event(
                db, event_type, mission_id=mission_id, actor=actor,
                payload_hash=payload_hash, details=details,
            )

    def claim_approved_with_audit(self, mission_id, approval_id):
        """Atomically consume an approval and append execution_started evidence."""
        now = datetime.now(timezone.utc).isoformat()
        with self.lock, self.connect() as db:
            cursor = db.execute(
                "UPDATE missions SET status='running',updated_at=? "
                "WHERE id=? AND status='approved' AND approval_id=? AND approval_expires_at>?",
                (now, mission_id, approval_id, now),
            )
            if cursor.rowcount != 1:
                return None
            row = db.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
            mission = self.decode(row)
            self._insert_audit_event(
                db, "execution_started", mission_id=mission_id,
                payload_hash=mission["payload_hash"],
            )
        return mission

    def list_audit_events(self, mission_id=None, limit=100, offset=0):
        """Return a bounded page of newest audit events, optionally scoped to one mission."""
        try:
            bounded_limit = min(max(int(limit), 1), 500)
            bounded_offset = int(offset)
        except (TypeError, ValueError) as exc:
            raise ValueError("limit and offset must be integers") from exc
        if bounded_offset < 0 or bounded_offset > 10000000:
            raise ValueError("offset must be between 0 and 10000000")
        with self.lock, self.connect() as db:
            if mission_id is None:
                rows = db.execute(
                    "SELECT * FROM audit_events ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                    (bounded_limit, bounded_offset),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM audit_events WHERE mission_id=? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                    (mission_id, bounded_limit, bounded_offset),
                ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["details"] = json.loads(event["details"])
            events.append(event)
        return events
