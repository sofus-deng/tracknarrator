import base64
import hmac
import hashlib
import json
import time
from typing import Tuple, Optional

from .config import SHARE_SECRET


def _b64url(b: bytes) -> str:
    """Convert bytes to URL-safe base64 string without padding."""
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def sign_share_token(session_id: str, exp_ts: int, secret: Optional[str] = None) -> str:
    """
    Create a signed share token for a session.
    
    Args:
        session_id: The session ID to share
        exp_ts: Expiration timestamp (Unix epoch seconds)
        secret: Optional secret key for signing (uses default if not provided)
        
    Returns:
        A signed token string
    """
    secret = (secret or SHARE_SECRET).encode()
    payload = {"sid": session_id, "exp": int(exp_ts)}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(secret, raw, hashlib.sha256).digest()
    return _b64url(raw) + "." + _b64url(sig)


def verify_share_token(token: str, now_ts: Optional[int] = None, secret: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verify a share token and extract the session ID.
    
    Args:
        token: The token to verify
        now_ts: Current timestamp (uses time.time() if not provided)
        secret: Optional secret key for verification (uses default if not provided)
        
    Returns:
        Tuple of (is_valid, session_id, error_message)
        If is_valid is True, session_id contains the extracted session ID and error_message is None
        If is_valid is False, session_id is None and error_message contains the error reason
    """
    try:
        enc_payload, enc_sig = token.split(".", 1)
        raw = base64.urlsafe_b64decode(enc_payload + "==")
        payload = json.loads(raw.decode())
        sid, exp = payload.get("sid"), int(payload.get("exp", 0))
        now = int(now_ts or time.time())
        sec = (secret or SHARE_SECRET).encode()
        good_sig = hmac.new(sec, raw, hashlib.sha256).digest()
        
        if not hmac.compare_digest(good_sig, base64.urlsafe_b64decode(enc_sig + "==")):
            return False, None, "bad_signature"
            
        if now > exp:
            return False, None, "expired"
            
        if not sid:
            return False, None, "missing_sid"
            
        return True, sid, None
    except Exception:
        return False, None, "malformed"