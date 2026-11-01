"""Fail-closed policy gate; policy decisions precede adapter execution."""
from dataclasses import dataclass
import hashlib
import json

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    payload_hash: str

class Governor:
    BLOCKED_CATEGORIES = {"deploy", "finance", "credentials", "destructive", "legal", "ownership"}
    def __init__(self, autonomy_level: int = 0):
        if not 0 <= autonomy_level <= 5:
            raise ValueError("autonomy_level must be between 0 and 5")
        self.autonomy_level = autonomy_level
    @staticmethod
    def digest(provider: str, prompt: str, category: str) -> str:
        raw = json.dumps({"provider": provider, "prompt": prompt, "category": category}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
    def evaluate(self, provider: str, prompt: str, category: str, approval_hash: str | None = None) -> Decision:
        digest = self.digest(provider, prompt, category)
        if self.autonomy_level == 0:
            return Decision(False, "observe_only_autonomy_level", digest)
        if category in self.BLOCKED_CATEGORIES:
            return Decision(False, "high_impact_action_blocked", digest)
        if category not in {"model", "read", "analysis"}:
            return Decision(False, "category_not_allowlisted", digest)
        if approval_hash is not None and approval_hash != digest:
            return Decision(False, "approval_payload_mismatch", digest)
        return Decision(True, "policy_allowed", digest)
