import tempfile
import unittest
from pathlib import Path
from jahids_runtime.governor import Governor
from jahids_runtime.store import MissionStore
from jahids_runtime.service import MissionService

class FakeAdapters:
    def run(self,provider,prompt): return {"provider":provider,"text":"test response"}

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=MissionStore(str(Path(self.tmp.name)/"missions.sqlite3"))
    def tearDown(self): self.tmp.cleanup()
    def test_observe_only_default(self):
        decision=Governor(0).evaluate("nvidia-nim","hello","model")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason,"observe_only_autonomy_level")
    def test_approved_mission_runs(self):
        service=MissionService(self.store,Governor(1),FakeAdapters())
        mission=service.create("nvidia-nim","hello")
        approved=service.approve(mission["id"])
        self.assertEqual(approved["mission"]["status"],"approved")
        result=service.execute(mission["id"],approved["mission"]["approval_id"])
        self.assertEqual(result["mission"]["status"],"succeeded")
        self.assertEqual(result["mission"]["result"]["text"],"test response")
    def test_wrong_approval_rejected(self):
        service=MissionService(self.store,Governor(1),FakeAdapters())
        mission=service.create("nvidia-nim","hello")
        result=service.execute(mission["id"],"wrong")
        self.assertFalse(result["decision"]["allowed"])
    def test_destructive_action_blocked(self):
        service=MissionService(self.store,Governor(5),FakeAdapters())
        mission=service.create("nvidia-nim","delete production","destructive")
        self.assertFalse(service.approve(mission["id"])["decision"]["allowed"])
    def test_hash_binds_approval_to_payload(self):
        governor=Governor(1)
        approved_hash=governor.digest("nvidia-nim","hello","model")
        result=governor.evaluate("nvidia-nim","changed","model",approved_hash)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason,"approval_payload_mismatch")

if __name__=="__main__": unittest.main()
