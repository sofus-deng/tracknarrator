import base64, hmac, hashlib, json, time
from typing import Optional, Tuple
from .config import TN_UI_KEY

def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def _ub64u(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + pad).encode())

def sign_cookie(user: str="admin", ttl_s: int=3600) -> Optional[str]:
    if not TN_UI_KEY:
        return None
    now = int(time.time())
    payload = {"u": user, "exp": now + int(ttl_s)}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(TN_UI_KEY.encode(), raw, hashlib.sha256).digest()
    return _b64u(raw) + "." + _b64u(sig)

def verify_cookie(cookie: str) -> Tuple[bool, Optional[str]]:
    try:
        if not TN_UI_KEY:
            return False, "ui_disabled"
        enc_raw, enc_sig = cookie.split(".", 1)
        raw = _ub64u(enc_raw)
        want = hmac.new(TN_UI_KEY.encode(), raw, hashlib.sha256).digest()
        got = _ub64u(enc_sig)
        if not hmac.compare_digest(want, got):
            return False, "bad_sig"
        payload = json.loads(raw.decode())
        if int(time.time()) > int(payload.get("exp", 0)):
            return False, "expired"
        return True, payload.get("u", "admin")
    except Exception:
        return False, "malformed"