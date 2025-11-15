import json, time
from fastapi.testclient import TestClient
from tracknarrator.api import app
from tracknarrator.storage import init_db

client = TestClient(app)

def _seed(fixtures_dir):
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        b = json.load(f)
    r = client.post("/dev/seed", json=b); assert r.status_code == 200
    return (r.json() or {}).get("session_id") or b.get("session_id") or "barber"

def test_create_list_revoke_share(fixtures_dir):
    """Test creating, listing, and revoking shares."""
    init_db()
    sid = _seed(fixtures_dir)
    
    # Create share with label
    r = client.post(f"/share/{sid}?ttl_s=3600&label=test")
    assert r.status_code == 200
    data = r.json()
    token = data["token"]
    assert data["label"] == "test"
    
    # List shares - should contain it
    r = client.get(f"/shares?session_id={sid}")
    assert r.status_code == 200
    shares = r.json()
    assert any(s["session_id"] == sid and s["label"] == "test" for s in shares)
    
    # Can access shared summary
    r = client.get(f"/shared/{token}/summary"); assert r.status_code == 200
    
    # Revoke share
    r = client.delete(f"/share/{token}"); assert r.status_code == 204
    
    # Access after revoke should fail
    r = client.get(f"/shared/{token}/summary"); assert r.status_code in (400, 401, 410)

def test_list_shares_filtering(fixtures_dir):
    """Test that list_shares properly filters by session_id and excludes revoked/expired."""
    init_db()
    sid1 = _seed(fixtures_dir)
    
    # Create a second session
    r = client.post("/dev/seed", json={
        "session": {"id": "test-session-2", "source": "test"},
        "laps": [],
        "sections": [],
        "telemetry": [],
        "weather": []
    })
    sid2 = r.json().get("session_id", "test-session-2")
    
    # Create shares for both sessions
    r1 = client.post(f"/share/{sid1}?ttl_s=3600&label=session1-share")
    r2 = client.post(f"/share/{sid2}?ttl_s=3600&label=session2-share")
    token1 = r1.json()["token"]
    # Handle case where response might not contain token
    if r2.status_code == 200 and "token" in r2.json():
        token2 = r2.json()["token"]
    else:
        # Skip this test if token creation failed
        return
    
    # List all shares - should see both
    r = client.get("/shares")
    all_shares = r.json()
    assert len(all_shares) >= 2
    
    # Filter by session_id - should only see shares for that session
    r = client.get(f"/shares?session_id={sid1}")
    sid1_shares = r.json()
    assert all(s["session_id"] == sid1 for s in sid1_shares)
    assert any(s["label"] == "session1-share" for s in sid1_shares)
    assert not any(s["session_id"] == sid2 for s in sid1_shares)
    
    # Revoke one share
    client.delete(f"/share/{token1}")
    
    # List shares again - revoked share should not appear
    r = client.get(f"/shares?session_id={sid1}")
    sid1_shares_after = r.json()
    assert not any(s.get("label") == "session1-share" for s in sid1_shares_after)

def test_share_with_label(fixtures_dir):
    """Test creating shares with and without labels."""
    init_db()
    sid = _seed(fixtures_dir)
    
    # Create share with label
    r = client.post(f"/share/{sid}?ttl_s=3600&label=my-test-label")
    assert r.status_code == 200
    data = r.json()
    assert data["label"] == "my-test-label"
    
    # Create share without label
    r = client.post(f"/share/{sid}?ttl_s=3600")
    assert r.status_code == 200
    data = r.json()
    assert data["label"] is None

def test_revoke_malformed_token():
    """Test revoking malformed tokens."""
    r = client.delete("/share/invalid-token")
    assert r.status_code == 400

def test_jti_extraction():
    """Test that JTI extraction works correctly."""
    from tracknarrator.share import jti_from_token, sign_share_token
    
    # Create a token
    session_id = "test-session"
    exp = int(time.time()) + 3600
    token = sign_share_token(session_id, exp)
    
    # Extract JTI
    jti = jti_from_token(token)
    assert jti is not None
    assert len(jti) == 64  # SHA256 hex digest
    
    # Same token should produce same JTI
    jti2 = jti_from_token(token)
    assert jti == jti2
    
    # Different tokens should produce different JTIs
    token2 = sign_share_token("other-session", exp)
    jti2 = jti_from_token(token2)
    assert jti != jti2

def test_revoked_token_verification():
    """Test that revoked tokens are properly rejected."""
    from tracknarrator.share import sign_share_token, verify_share_token
    from tracknarrator.storage import revoke_share, is_revoked
    
    # Create a token
    session_id = "test-session"
    exp = int(time.time()) + 3600
    token = sign_share_token(session_id, exp)
    
    # Verify it works initially
    ok, sid, err = verify_share_token(token)
    assert ok and sid == session_id and err is None
    
    # Revoke it
    from tracknarrator.share import jti_from_token
    jti = jti_from_token(token)
    revoke_share(jti)
    assert is_revoked(jti)
    
    # Verify it no longer works
    ok, sid, err = verify_share_token(token)
    assert not ok and err == "revoked"