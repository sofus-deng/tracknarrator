import io, json, zipfile, pathlib
from fastapi.testclient import TestClient
from tracknarrator.api import app
from tracknarrator.storage import init_db, list_sessions, get_session_bundle
client = TestClient(app)

def test_seeded_session_shows_in_list():
    init_db()
    fixtures_dir = pathlib.Path(__file__).parent.parent.parent / "fixtures"
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle); assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id")
    r = client.get("/sessions"); assert r.status_code == 200
    ids = [s["session_id"] for s in r.json()["sessions"]]
    assert sid in ids

def test_delete_session_removes_data():
    init_db()
    fixtures_dir = pathlib.Path(__file__).parent.parent.parent / "fixtures"
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle); assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id")
    r = client.delete(f"/session/{sid}"); assert r.status_code in (200,204)
    r = client.get(f"/session/{sid}/summary"); assert r.status_code in (404,410)

def test_upload_rejects_unknown_type():
    data = {"file": ("notes.txt", b"hello", "text/plain")}
    r = client.post("/upload", files=data); assert r.status_code == 400

# If RaceChrono/TRD sample CSV fixtures exist, add a minimal happy path:
def test_upload_accepts_csv_if_fixture_exists():
    # Optional: try to load a known csv fixture; if not present, skip
    import os
    fixtures_dir = pathlib.Path(__file__).parent.parent.parent / "fixtures"
    rc_csv = fixtures_dir / "racechrono_sample.csv"
    if not rc_csv.exists():
        return
    with open(rc_csv, "rb") as f:
        data = {"file": ("racechrono_sample.csv", f.read(), "text/csv")}
    r = client.post("/upload", files=data); assert r.status_code in (201, 200)

def test_uploaded_session_appears_in_sessions_list():
    """Test that sessions uploaded via /upload appear in the sessions list."""
    init_db()
    
    # Create a minimal GPX file for upload
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="tn-test">
  <trk><trkseg>
    <trkpt lat="25.0000" lon="121.0000"><time>2024-01-01T00:00:00Z</time></trkpt>
    <trkpt lat="25.0010" lon="121.0010"><time>2024-01-01T00:00:10Z</time></trkpt>
  </trkseg></trk>
</gpx>"""
    
    # Upload the file
    files = {"file": ("test.gpx", gpx_content, "application/gpx+xml")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200
    upload_data = r.json()
    assert "session_id" in upload_data
    session_id = upload_data["session_id"]
    
    # Verify the session appears in the sessions list
    r = client.get("/sessions")
    assert r.status_code == 200
    sessions_data = r.json()
    assert "sessions" in sessions_data
    sessions = sessions_data["sessions"]
    session_ids = [s.get("session_id") for s in sessions]
    assert session_id in session_ids