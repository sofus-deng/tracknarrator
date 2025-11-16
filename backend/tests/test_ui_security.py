from fastapi.testclient import TestClient
from .test_helpers import create_test_client_with_env
import json
import re

def _login(client, key="demo-key", uik=None):
    # Get CSRF token first
    page = client.get("/ui/login").text
    import re
    token_match = re.search(r'name="csrf" value="([0-9a-f]{64})"', page)
    csrf_token = token_match.group(1) if token_match else ""
    
    data = {"key": key, "csrf": csrf_token}
    if uik:
        data["uik"] = uik
    r = client.post("/ui/login", data=data, follow_redirects=False)
    return r.cookies.get("tn_ui"), r.cookies.get("tn_uik")

def test_allowlist_and_rate_and_audit(fixtures_dir):
    # Create client with specific environment variables
    client = create_test_client_with_env({
        "TN_UI_KEY": "demo-key",
        "TN_UI_KEYS": "alpha"  # enable allowlist
    })

    # Without allowlist cookie/header, sessions should 401
    ui, uik = _login(client)  # no uik
    assert ui
    r = client.get("/ui/sessions", cookies={"tn_ui": ui})
    assert r.status_code == 401

    # Login with allowlist key, then list sessions OK
    ui, uik = _login(client, uik="alpha")
    assert ui and uik == "alpha"
    r = client.get("/ui/sessions", cookies={"tn_ui": ui, "tn_uik": uik})
    assert r.status_code == 200

    # Seed and create share - ensures audit entries are written
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        b = json.load(f)
    assert client.post("/dev/seed", json=b).status_code == 200
    r = client.get("/sessions")
    sessions = r.json().get("sessions", [])
    assert len(sessions) > 0, "No sessions found after seeding"
    sid = sessions[0]["session_id"]
    # Get CSRF token from UI page first
    home = client.get("/ui", cookies={"tn_ui": ui, "tn_uik": uik}).text
    token_match = re.search(r'name="csrf" value="([0-9a-f]{64})"', home)
    csrf_token = token_match.group(1) if token_match else ""
    
    r = client.post(f"/ui/share/{sid}?csrf={csrf_token}", cookies={"tn_ui": ui, "tn_uik": uik})
    assert r.status_code == 200
    # audit endpoint should contain login/upload/share entries
    logs = client.get("/dev/audits").json()
    assert any(x["action"] in ("login","share_create") for x in logs)

    # Rate limit: shrink bucket then call repeatedly
    # approximate by performing many calls quickly
    hit = 0; fail = 0
    for _ in range(50):
        rr = client.get("/ui/sessions", cookies={"tn_ui": ui, "tn_uik": uik})
        if rr.status_code == 200: hit += 1
        if rr.status_code == 429: fail += 1
        if fail: break
    assert fail >= 1