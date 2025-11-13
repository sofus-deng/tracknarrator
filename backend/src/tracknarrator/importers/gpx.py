import io, base64, xml.etree.ElementTree as ET
from typing import Iterable, Dict, Any, Optional
from datetime import datetime, timezone

def sniff_gpx(buf: bytes) -> bool:
    head = buf[:200].lstrip()
    # quick checks: xml and <gpx
    return b"<gpx" in head or b"<trkpt" in head

def _iso_to_ms(s: str) -> int:
    # tolerate Z or offset; fall back to naive UTC
    try:
        dt = datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception:
        # some devices emit like 2024-05-02T01:02:03Z
        try:
            dt = datetime.strptime(s.replace("Z",""), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()*1000)

def _iter_points(root: ET.Element) -> Iterable[Dict[str, Any]]:
    ns = {"gpxtpx": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"}
    for trkpt in root.findall(".//trkpt"):
        lat = trkpt.get("lat")
        lon = trkpt.get("lon")
        time_el = trkpt.find("time")
        ele_el = trkpt.find("ele")
        ext = trkpt.find("extensions")
        # optional speed from TrackPointExtension
        sp = None
        if ext is not None:
            sp_el = ext.find(".//gpxtpx:speed", ns)
            if sp_el is not None and sp_el.text:
                try: sp = float(sp_el.text)
                except: sp = None
        if lat is None or lon is None or time_el is None or time_el.text is None:
            continue
        row = {
            "ts_ms": _iso_to_ms(time_el.text.strip()),
            "lat": float(lat),
            "lon": float(lon),
        }
        if ele_el is not None and ele_el.text:
            try: row["ele"] = float(ele_el.text)
            except: pass
        if sp is not None:
            row["speed_mps"] = sp
        yield row

def parse_gpx_to_bundle(buf: bytes, *, session_id: Optional[str]=None, name: Optional[str]=None):
    root = ET.fromstring(buf)
    points = list(_iter_points(root))
    if not points:
        raise ValueError("No <trkpt> with time/lat/lon found")
    
    # Convert GPX points to telemetry format
    telemetry = []
    for point in points:
        # Convert to telemetry schema
        tel_point = {
            "session_id": session_id,
            "ts_ms": point["ts_ms"],
            "lat_deg": point["lat"],
            "lon_deg": point["lon"],
            "speed_kph": point.get("speed_mps", 0) * 3.6 if point.get("speed_mps") else None,  # Convert m/s to km/h
        }
        telemetry.append(tel_point)
    
    # Create session and bundle
    from ..schema import Session, SessionBundle
    
    session = Session(
        id=session_id,
        source="gpx",
        track_id="unknown",  # Will be updated by other importers
    )
    
    bundle = SessionBundle(
        session=session,
        telemetry=telemetry
    )
    
    return bundle