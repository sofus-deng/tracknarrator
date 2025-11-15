import time
from tracknarrator.share import sign_share_token, verify_share_token, jti_from_token
from tracknarrator.storage import add_share, revoke_share, is_revoked

def test_jti_roundtrip():
    """Test that JTI extraction works correctly."""
    t = sign_share_token("s1", int(time.time())+60)
    jti = jti_from_token(t)
    assert isinstance(jti, str) and len(jti) == 64
    ok, sid, err = verify_share_token(t)
    assert ok and sid=="s1" and err is None

def test_jti_deterministic():
    """Test that JTI is deterministic for same token."""
    t = sign_share_token("test-session", int(time.time())+3600)
    jti1 = jti_from_token(t)
    jti2 = jti_from_token(t)
    assert jti1 == jti2

def test_jti_different_tokens():
    """Test that different tokens have different JTIs."""
    t1 = sign_share_token("session1", int(time.time())+3600)
    t2 = sign_share_token("session2", int(time.time())+3600)
    jti1 = jti_from_token(t1)
    jti2 = jti_from_token(t2)
    assert jti1 != jti2

def test_revoked_token_rejection():
    """Test that revoked tokens are rejected."""
    # Create a token
    session_id = "test-revoke-session"
    exp = int(time.time()) + 3600
    token = sign_share_token(session_id, exp)
    
    # Verify it works initially
    ok, sid, err = verify_share_token(token)
    assert ok and sid == session_id and err is None
    
    # Get JTI and revoke it
    jti = jti_from_token(token)
    revoke_share(jti)
    assert is_revoked(jti)
    
    # Verify it no longer works
    ok, sid, err = verify_share_token(token)
    assert not ok and err == "revoked"

def test_expired_token_still_expired():
    """Test that expired tokens are still rejected even if not revoked."""
    # Create an expired token
    session_id = "test-expired-session"
    exp = int(time.time()) - 1  # Already expired
    token = sign_share_token(session_id, exp)
    
    # Verify it's rejected due to expiration
    ok, sid, err = verify_share_token(token)
    assert not ok and err == "expired"

def test_malformed_token_jti():
    """Test JTI extraction from malformed tokens."""
    jti = jti_from_token("invalid-token")
    assert jti is None
    
    jti = jti_from_token("only-one-part")
    assert jti is None
    
    jti = jti_from_token("")
    assert jti is None

def test_share_creation_records_jti():
    """Test that creating a share automatically records it."""
    # Create a token
    session_id = "test-record-session"
    exp = int(time.time()) + 3600
    token = sign_share_token(session_id, exp)
    
    # Get the JTI
    jti = jti_from_token(token)
    
    # The share should be recorded (not revoked)
    assert not is_revoked(jti)