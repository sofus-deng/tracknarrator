import textwrap
import time
from fastapi.testclient import TestClient
from tracknarrator.api import app
from tracknarrator.storage import init_db
client = TestClient(app)

_MINI_GPX = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="tn"><trk><trkseg>
  <trkpt lat="25.0478" lon="121.5319"><time>2024-10-05T01:02:03Z</time></trkpt>
  <trkpt lat="25.0480" lon="121.5321"><time>2024-10-05T01:02:04Z</time></trkpt>
</trkseg></trk></gpx>""")

# GPX with 3 points 10 seconds apart for round-trip test
_ROUNDTRIP_GPX = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="tn-roundtrip-test">
  <trk>
    <name>Roundtrip Test</name>
    <trkseg>
      <trkpt lat="25.0000" lon="121.0000"><time>2024-01-01T00:00:00Z</time></trkpt>
      <trkpt lat="25.0010" lon="121.0010"><time>2024-01-01T00:00:10Z</time></trkpt>
      <trkpt lat="25.0020" lon="121.0020"><time>2024-01-01T00:00:20Z</time></trkpt>
    </trkseg>
  </trk>
</gpx>""")

def test_upload_gpx_minimal():
    files = {"file": ("demo.gpx", _MINI_GPX.encode("utf-8"), "application/gpx+xml")}
    r = client.post("/upload", files=files)
    assert r.status_code in (200, 201)
    assert "session_id" in r.json()

def test_upload_gpx_roundtrip_summary_and_share():
    """Test that after upload, summary and share endpoints work correctly."""
    # Initialize database
    init_db()
    
    # Upload GPX file
    files = {"file": ("roundtrip.gpx", _ROUNDTRIP_GPX.encode("utf-8"), "application/gpx+xml")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200
    upload_data = r.json()
    assert "session_id" in upload_data
    session_id = upload_data["session_id"]
    
    # Verify session appears in sessions list
    r = client.get("/sessions")
    assert r.status_code == 200
    sessions = r.json().get("sessions", [])
    session_ids = [s.get("session_id") for s in sessions]
    assert session_id in session_ids
    
    # Test /session/{id}/summary endpoint
    # Poll for up to 2 seconds to handle any async processing
    max_attempts = 20
    for attempt in range(max_attempts):
        r = client.get(f"/session/{session_id}/summary")
        if r.status_code == 200:
            break
        if attempt == max_attempts - 1:
            assert r.status_code == 200, f"Summary not ready after {max_attempts} attempts"
        time.sleep(0.1)
    
    summary_data = r.json()
    # Verify required keys are present
    assert "events" in summary_data
    assert "cards" in summary_data
    assert "sparklines" in summary_data
    # narrative is optional
    
    # Test /share/{id} endpoint
    r = client.post(f"/share/{session_id}")
    assert r.status_code == 200
    share_data = r.json()
    assert "token" in share_data
    token = share_data["token"]
    
    # Test /shared/{token}/summary endpoint
    r = client.get(f"/shared/{token}/summary")
    assert r.status_code == 200
    shared_summary = r.json()
    # Verify required keys are present
    assert "events" in shared_summary
    assert "cards" in shared_summary
    assert "sparklines" in shared_summary