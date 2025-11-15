from typing import Dict, Any, List, Sequence, Optional
import math

def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals: return math.nan
    k = (len(sorted_vals)-1) * p
    f = math.floor(k); c = math.ceil(k)
    if f == c: return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c-k)
    d1 = sorted_vals[c] * (k-f)
    return float(d0 + d1)

def _robust_sigma(vals: Sequence[float]) -> float:
    if not vals: return math.nan
    s = sorted(vals); med = _percentile(s, 0.5)
    mad = _percentile(sorted([abs(v-med) for v in s]), 0.5)
    return 1.4826 * mad  # ≈ robust std

def _clamp01(x: float) -> float:
    return 0.0 if math.isnan(x) else max(0.0, min(1.0, x))

def _to100(x: float) -> int:
    return int(round(100.0 * _clamp01(x)))

def compute_coach_score(sparklines: Dict[str, Any], events: List[Dict[str, Any]], lang: str="zh-Hant") -> Dict[str, Any]:
    """
    Input:
      sparklines: expects keys laps_ms (list of {lap_no, lap_ms}) and sections_ms (2D list)
      events: list of event dicts (type, lap_no, severity, ...)
    Output:
      {
        "version": "v1.5",
        "total_score": 0..100,
        "badge": "gold|silver|bronze|practice",
        "dimensions": [
          {"key":"pace_consistency","score":..,"rationale": "..."},
          {"key":"section_smoothness","score":..,"rationale": "..."},
          {"key":"overtake_readiness","score":..,"rationale": "..."},
          {"key":"trend_stability","score":..,"rationale": "..."}
        ]
      }
    Deterministic, no randomness.
    """
    laps = sparklines.get("laps_ms") or []
    secs = sparklines.get("sections_ms") or []
    # Handle both formats: list of dicts or list of integers
    if laps and isinstance(laps[0], dict):
        lap_vals = [float(r["lap_ms"]) for r in laps if r.get("lap_ms") is not None]
    else:
        lap_vals = [float(l) for l in laps if l is not None]
    if not lap_vals:
        return {"version":"v1.5","total_score":0,"badge":"practice","dimensions":[]}

    s = sorted(lap_vals)
    med = _percentile(s, 0.5)
    rsig = _robust_sigma(lap_vals)

    # 1) Pace Consistency (高分=穩定) — 以 robust sigma/median 比值轉換
    pcs = 1.0 - min(1.0, (rsig / med) * 4.0) if med > 0 and not math.isnan(rsig) else 0.0

    # 2) Section Smoothness (分段一致性) — 各段的變異係數均值倒數
    sec_scores = []
    if secs:
        # Handle both formats: dict of section names or 2D list
        if isinstance(secs, dict):
            # secs is a dict with section names as keys and lists of times as values
            for section_name, times in secs.items():
                if isinstance(times, list) and times:
                    # Filter out None and non-numeric values
                    valid_times = [float(t) for t in times if t is not None and isinstance(t, (int, float))]
                    if len(valid_times) >= 3:
                        m = sum(valid_times)/len(valid_times)
                        sig = _robust_sigma(valid_times)
                        cv = (sig/m) if m>0 and not math.isnan(sig) else float('nan')
                        sec_scores.append(1.0 - min(1.0, max(0.0, cv) * 3.5))
        else:
            # secs is a 2D list (original expected format)
            n_sec = max(len(r) for r in secs if r)
            for i in range(n_sec):
                col = [float(r[i]) for r in secs if r and i < len(r) and r[i] is not None]
                if len(col) >= 3:
                    col_s = sorted(col)
                    m = sum(col)/len(col)
                    sig = _robust_sigma(col)
                    cv = (sig/m) if m>0 and not math.isnan(sig) else float('nan')
                    sec_scores.append(1.0 - min(1.0, max(0.0, cv) * 3.5))
    sss = sum(sec_scores)/len(sec_scores) if sec_scores else 0.0

    # 3) Overtake Readiness (可進攻性) — 以快於中位圈的比例衡量
    deltas = [v - med for v in lap_vals]
    good = sum(1 for d in deltas if d <= -max(20.0, rsig*0.5 if not math.isnan(rsig) else 20.0))
    ors = min(1.0, good / max(1, len(deltas)))  # 快圈比例

    # 4) Trend Stability (節奏趨勢穩定) — delta_ma3 斜率越接近 0 越好
    # 簡化：首末四分位的平均差，越小越穩，映射到[0,1]
    q1 = _percentile(sorted(deltas), 0.25); q3 = _percentile(sorted(deltas), 0.75)
    span = abs(q3 - q1)
    # 以分位跨度當尺度，首10%與末10%均值差越小越穩
    head = s[:max(1,int(0.1*len(s)))]
    tail = s[-max(1,int(0.1*len(s))):]
    if head and tail:
        head_mean = sum([x-med for x in head])/len(head)
        tail_mean = sum([x-med for x in tail])/len(tail)
        drift = abs(tail_mean - head_mean)
        ts = 1.0 - min(1.0, (drift / max(1.0, span if span>0 else rsig if not math.isnan(rsig) else 100.0)) )
    else:
        ts = 0.5

    # 綜合分數
    total = 0.35*pcs + 0.35*sss + 0.20*ors + 0.10*ts
    total_score = _to100(total)

    if total_score >= 85: badge = "gold"
    elif total_score >= 70: badge = "silver"
    elif total_score >= 55: badge = "bronze"
    else: badge = "practice"

    def _r(key: str, zh: str, en: str) -> str:
        return zh if (lang or "zh-Hant").startswith("zh") else en

    dims = [
        {"key":"pace_consistency","score":_to100(pcs),
         "rationale": _r("pace_consistency", "圈速分佈集中，節奏穩定。","Lap times clustered around median; steady rhythm.")},
        {"key":"section_smoothness","score":_to100(sss),
         "rationale": _r("section_smoothness", "分段波動小，動作銜接順。","Low section variability; smooth sequencing.")},
        {"key":"overtake_readiness","score":_to100(ors),
         "rationale": _r("overtake_readiness", "具備一定比例的快圈，具備進攻窗口。","Good share of fast laps; windows to attack.")},
        {"key":"trend_stability","score":_to100(ts),
         "rationale": _r("trend_stability", "節奏漂移有限，狀態承接良好。","Limited drift in pace; stable trend.")}
    ]
    return {"version":"v1.5","total_score": total_score, "badge": badge, "dimensions": dims}