import json, time, hmac, hashlib
from typing import Dict, Any
from .config import TN_UI_KEYS
from .share import SHARE_SECRET

# in-memory token bucket for rate limiting (per remote addr)
_BUCKETS: Dict[str, Dict[str, float]] = {}

def rate_check(key: str, rate_per_s: float = 5.0, burst: float = 20.0) -> bool:
    # token bucket: add tokens = dt*rate, cap by burst, consume 1 token
    now = time.time()
    b = _BUCKETS.setdefault(key, {"tok": burst, "ts": now})
    dt = max(0.0, now - b["ts"])
    b["tok"] = min(burst, b["tok"] + dt * rate_per_s)
    b["ts"] = now
    if b["tok"] >= 1.0:
        b["tok"] -= 1.0
        return True
    return False

def audit_sig(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    secret = (SHARE_SECRET or "audit").encode()
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()

def make_audit(actor: str, action: str, target: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    rec = {"ts": int(time.time()), "actor": actor, "action": action, "target": target, "meta": meta}
    rec["sig"] = audit_sig(rec)
    return rec

def is_allowlisted(api_key: str) -> bool:
    if not TN_UI_KEYS:
        return True
    return api_key in TN_UI_KEYS