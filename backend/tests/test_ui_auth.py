from fastapi.testclient import TestClient
from tracknarrator.main import app
import os, json
from .test_helpers import create_test_client_with_env

def test_ui_login_and_sessions(fixtures_dir, monkeypatch):
    # enable UI
    client = create_test_client_with_env({"TN_UI_KEY": "demo-key"})
    # visiting /ui should redirect to /ui/login or return 401 if not authenticated
    r = client.get("/ui", follow_redirects=False)
    assert r.status_code in (302,307,401)
    # login - get CSRF token first
    page = client.get("/ui/login").text
    import re
    token_match = re.search(r'name="csrf" value="([0-9a-f]{64})"', page)
    csrf_token = token_match.group(1) if token_match else ""
    
    r = client.post("/ui/login", data={"key":"demo-key", "csrf": csrf_token}, follow_redirects=False)
    assert r.status_code in (302,307)
    cookie = r.cookies.get("tn_ui")
    assert cookie
    # Set cookie on client for subsequent requests
    client.cookies.set("tn_ui", cookie)
    # seed one session
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        b = json.load(f)
    assert client.post("/dev/seed", json=b).status_code == 200
    # list sessions
    r = client.get("/ui/sessions")
    assert r.status_code == 200
    assert "<table" in r.text