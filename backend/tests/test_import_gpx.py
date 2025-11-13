import textwrap, json
from tracknarrator.importers.gpx import sniff_gpx, parse_gpx_to_bundle

_MINI_GPX = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="tn">
  <trk><name>demo</name><trkseg>
    <trkpt lat="25.0478" lon="121.5319"><ele>10.2</ele><time>2024-10-05T01:02:03Z</time></trkpt>
    <trkpt lat="25.0480" lon="121.5321"><time>2024-10-05T01:02:04Z</time></trkpt>
  </trkseg></trk>
</gpx>
""")

def test_sniff_gpx_true():
    assert sniff_gpx(_MINI_GPX.encode("utf-8"))

def test_parse_gpx_to_bundle_returns_bundle_like():
    bundle = parse_gpx_to_bundle(_MINI_GPX.encode("utf-8"), session_id="gpx-mini")
    # minimal shape checks (do not over-specify)
    assert isinstance(bundle, dict) or hasattr(bundle, "model_dump")
    data = bundle if isinstance(bundle, dict) else bundle.model_dump()
    # Check for session_id in the session object
    session = data.get("session", {})
    assert session.get("id")