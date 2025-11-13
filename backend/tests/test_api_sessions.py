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