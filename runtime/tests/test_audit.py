import sqlite3
import tempfile
import unittest
from unittest.mock import patch
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

    def test_scoped_listing_returns_newest_first_and_paginates(self):
        first = self.store.record_audit_event(
            "first", mission_id="mission-1", payload_hash="a" * 64
        )
        other = self.store.record_audit_event("other", mission_id="mission-2")
        second = self.store.record_audit_event(
            "second", mission_id="mission-1", payload_hash="b" * 64
        )

        page_one = self.store.list_audit_events("mission-1", limit=1, offset=0)
        page_two = self.store.list_audit_events("mission-1", limit=1, offset=1)

        self.assertEqual([event["event_type"] for event in page_one], ["second"])
        self.assertEqual(page_one[0]["payload_hash"], "b" * 64)
        self.assertEqual([event["event_type"] for event in page_two], ["first"])
        self.assertEqual(page_two[0]["payload_hash"], "a" * 64)
        self.assertEqual(
            [event["id"] for event in self.store.list_audit_events("mission-2")],
            [other["id"]],
        )
        self.assertNotEqual(first["id"], second["id"])

    def test_approved_claim_rolls_back_when_start_event_fails(self):
        from jahids_runtime.governor import Governor
        from jahids_runtime.service import MissionService

        service = MissionService(self.store, Governor(1), adapters=object())
        mission = service.create("nvidia-nim", "hello")
        approved = service.approve(mission["id"])["mission"]
        with patch.object(MissionStore, "_insert_audit_event", side_effect=ValueError("audit unavailable")):
            with self.assertRaises(ValueError):
                self.store.claim_approved_with_audit(mission["id"], approved["approval_id"])

        current = self.store.get(mission["id"])
        self.assertEqual(current["status"], "approved")
        event_types = [
            event["event_type"] for event in self.store.list_audit_events(mission["id"])
        ]
        self.assertEqual(sorted(event_types), ["mission_approved", "mission_created"])

    def test_rejects_unbounded_or_invalid_event_data(self):
        with self.assertRaises(ValueError):
            self.store.record_audit_event("")
        with self.assertRaises(ValueError):
            self.store.record_audit_event("event", payload_hash="not-a-digest")
        with self.assertRaises(ValueError):
            self.store.record_audit_event("event", details={"large": "x" * 9000})


if __name__ == "__main__":
    unittest.main()
