"""AI-native narrative generation for racing sessions."""

from typing import List, Dict, Any
import math

from .schema import SessionBundle
from .events import Event, top5_events


def _compute_session_stats(bundle: SessionBundle) -> Dict[str, Any]:
    """
    Compute session-level statistics for narrative fallback.
    
    Args:
        bundle: Session bundle containing lap data
        
    Returns:
        Dictionary with session statistics
    """
    if not bundle.laps:
        return {}
    
    # Extract valid lap times
    lap_times = [lap.laptime_ms for lap in bundle.laps if lap.laptime_ms > 0]
    
    if not lap_times:
        return {}
    
    # Sort lap times
    sorted_times = sorted(lap_times)
    n = len(sorted_times)
    
    # Calculate statistics
    best_ms = sorted_times[0]
    
    # Median
    if n % 2 == 0:
        median_ms = (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
    else:
        median_ms = sorted_times[n//2]
    
    # Percentiles for spread calculation
    p90_idx = int(0.9 * (n - 1))
    p10_idx = int(0.1 * (n - 1))
    p90_ms = sorted_times[p90_idx]
    p10_ms = sorted_times[p10_idx]
    spread_ms = p90_ms - p10_ms
    
    return {
        "best_ms": best_ms,
        "median_ms": median_ms,
        "n_laps": n,
        "spread_ms": spread_ms
    }


def _format_lap_outlier(event: Event, bundle: SessionBundle) -> str:
    """
    Format lap outlier event into narrative line.
    
    Args:
        event: Lap outlier event
        bundle: Session bundle for fallback calculations
        
    Returns:
        Formatted narrative line
    """
    lap_no = event["lap_no"]
    meta = event["meta"]
    
    # Try to use meta fields first
    if "laptime_ms" in meta and "median_ms" in meta and "robust_z" in meta:
        return f"Lap {lap_no} stood out: {meta['laptime_ms']} ms vs median {meta['median_ms']:.0f} ms (z={meta['robust_z']:.2f})."
    
    # Fallback: recompute from bundle if needed
    lap_time = None
    for lap in bundle.laps:
        if lap.lap_no == lap_no and lap.driver == meta.get("driver"):
            lap_time = lap.laptime_ms
            break
    
    if lap_time:
        return f"Lap {lap_no} stood out with {lap_time} ms."
    
    return f"Lap {lap_no} stood out."


def _format_section_outlier(event: Event, bundle: SessionBundle) -> str:
    """
    Format section outlier event into narrative line.
    
    Args:
        event: Section outlier event
        bundle: Session bundle (unused for section outliers)
        
    Returns:
        Formatted narrative line
    """
    lap_no = event["lap_no"]
    section = event["section"]
    meta = event["meta"]
    
    # Try to use meta fields first
    if "duration_ms" in meta and "median_ms" in meta and "robust_z" in meta:
        return f"Section {section} on lap {lap_no} was unusual: {meta['duration_ms']} ms vs med {meta['median_ms']:.0f} ms (z={meta['robust_z']:.2f})."
    
    # Fallback: basic message
    return f"Section {section} on lap {lap_no} was unusual."


def _format_position_change(event: Event, bundle: SessionBundle) -> str:
    """
    Format position change event into narrative line.
    
    Args:
        event: Position change event
        bundle: Session bundle (unused for position changes)
        
    Returns:
        Formatted narrative line
    """
    lap_no = event["lap_no"]
    meta = event["meta"]
    
    # Try to use meta fields first
    if "delta" in meta and "prev_pos" in meta and "curr_pos" in meta:
        return f"Position shift on lap {lap_no}: {meta['delta']:+d} places (from {meta['prev_pos']}→{meta['curr_pos']})."
    
    # Fallback: delta only
    if "delta" in meta:
        return f"Position shift on lap {lap_no}: {meta['delta']:+d}."
    
    return f"Position shift on lap {lap_no}."


def _format_fallback_stats(stats: Dict[str, Any]) -> List[str]:
    """
    Format session statistics as fallback narrative lines.
    
    Args:
        stats: Session statistics dictionary
        
    Returns:
        List of formatted narrative lines
    """
    lines = []
    
    if "best_ms" in stats and "median_ms" in stats and "n_laps" in stats:
        lines.append(f"Best lap: {stats['best_ms']} ms; median: {stats['median_ms']:.0f} ms (n={stats['n_laps']}).")
    
    if "spread_ms" in stats:
        lines.append(f"Pace spread (p90−p10): {stats['spread_ms']} ms.")
    
    return lines


def build_narrative(bundle: SessionBundle, events: List[Event], on: bool) -> Dict[str, Any]:
    """
    Build AI-native narrative for a racing session.
    
    Args:
        bundle: Session bundle containing all data
        events: List of events (typically top5_events)
        on: Whether AI-native features are enabled
        
    Returns:
        Dictionary with enabled flag and narrative lines
    """
    if not on:
        return {"enabled": False, "lines": []}
    
    lines = []
    
    # Process events in order (already ranked by top5_events)
    for event in events:
        if event["type"] == "lap_outlier":
            lines.append(_format_lap_outlier(event, bundle))
        elif event["type"] == "section_outlier":
            lines.append(_format_section_outlier(event, bundle))
        elif event["type"] == "position_change":
            lines.append(_format_position_change(event, bundle))
        
        # Stop at 3 lines
        if len(lines) >= 3:
            break
    
    # If we have fewer than 3 lines, add session statistics
    if len(lines) < 3:
        stats = _compute_session_stats(bundle)
        fallback_lines = _format_fallback_stats(stats)
        
        for line in fallback_lines:
            lines.append(line)
            if len(lines) >= 3:
                break
    
    # Ensure exactly 3 lines if possible
    while len(lines) < 3 and stats:
        # Add generic lines if we still need more
        if len(lines) == 0:
            lines.append("Session completed.")
        elif len(lines) == 1:
            lines.append("No significant anomalies detected.")
        else:
            lines.append("Data analysis complete.")
    
    return {"enabled": True, "lines": lines[:3]}