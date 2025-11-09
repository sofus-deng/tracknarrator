"""Event detection algorithms for racing session analysis."""

from typing import TypedDict, List, Literal, Dict, Any, Optional
from collections import defaultdict
import math

from .schema import SessionBundle, Lap, Section, Telemetry
from .config import ROBUST_Z_LAP, ROBUST_Z_SECTION, EVENT_TYPE_ORDER, DEFAULT_SECTION_LABELS


def prepare_robust_stats(values: List[float]) -> tuple[float, float]:
    """
    Prepare robust statistics (median and MAD) for a list of values.
    
    Args:
        values: List of values to calculate statistics from
        
    Returns:
        Tuple of (median, mad) where mad is median absolute deviation
    """
    if not values:
        return 0.0, 0.0
    
    # Calculate median
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 0:
        median = (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
    else:
        median = sorted_vals[n//2]
    
    # Calculate MAD (Median Absolute Deviation)
    abs_devs = [abs(v - median) for v in values]
    abs_devs.sort()
    if n % 2 == 0:
        mad = (abs_devs[n//2 - 1] + abs_devs[n//2]) / 2
    else:
        mad = abs_devs[n//2]
    
    return median, mad


def robust_z_from_stats(x: float, median: float, mad: float) -> float:
    """
    Calculate robust z-score from pre-computed statistics.
    
    Args:
        x: Value to calculate z-score for
        median: Pre-computed median
        mad: Pre-computed median absolute deviation
        
    Returns:
        Robust z-score (0 if MAD ≈ 0)
    """
    if mad < 1e-10:  # MAD ≈ 0
        return 0.0
    
    return abs(x - median) / (1.4826 * mad)


class Event(TypedDict):
    """Event structure for detected anomalies."""
    type: Literal["lap_outlier", "section_outlier", "position_change"]
    lap_no: Optional[int]
    section: Optional[str]  # only for section_outlier
    severity: float  # 0..1
    summary: str  # short human summary
    meta: Dict[str, Any]  # raw numbers for debugging


def _robust_z_score(values: List[float], x: float) -> float:
    """
    Calculate robust z-score using median and MAD.
    
    Args:
        values: List of values to calculate statistics from
        x: Value to calculate z-score for
        
    Returns:
        Robust z-score (0 if MAD ≈ 0)
    """
    if not values:
        return 0.0
    
    median, mad = prepare_robust_stats(values)
    return robust_z_from_stats(x, median, mad)


def _detect_lap_outliers(bundle: SessionBundle) -> List[Event]:
    """
    Detect lap time outliers using robust statistics.
    
    Args:
        bundle: Session bundle containing lap data
        
    Returns:
        List of lap outlier events
    """
    events = []
    
    # Group laps by driver
    driver_laps = defaultdict(list)
    for lap in bundle.laps:
        if lap.laptime_ms > 0:  # Only consider valid lap times
            driver_laps[lap.driver].append(lap)
    
    # Process each driver's laps
    for driver, laps in driver_laps.items():
        if len(laps) < 3:  # Need at least 3 laps for meaningful statistics
            continue
            
        # Extract lap times
        lap_times = [lap.laptime_ms for lap in laps]
        
        # Check each lap for outlier status
        for lap in laps:
            robust_z = _robust_z_score(lap_times, lap.laptime_ms)
            
            if robust_z >= ROBUST_Z_LAP:  # Threshold for outlier
                    severity = min(1.0, robust_z / 4.0)  # Cap at 1.0
                    
                    # Calculate median for summary
                    median, _ = prepare_robust_stats(lap_times)
                    
                    events.append({
                        "type": "lap_outlier",
                        "lap_no": lap.lap_no,
                        "section": None,
                        "severity": severity,
                        "summary": f"Lap {lap.lap_no}: {lap.laptime_ms} ms vs median {median:.0f} ms (robust_z={robust_z:.2f})",
                        "meta": {
                            "driver": driver,
                            "laptime_ms": lap.laptime_ms,
                            "median_ms": median,
                            "robust_z": robust_z,
                            "threshold": ROBUST_Z_LAP
                        }
                    })
    
    return events


def _detect_section_outliers(bundle: SessionBundle) -> List[Event]:
    """
    Detect section duration outliers per section name.
    
    Args:
        bundle: Session bundle containing section data
        
    Returns:
        List of section outlier events
    """
    events = []
    
    # Create a mapping of lap_no to driver for O(1) lookup
    lap_driver_map = {lap.lap_no: lap.driver for lap in bundle.laps}
    
    # Group sections by name and driver
    driver_sections = defaultdict(lambda: defaultdict(list))
    for section in bundle.sections:
        if section.name in DEFAULT_SECTION_LABELS:
            duration = section.t_end_ms - section.t_start_ms
            if duration > 0:  # Only consider valid durations
                # Use O(1) lookup instead of O(n) scan
                driver = lap_driver_map.get(section.lap_no)
                
                if driver:
                    driver_sections[driver][section.name].append({
                        "lap_no": section.lap_no,
                        "duration": duration,
                        "section": section
                    })
    
    # Process each driver's sections
    for driver, sections_by_name in driver_sections.items():
        for section_name, section_data_list in sections_by_name.items():
            if len(section_data_list) < 3:  # Need at least 3 sections for meaningful stats
                continue
            
            # Extract durations
            durations = [sd["duration"] for sd in section_data_list]
            # Pre-compute statistics once
            median, mad = prepare_robust_stats(durations)
            
            # Check each section for outlier status
            for section_data in section_data_list:
                robust_z = robust_z_from_stats(section_data["duration"], median, mad)
                
                if robust_z >= ROBUST_Z_SECTION:  # Threshold for section outlier
                    severity = min(1.0, robust_z / 3.5)  # Cap at 1.0
                    
                    events.append({
                        "type": "section_outlier",
                        "lap_no": section_data["lap_no"],
                        "section": section_name,
                        "severity": severity,
                        "summary": f"Lap {section_data['lap_no']} {section_name}: {section_data['duration']} ms vs med {median:.0f} ms (z={robust_z:.2f})",
                        "meta": {
                            "driver": driver,
                            "section_name": section_name,
                            "duration_ms": section_data["duration"],
                            "median_ms": median,
                            "robust_z": robust_z,
                            "threshold": ROBUST_Z_SECTION
                        }
                    })
    
    return events


def _detect_position_changes(bundle: SessionBundle) -> List[Event]:
    """
    Detect position changes per driver across consecutive laps.
    
    Args:
        bundle: Session bundle containing lap data with positions
        
    Returns:
        List of position change events
    """
    events = []
    
    # Group laps by driver
    driver_laps = defaultdict(list)
    for lap in bundle.laps:
        if lap.position is not None:  # Only consider laps with position data
            driver_laps[lap.driver].append(lap)
    
    # Process each driver's laps
    for driver, laps in driver_laps.items():
        if len(laps) < 2:  # Need at least 2 laps for position changes
            continue
        
        # Sort by lap number
        laps_sorted = sorted(laps, key=lambda l: l.lap_no)
        
        # Track position changes with sliding window
        for i in range(1, len(laps_sorted)):
            prev_lap = laps_sorted[i-1]
            curr_lap = laps_sorted[i]
            
            prev_pos = prev_lap.position
            curr_pos = curr_lap.position
            
            # Calculate delta
            delta = curr_pos - prev_pos  # negative = overtaking
            
            if delta == 0:  # No position change
                continue
            
            # Check for position change (|delta| >= 1)
            if abs(delta) >= 1:
                severity = min(1.0, abs(delta) / 5.0)  # Cap at 1.0
                
                # Calculate sliding window sum (up to 3 laps)
                window_start = max(0, i - 2)  # Include current lap and up to 2 previous
                window_laps = laps_sorted[window_start:i+1]
                window_sum = 0
                
                if len(window_laps) >= 2:
                    for j in range(1, len(window_laps)):
                        window_sum += window_laps[j].position - window_laps[j-1].position
                
                events.append({
                    "type": "position_change",
                    "lap_no": curr_lap.lap_no,
                    "section": None,
                    "severity": severity,
                    "summary": f"Position change {delta:+d} on lap {curr_lap.lap_no}",
                    "meta": {
                        "driver": driver,
                        "prev_pos": prev_pos,
                        "curr_pos": curr_pos,
                        "delta": delta,
                        "window_sum_abs": abs(window_sum),
                        "window_size": len(window_laps)
                    }
                })
    
    # Deduplicate events for same (driver, lap_no) keeping higher severity
    events_by_driver_lap = {}
    for event in events:
        key = (event["meta"]["driver"], event["lap_no"])
        if key not in events_by_driver_lap:
            events_by_driver_lap[key] = event
        else:
            existing = events_by_driver_lap[key]
            # Keep event with higher severity, or higher window_sum_abs if equal
            if (event["severity"] > existing["severity"] or
                (abs(event["severity"] - existing["severity"]) < 1e-10 and
                 event["meta"]["window_sum_abs"] > existing["meta"]["window_sum_abs"])):
                events_by_driver_lap[key] = event
    
    return list(events_by_driver_lap.values())


def detect_events(bundle: SessionBundle) -> List[Event]:
    """
    Detect all types of events in a session bundle.
    
    Args:
        bundle: Session bundle containing all data
        
    Returns:
        List of all detected events
    """
    events = []
    
    # Detect different types of events
    events.extend(_detect_lap_outliers(bundle))
    events.extend(_detect_section_outliers(bundle))
    events.extend(_detect_position_changes(bundle))
    
    return events


def top5_events(bundle: SessionBundle) -> List[Event]:
    """
    Get top 5 events ranked by severity, recency, and type.
    
    Args:
        bundle: Session bundle containing all data
        
    Returns:
        List of top 5 events
    """
    # Detect all events
    all_events = detect_events(bundle)
    
    if not all_events:
        return []
    
    # Use centralized type order from config
    type_order = {event_type: i for i, event_type in enumerate(EVENT_TYPE_ORDER)}
    
    # Sort events by:
    # 1. Severity (descending)
    # 2. Recency (higher lap_no first, None last)
    # 3. Type order
    def sort_key(event):
        severity = -event["severity"]  # Negative for descending
        lap_no = event["lap_no"] if event["lap_no"] is not None else -1
        recency = -lap_no  # Negative for descending
        type_rank = type_order.get(event["type"], 999)
        return (severity, recency, type_rank)
    
    sorted_events = sorted(all_events, key=sort_key)
    
    # Deduplicate by (lap_no, type) keeping higher severity
    seen = set()
    deduplicated = []
    
    for event in sorted_events:
        key = (event["lap_no"], event["type"])
        if key not in seen:
            seen.add(key)
            deduplicated.append(event)
            if len(deduplicated) >= 5:
                break
    
    return deduplicated


def build_sparklines(bundle: SessionBundle) -> Dict[str, Any]:
    """
    Build sparkline data for visualization.
    
    Args:
        bundle: Session bundle containing all data
        
    Returns:
        Dictionary with sparkline data
    """
    # Extract lap times ordered by lap_no
    laps_by_no = {}
    for lap in bundle.laps:
        if lap.laptime_ms > 0:
            laps_by_no[lap.lap_no] = lap.laptime_ms
    
    laps_ms = [laps_by_no[lap_no] for lap_no in sorted(laps_by_no.keys())]
    
    # Extract section durations by name
    sections_ms = {name: [] for name in DEFAULT_SECTION_LABELS}
    
    # Group sections by lap and name
    sections_by_lap_name = defaultdict(lambda: defaultdict(list))
    for section in bundle.sections:
        if section.name in DEFAULT_SECTION_LABELS:
            duration = section.t_end_ms - section.t_start_ms
            if duration > 0:
                sections_by_lap_name[section.lap_no][section.name] = duration
    
    # Create ordered lists for each section name
    for lap_no in sorted(sections_by_lap_name.keys()):
        for name in DEFAULT_SECTION_LABELS:
            if name in sections_by_lap_name[lap_no]:
                sections_ms[name].append(sections_by_lap_name[lap_no][name])
            else:
                sections_ms[name].append(None)  # Missing data
    
    # Process telemetry for speed series
    speed_points = []
    
    # Filter and sort telemetry
    valid_telemetry = []
    for telemetry in bundle.telemetry:
        if (telemetry.speed_kph is not None and 
            0 <= telemetry.speed_kph <= 400 and
            math.isfinite(telemetry.speed_kph)):
            valid_telemetry.append(telemetry)
    
    # Sort by timestamp
    valid_telemetry.sort(key=lambda t: t.ts_ms)
    
    # Deduplicate time buckets (±1ms)
    time_buckets = {}
    for telemetry in valid_telemetry:
        bucket = telemetry.ts_ms
        # Check for existing telemetry in ±1ms range
        found = False
        for existing_bucket in list(time_buckets.keys()):
            if abs(existing_bucket - bucket) <= 1:
                # Keep the one with more populated fields
                existing = time_buckets[existing_bucket]
                existing_fields = sum(1 for field in ['speed_kph', 'throttle_pct', 'brake_bar', 'gear', 
                                                    'acc_long_g', 'acc_lat_g', 'steer_deg', 'lat_deg', 'lon_deg']
                                     if getattr(existing, field) is not None)
                new_fields = sum(1 for field in ['speed_kph', 'throttle_pct', 'brake_bar', 'gear', 
                                               'acc_long_g', 'acc_lat_g', 'steer_deg', 'lat_deg', 'lon_deg']
                                if getattr(telemetry, field) is not None)
                
                if new_fields > existing_fields:
                    time_buckets[existing_bucket] = telemetry
                found = True
                break
        
        if not found:
            time_buckets[bucket] = telemetry
    
    # Convert to list and sort
    deduplicated = [time_buckets[bucket] for bucket in sorted(time_buckets.keys())]
    
    # Downsample to at most 120 points
    max_points = 120
    if len(deduplicated) > max_points:
        stride = len(deduplicated) // max_points
        if stride < 1:
            stride = 1
        
        # Take every stride-th point, but always include the last point
        downsampled = deduplicated[::stride]
        if downsampled[-1] != deduplicated[-1]:
            downsampled.append(deduplicated[-1])
    else:
        downsampled = deduplicated
    
    # Create speed series
    speed_series = []
    for telemetry in downsampled:
        speed_series.append({
            "ts_ms": telemetry.ts_ms,
            "speed_kph": float(telemetry.speed_kph)
        })
    
    return {
        "laps_ms": laps_ms,
        "sections_ms": sections_ms,
        "speed_series": speed_series
    }