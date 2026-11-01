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
    def _audit(self, event_type, mission, reason=None):
        details = {"reason": reason} if reason else {}
        return self.store.record_audit_event(
            event_type,
            mission_id=mission.get("id") if mission else None,
            payload_hash=mission.get("payload_hash") if mission else None,
            details=details,
        )
    def create(self,provider,prompt,category="model"):
        if provider not in {"nvidia-nim","openclaw","hermes"}: raise ValueError("unsupported provider")
        if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>12000: raise ValueError("prompt must contain 1-12000 characters")
        digest=self.governor.digest(provider,prompt,category)
        mission = self.store.create({"id":str(uuid.uuid4()),"provider":provider,"prompt":prompt,"category":category,"payload_hash":digest})
        self._audit("mission_created", mission)
        return mission
    def approve(self,mission_id):
        mission=self.store.get(mission_id)
        if not mission: return None
        if mission["status"]!="pending_approval":
            self._audit("approval_denied", mission, "mission_not_pending_approval")
            return {"mission":mission,"decision":{"allowed":False,"reason":"mission_not_pending_approval"}}
        decision=self.governor.evaluate(mission["provider"],mission["prompt"],mission["category"])
        if not decision.allowed:
            self._audit("approval_denied", mission, decision.reason)
            return {"mission":mission,"decision":decision.__dict__}
        approval_id=str(uuid.uuid4())
        expires=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
        updated=self.store.update(mission_id,status="approved",approval_id=approval_id,approval_expires_at=expires)
        self._audit("mission_approved", updated)
        return {"mission":updated,"decision":decision.__dict__}
    def execute(self,mission_id,approval_id):
        mission=self.store.get(mission_id)
        if not mission: return None
        if mission["status"]!="approved" or not approval_id or approval_id!=mission["approval_id"]:
            self._audit("execution_denied", mission, "valid_approval_required")
            return {"mission":mission,"decision":{"allowed":False,"reason":"valid_approval_required"}}
        if not mission.get("approval_expires_at") or datetime.fromisoformat(mission["approval_expires_at"])<=datetime.now(timezone.utc):
            self._audit("execution_denied", mission, "approval_expired")
            return {"mission":mission,"decision":{"allowed":False,"reason":"approval_expired"}}
        decision=self.governor.evaluate(mission["provider"],mission["prompt"],mission["category"],mission["payload_hash"])
        if not decision.allowed:
            self._audit("execution_denied", mission, decision.reason)
            return {"mission":mission,"decision":decision.__dict__}
        claimed=self.store.claim_approved(mission_id,approval_id)
        if not claimed:
            current = self.store.get(mission_id)
            self._audit("execution_denied", current, "approval_used_or_expired")
            return {"mission":current,"decision":{"allowed":False,"reason":"approval_used_or_expired"}}
        self._audit("execution_started", claimed)
        try:
            result=self.adapters.run(mission["provider"],mission["prompt"])
            completed = self.store.update(mission_id,status="succeeded",result=result)
            self._audit("execution_succeeded", completed)
            return {"mission":completed,"decision":decision.__dict__}
        except Exception as exc:
            failed = self.store.update(mission_id,status="failed",error=type(exc).__name__)
            self._audit("execution_failed", failed, type(exc).__name__)
            return {"mission":failed,"decision":decision.__dict__}
