import json
import pathlib
from fastapi.testclient import TestClient
from tracknarrator.main import app

def test_coach_score_contract():
    client = TestClient(app)
    
    # Load fixture data
    fixtures_dir = pathlib.Path(__file__).parent.parent.parent / "fixtures"
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        b = json.load(f)
    r = client.post("/dev/seed", json=b); assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or b.get("session_id") or "barber"
    r = client.get(f"/session/{sid}/coach?lang=zh-Hant"); assert r.status_code == 200
    data = r.json()
    for k in ("version","total_score","badge","dimensions"):
        assert k in data
    assert 0 <= int(data["total_score"]) <= 100
    assert isinstance(data["dimensions"], list) and data["dimensions"]