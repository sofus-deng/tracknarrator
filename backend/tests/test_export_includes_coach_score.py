import io, zipfile, json
import pathlib
from fastapi.testclient import TestClient
from tracknarrator.main import app

def test_export_contains_coach_score():
    client = TestClient(app)
    
    # Load fixture data
    fixtures_dir = pathlib.Path(__file__).parent.parent.parent / "fixtures"
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        b = json.load(f)
    r = client.post("/dev/seed", json=b); assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or b.get("session_id") or "barber"
    r = client.get(f"/session/{sid}/export?lang=en"); assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(z.namelist())
    assert "coach_score.json" in names
    data = json.loads(z.read("coach_score.json"))
    assert "total_score" in data