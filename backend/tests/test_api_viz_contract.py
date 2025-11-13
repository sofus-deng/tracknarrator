import json
import pathlib
import pytest
from fastapi.testclient import TestClient
from tracknarrator.api import app
from tracknarrator.storage import init_db
client = TestClient(app)

@pytest.fixture
def fixtures_dir():
    return pathlib.Path(__file__).parent.parent.parent / "fixtures"

def test_viz_has_expected_keys(fixtures_dir):
    with open(fixtures_dir / "bundle_sample_barber.json","r") as f:
        bundle = json.load(f)
    r = client.post("/dev/seed", json=bundle); assert r.status_code == 200
    sid = (r.json() or {}).get("session_id") or bundle.get("session_id") or "barber"
    r = client.get(f"/session/{sid}/viz"); assert r.status_code == 200
    data = r.json()
    assert "lap_delta_series" in data and "section_box" in data
    assert isinstance(data["lap_delta_series"], list)
    if data["lap_delta_series"]:
        item = data["lap_delta_series"][0]
        for k in ("lap_no","lap_ms","delta_ms_to_median","delta_ma3"):
            assert k in item
    assert isinstance(data["section_box"], list)