import json
import time
from pathlib import Path

from tracknarrator.schema import SessionBundle
from tracknarrator.api import app
from tracknarrator.share import sign_share_token
from fastapi.testclient import TestClient

# Load the sample bundle
BUNDLE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "bundle_sample_barber.json"

client = TestClient(app)


def test_shared_summary_ok():
    """Test that shared summary works with a valid token."""
    # seed barber bundle
    with open(BUNDLE_PATH, "r") as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle)
    assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id") or "barber"
    
    # Create share token
    token = sign_share_token(sid, int(time.time()) + 3600)
    
    # Get shared summary
    r = client.get(f"/shared/{token}/summary?ai_native=on&lang=zh-Hant")
    assert r.status_code == 200
    data = r.json()
    
    # Check response structure
    assert "events" in data
    assert "cards" in data
    assert "sparklines" in data
    assert "kpis" in data
    assert "narrative" in data
    
    # Check narrative structure
    assert "lines" in data["narrative"]
    assert "lang" in data["narrative"]
    assert "ai_native" in data["narrative"]
    assert data["narrative"]["lang"] == "zh-Hant"


def test_shared_summary_bad_token():
    """Test that bad tokens are rejected."""
    r = client.get("/shared/not-a-token/summary")
    assert r.status_code in (400, 401)


def test_shared_summary_expired_token():
    """Test that expired tokens are rejected."""
    # Create expired token
    token = sign_share_token("test-session", int(time.time()) - 1)
    
    r = client.get(f"/shared/{token}/summary")
    assert r.status_code == 410  # Gone


def test_shared_summary_nonexistent_session():
    """Test that tokens for non-existent sessions are rejected."""
    # Create token for non-existent session
    token = sign_share_token("non-existent-session", int(time.time()) + 3600)
    
    r = client.get(f"/shared/{token}/summary")
    assert r.status_code == 404


def test_shared_summary_without_narrative():
    """Test that shared summary works without narrative."""
    # seed barber bundle
    with open(BUNDLE_PATH, 'r') as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle)
    assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id") or "barber"
    
    # Create share token
    token = sign_share_token(sid, int(time.time()) + 3600)
    
    # Get shared summary without ai_native=on
    r = client.get(f"/shared/{token}/summary")
    assert r.status_code == 200
    data = r.json()
    
    # Check response structure
    assert "events" in data
    assert "cards" in data
    assert "sparklines" in data
    assert "kpis" in data
    assert "narrative" not in data


def test_shared_summary_kpis_structure():
    """Test that KPIs have the expected structure."""
    # seed barber bundle
    with open(BUNDLE_PATH, 'r') as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle)
    assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id") or "barber"
    
    # Create share token
    token = sign_share_token(sid, int(time.time()) + 3600)
    
    # Get shared summary
    r = client.get(f"/shared/{token}/summary")
    assert r.status_code == 200
    data = r.json()
    
    # Check KPIs structure
    kpis = data["kpis"]
    assert "total_laps" in kpis
    assert "best_lap_ms" in kpis
    assert "median_lap_ms" in kpis
    assert "session_duration_ms" in kpis
    
    # Check data types
    assert isinstance(kpis["total_laps"], int)
    assert isinstance(kpis["best_lap_ms"], (int, float))
    assert isinstance(kpis["median_lap_ms"], (int, float))
    assert isinstance(kpis["session_duration_ms"], (int, float))


def test_create_share_token_endpoint():
    """Test the share token creation endpoint."""
    # seed barber bundle
    with open(BUNDLE_PATH, 'r') as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle)
    assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id") or "barber"
    
    # Create share token via API
    r = client.post(f"/share/{sid}")
    assert r.status_code == 200
    data = r.json()
    
    # Check response structure
    assert "token" in data
    assert "expire_at" in data
    assert "url" in data
    
    # Check data types
    assert isinstance(data["token"], str)
    assert isinstance(data["expire_at"], (int, float))
    assert isinstance(data["url"], str)
    
    # Verify token works
    token = data["token"]
    r = client.get(f"/shared/{token}/summary")
    assert r.status_code == 200


def test_create_share_token_custom_ttl():
    """Test the share token creation endpoint with custom TTL."""
    # seed barber bundle
    with open(BUNDLE_PATH, 'r') as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle)
    assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id") or "barber"
    
    # Create share token with custom TTL
    custom_ttl = 7200  # 2 hours
    r = client.post(f"/share/{sid}?ttl_s={custom_ttl}")
    assert r.status_code == 200
    data = r.json()
    
    # Check expiration time
    exp_ts = data["expire_at"]
    now_ts = int(time.time())
    expected_min = now_ts + custom_ttl - 5  # Allow 5 seconds variance
    expected_max = now_ts + custom_ttl + 5
    assert expected_min <= exp_ts <= expected_max


def test_create_share_token_nonexistent_session():
    """Test that creating share token for non-existent session fails."""
    r = client.post("/share/non-existent-session")
    assert r.status_code == 404