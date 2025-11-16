from fastapi.testclient import TestClient
from tracknarrator.main import app
import os, io
from .test_helpers import create_test_client_with_env

def test_ui_upload_and_share(monkeypatch):
    client = create_test_client_with_env({"TN_UI_KEY": "demo-key", "TN_UI_KEYS": ""})
    # login - get CSRF token first
    page = client.get("/ui/login").text
    import re
    token_match = re.search(r'name="csrf" value="([0-9a-f]{64})"', page)
    csrf_token = token_match.group(1) if token_match else ""
    
    r = client.post("/ui/login", data={"key":"demo-key", "csrf": csrf_token}, follow_redirects=False)
    cookie = r.cookies.get("tn_ui")
    # Set cookie on client for subsequent requests
    client.cookies.set("tn_ui", cookie)
    # minimal GPX
    gpx = b'<?xml version="1.0"?><gpx><trk><trkseg><trkpt lat="25" lon="121"><time>2024-10-05T01:02:03Z</time></trkpt></trkseg></trk></gpx>'
    # Get CSRF token from UI page
    home = client.get("/ui").text
    import re
    token_match = re.search(r'name="csrf" value="([0-9a-f]{64})"', home)
    csrf_token = token_match.group(1) if token_match else ""
    
    files = {"file": ("mini.gpx", io.BytesIO(gpx), "application/gpx+xml")}
    r = client.post("/ui/upload", data={"csrf": csrf_token}, files=files)
    assert r.status_code == 200
    # create share needs a session id; sessions table should exist now
    r = client.get("/sessions")
    assert r.status_code == 200
    data = r.json()
    sessions = data.get("sessions", [])
    if sessions:
        sid = sessions[0]["session_id"]
        # Get CSRF token from UI page first
        home = client.get("/ui").text
        token_match = re.search(r'name="csrf" value="([0-9a-f]{64})"', home)
        csrf_token = token_match.group(1) if token_match else ""
        
        r = client.post(f"/ui/share/{sid}?csrf={csrf_token}")
        assert r.status_code == 200
        assert "Viewer" in r.text