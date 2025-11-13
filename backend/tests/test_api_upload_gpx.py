import textwrap
from fastapi.testclient import TestClient
from tracknarrator.api import app
client = TestClient(app)

_MINI_GPX = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="tn"><trk><trkseg>
  <trkpt lat="25.0478" lon="121.5319"><time>2024-10-05T01:02:03Z</time></trkpt>
  <trkpt lat="25.0480" lon="121.5321"><time>2024-10-05T01:02:04Z</time></trkpt>
</trkseg></trk></gpx>""")

def test_upload_gpx_minimal():
    files = {"file": ("demo.gpx", _MINI_GPX.encode("utf-8"), "application/gpx+xml")}
    r = client.post("/upload", files=files)
    assert r.status_code in (200, 201)
    assert "session_id" in r.json()