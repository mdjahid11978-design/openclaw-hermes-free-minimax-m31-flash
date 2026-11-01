"""Mission lifecycle with hash-bound, expiring, single-use approvals."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from .governor import Governor
from .store import MissionStore
from .adapters import AdapterRegistry

class MissionService:
    def __init__(self,store=None,governor=None,adapters=None):
        self.store=store or MissionStore()
        self.governor=governor or Governor(int(os.getenv("JAHIDS_AUTONOMY_LEVEL","0")))
        self.adapters=adapters or AdapterRegistry()
    def create(self,provider,prompt,category="model"):
        if provider not in {"nvidia-nim","openclaw","hermes"}: raise ValueError("unsupported provider")
        if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>12000: raise ValueError("prompt must contain 1-12000 characters")
        digest=self.governor.digest(provider,prompt,category)
        return self.store.create({"id":str(uuid.uuid4()),"provider":provider,"prompt":prompt,"category":category,"payload_hash":digest})
    def approve(self,mission_id):
        mission=self.store.get(mission_id)
        if not mission: return None
        if mission["status"]!="pending_approval":
            return {"mission":mission,"decision":{"allowed":False,"reason":"mission_not_pending_approval"}}
        decision=self.governor.evaluate(mission["provider"],mission["prompt"],mission["category"])
        if not decision.allowed: return {"mission":mission,"decision":decision.__dict__}
        approval_id=str(uuid.uuid4())
        expires=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
        updated=self.store.update(mission_id,status="approved",approval_id=approval_id,approval_expires_at=expires)
        return {"mission":updated,"decision":decision.__dict__}
    def execute(self,mission_id,approval_id):
        mission=self.store.get(mission_id)
        if not mission: return None
        if mission["status"]!="approved" or not approval_id or approval_id!=mission["approval_id"]:
            return {"mission":mission,"decision":{"allowed":False,"reason":"valid_approval_required"}}
        if not mission.get("approval_expires_at") or datetime.fromisoformat(mission["approval_expires_at"])<=datetime.now(timezone.utc):
            return {"mission":mission,"decision":{"allowed":False,"reason":"approval_expired"}}
        decision=self.governor.evaluate(mission["provider"],mission["prompt"],mission["category"],mission["payload_hash"])
        if not decision.allowed: return {"mission":mission,"decision":decision.__dict__}
        claimed=self.store.claim_approved(mission_id,approval_id)
        if not claimed:
            return {"mission":self.store.get(mission_id),"decision":{"allowed":False,"reason":"approval_used_or_expired"}}
        try:
            result=self.adapters.run(mission["provider"],mission["prompt"])
            return {"mission":self.store.update(mission_id,status="succeeded",result=result),"decision":decision.__dict__}
        except Exception as exc:
            return {"mission":self.store.update(mission_id,status="failed",error=type(exc).__name__),"decision":decision.__dict__}
