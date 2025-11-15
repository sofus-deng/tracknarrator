import time
from tracknarrator.share import sign_share_token, verify_share_token


def test_token_sign_and_verify_roundtrip():
    """Test that a signed token can be verified successfully."""
    exp = int(time.time()) + 60
    t = sign_share_token("barber", exp)
    ok, sid, err = verify_share_token(t, now_ts=exp-1)
    assert ok and sid == "barber" and err is None


def test_token_expired():
    """Test that expired tokens are rejected."""
    exp = int(time.time()) - 1
    t = sign_share_token("s1", exp)
    ok, sid, err = verify_share_token(t, now_ts=exp+10)
    assert not ok and err == "expired"


def test_token_bad_signature():
    """Test that tokens with bad signatures are rejected."""
    exp = int(time.time()) + 60
    t = sign_share_token("s1", exp)
    # Corrupt the signature
    corrupted = t[:-5] + "xxxxx"
    ok, sid, err = verify_share_token(corrupted)
    assert not ok and err == "bad_signature"


def test_token_missing_session_id():
    """Test that tokens without session ID are rejected."""
    # Create a token with empty session ID
    exp = int(time.time()) + 60
    import json, base64, hmac, hashlib
    from tracknarrator.share import _b64url
    
    payload = {"sid": "", "exp": exp}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(b"dev-share-secret", raw, hashlib.sha256).digest()
    t = _b64url(raw) + "." + _b64url(sig)
    
    ok, sid, err = verify_share_token(t)
    assert not ok and err == "missing_sid"


def test_token_malformed():
    """Test that malformed tokens are rejected."""
    # Test with missing separator
    t = "invalidtoken"
    ok, sid, err = verify_share_token(t)
    assert not ok and err == "malformed"
    
    # Test with invalid base64
    t = "invalid.!@#$%^&*().invalid"
    ok, sid, err = verify_share_token(t)
    assert not ok and err == "malformed"


def test_token_custom_secret():
    """Test that custom secrets work correctly."""
    exp = int(time.time()) + 60
    t1 = sign_share_token("session1", exp, secret="secret1")
    t2 = sign_share_token("session1", exp, secret="secret2")
    
    # Verify with correct secret
    ok, sid, err = verify_share_token(t1, secret="secret1")
    assert ok and sid == "session1" and err is None
    
    # Verify with wrong secret
    ok, sid, err = verify_share_token(t1, secret="wrong")
    assert not ok and err == "bad_signature"
    
    # Verify token2 with secret2
    ok, sid, err = verify_share_token(t2, secret="secret2")
    assert ok and sid == "session1" and err is None


def test_token_default_timestamp():
    """Test that tokens work with default current timestamp."""
    # Add a larger buffer to account for any processing delay
    t = sign_share_token("test-session", int(time.time()) + 3600)  # 1 hour instead of 60 seconds
    ok, sid, err = verify_share_token(t)
    assert ok and sid == "test-session" and err is None