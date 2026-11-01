import sqlite3
import tempfile
import unittest
from pathlib import Path

from jahids_runtime.store import MissionStore


class AuditEventTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "audit.sqlite3")
        self.store = MissionStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_events_are_append_only_and_listable(self):
        event = self.store.record_audit_event(
            "mission_created",
            mission_id="mission-1",
            payload_hash="a" * 64,
            details={"provider": "nvidia-nim"},
        )
        listed = self.store.list_audit_events("mission-1")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["id"], event["id"])
        self.assertEqual(listed[0]["details"], {"provider": "nvidia-nim"})
        with self.store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE audit_events SET event_type='changed' WHERE id=?", (event["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM audit_events WHERE id=?", (event["id"],))

    def test_rejects_unbounded_or_invalid_event_data(self):
        with self.assertRaises(ValueError):
            self.store.record_audit_event("")
        with self.assertRaises(ValueError):
            self.store.record_audit_event("event", payload_hash="not-a-digest")
        with self.assertRaises(ValueError):
            self.store.record_audit_event("event", details={"large": "x" * 9000})


if __name__ == "__main__":
    unittest.main()
