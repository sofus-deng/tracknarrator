from fastapi.testclient import TestClient
from tracknarrator.main import app
import os, io
from .test_helpers import create_test_client_with_env

def test_ui_upload_and_share(monkeypatch):
    client = create_test_client_with_env({"TN_UI_KEY": "demo-key"})
    # login
    r = client.post("/ui/login", data={"key":"demo-key"}, follow_redirects=False)
    cookie = r.cookies.get("tn_ui")
    # Set cookie on client for subsequent requests
    client.cookies.set("tn_ui", cookie)
    # minimal GPX
    gpx = b'<?xml version="1.0"?><gpx><trk><trkseg><trkpt lat="25" lon="121"><time>2024-10-05T01:02:03Z</time></trkpt></trkseg></trk></gpx>'
    files = {"file": ("mini.gpx", io.BytesIO(gpx), "application/gpx+xml")}
    r = client.post("/ui/upload", files=files)
    assert r.status_code == 200
    # create share needs a session id; sessions table should exist now
    r = client.get("/sessions")
    assert r.status_code == 200
    data = r.json()
    sessions = data.get("sessions", [])
    if sessions:
        sid = sessions[0]["session_id"]
        r = client.post(f"/ui/share/{sid}")
        assert r.status_code == 200
        assert "Viewer" in r.text