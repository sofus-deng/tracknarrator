from typing import List, Dict, Any, Sequence, Optional
import math

def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals:
        return math.nan
    k = (len(sorted_vals)-1) * p
    f = math.floor(k); c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c-k)
    d1 = sorted_vals[c] * (k-f)
    return float(d0 + d1)

def lap_deltas(laps_ms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # laps_ms: [{"lap_no": int, "lap_ms": int}, ...]
    arr = [r.get("lap_ms") for r in laps_ms if r.get("lap_ms") is not None]
    if not arr:
        return []
    # median as baseline
    s = sorted(arr)
    med = _percentile(s, 0.5)
    out = []
    for r in laps_ms:
        lm = r.get("lap_ms")
        if lm is None:
            continue
        delta = lm - med
        out.append({"lap_no": r.get("lap_no"), "lap_ms": lm, "delta_ms_to_median": float(delta)})
    # moving average of delta window 3
    for i in range(len(out)):
        win = out[max(0,i-1):min(len(out), i+2)]
        out[i]["delta_ma3"] = float(sum(x["delta_ms_to_median"] for x in win) / len(win))
    return out

def section_box_stats(sections_ms: List[List[Optional[float]]]) -> List[Dict[str, Any]]:
    # sections_ms is a 2D series: per lap list of per-section ms, shape [laps][sections]
    if not sections_ms:
        return []
    n_sec = max(len(row) for row in sections_ms if row)
    result = []
    for sidx in range(n_sec):
        col = [row[sidx] for row in sections_ms if row and sidx < len(row) and row[sidx] is not None]
        colf = sorted(float(x) for x in col)
        if not colf:
            result.append({"section_no": sidx+1})
            continue
        stats = {
            "section_no": sidx+1,
            "p10": _percentile(colf, 0.10),
            "p25": _percentile(colf, 0.25),
            "p50": _percentile(colf, 0.50),
            "p75": _percentile(colf, 0.75),
            "p90": _percentile(colf, 0.90),
            "best_ms": min(colf),
        }
        result.append(stats)
    return result