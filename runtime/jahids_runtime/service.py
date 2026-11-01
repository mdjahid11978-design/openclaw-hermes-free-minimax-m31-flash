"""Mission lifecycle orchestration with approval-bound payload hashes."""
import os
import uuid
from .governor import Governor
from .store import MissionStore
from .adapters import AdapterRegistry

class MissionService:
    def __init__(self, store=None, governor=None, adapters=None):
        self.store = store or MissionStore()
        self.governor = governor or Governor(int(os.getenv("JAHIDS_AUTONOMY_LEVEL","0")))
        self.adapters = adapters or AdapterRegistry()
    def create(self, provider, prompt, category="model"):
        if provider not in {"nvidia-nim","openclaw","hermes"}:
            raise ValueError("unsupported provider")
        if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>12000:
            raise ValueError("prompt must contain 1-12000 characters")
        digest = self.governor.digest(provider,prompt,category)
        return self.store.create({"id":str(uuid.uuid4()),"provider":provider,"prompt":prompt,"category":category,"payload_hash":digest})
    def approve(self, mission_id):
        mission = self.store.get(mission_id)
        if not mission: return None
        decision = self.governor.evaluate(mission["provider"],mission["prompt"],mission["category"])
        if not decision.allowed: return {"mission":mission,"decision":decision.__dict__}
        approval_id = str(uuid.uuid4())
        return {"mission":self.store.update(mission_id,status="approved",approval_id=approval_id),"decision":decision.__dict__}
    def execute(self, mission_id, approval_id):
        mission = self.store.get(mission_id)
        if not mission: return None
        if mission["status"]!="approved" or not approval_id or approval_id!=mission["approval_id"]:
            return {"mission":mission,"decision":{"allowed":False,"reason":"valid_approval_required"}}
        decision = self.governor.evaluate(mission["provider"],mission["prompt"],mission["category"],mission["payload_hash"])
        if not decision.allowed: return {"mission":mission,"decision":decision.__dict__}
        self.store.update(mission_id,status="running")
        try:
            result = self.adapters.run(mission["provider"],mission["prompt"])
            return {"mission":self.store.update(mission_id,status="succeeded",result=result),"decision":decision.__dict__}
        except Exception as exc:
            return {"mission":self.store.update(mission_id,status="failed",error=type(exc).__name__),"decision":decision.__dict__}
