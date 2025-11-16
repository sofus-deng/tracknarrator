import hmac
import hashlib
import time
from .config import TN_CSRF_SECRET

# time-bucketed token (5 min) to avoid server state; bind to cookie value if present
def make_csrf(cookie_val: str | None) -> str:
    now = int(time.time() // 300)  # 5-min bucket
    msg = f"{cookie_val or ''}:{now}".encode()
    return hmac.new(TN_CSRF_SECRET.encode(), msg, hashlib.sha256).hexdigest()

def verify_csrf(token: str, cookie_val: str | None) -> bool:
    if not token:
        return False
    now = int(time.time() // 300)
    for bucket in (now, now-1):  # allow 10 minutes window
        msg = f"{cookie_val or ''}:{bucket}".encode()
        want = hmac.new(TN_CSRF_SECRET.encode(), msg, hashlib.sha256).hexdigest()
        if hmac.compare_digest(want, token):
            return True
    return False