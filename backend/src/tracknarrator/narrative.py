"""AI-native narrative generation for racing sessions."""

from typing import List, Dict, Any
import math
import hashlib

from .schema import SessionBundle
from .events import Event, top5_events
from .config import get_settings


# Template banks for multilingual narrative generation
NARRATIVE_TEMPLATES = {
    "zh-Hant": {
        "lap_outlier": [
            "第{lap_no}圈節奏異常：配速{meta_laptime_ms}ms，比中位數{meta_median_ms:.0f}ms{meta_z_direction}了{meta_robust_z:.1f}個標準差。",
            "第{lap_no}圈表現突出：單圈時間{meta_laptime_ms}ms，與平均值{meta_median_ms:.0f}ms有顯著差異。",
            "第{lap_no}圈出現異常節奏：{meta_laptime_ms}ms的成績，相較於基準線{meta_median_ms:.0f}ms{meta_z_direction}幅度較大。",
            "第{lap_no}圈節奏變化：完成時間{meta_laptime_ms}ms，與正常配速{meta_median_ms:.0f}ms相比{meta_z_direction}明顯。",
            "第{lap_no}圈表現特殊：{meta_laptime_ms}ms的單圈時間，偏離中位數{meta_median_ms:.0f}ms達{meta_robust_z:.1f}個標準差。"
        ],
        "section_outlier": [
            "第{lap_no}圈{section}路段異常：通過時間{meta_duration_ms}ms，比中位數{meta_median_ms:.0f}ms{meta_z_direction}了{meta_robust_z:.1f}個標準差。",
            "第{lap_no}圈{section}路段表現突出：路段時間{meta_duration_ms}ms，與基準{meta_median_ms:.0f}ms有明顯差異。",
            "第{lap_no}圈{section}路段節奏異常：{meta_duration_ms}ms的通過時間，相較於正常值{meta_median_ms:.0f}ms{meta_z_direction}幅度較大。",
            "第{lap_no}圈{section}路段變化：路段時間{meta_duration_ms}ms，與平均表現{meta_median_ms:.0f}ms相比{meta_z_direction}顯著。",
            "第{lap_no}圈{section}路段特殊：{meta_duration_ms}ms的成績，偏離中位數{meta_median_ms:.0f}ms達{meta_robust_z:.1f}個標準差。"
        ],
        "position_change": [
            "第{lap_no}圈位置變化：{meta_prev_pos}位→{meta_curr_pos}位，{meta_delta_direction}了{meta_delta_abs}個位置。",
            "第{lap_no}圈排名調整：從第{meta_prev_pos}位{meta_delta_direction}至第{meta_curr_pos}位，變動{meta_delta_abs}位。",
            "第{lap_no}圈位置變動：{meta_prev_pos}位變為{meta_curr_pos}位，{meta_delta_direction}{meta_delta_abs}個位置。"
        ]
    },
    "en": {
        "lap_outlier": [
            "Lap {lap_no} rhythm anomaly: {meta_laptime_ms}ms vs median {meta_median_ms:.0f}ms, {meta_z_direction} by {meta_robust_z:.1f} standard deviations.",
            "Lap {lap_no} performance stands out: {meta_laptime_ms}ms lap time, significantly different from average {meta_median_ms:.0f}ms.",
            "Lap {lap_no} unusual rhythm: {meta_laptime_ms}ms completion time, {meta_z_direction} notably compared to baseline {meta_median_ms:.0f}ms.",
            "Lap {lap_no} pace variation: {meta_laptime_ms}ms time, {meta_z_direction} significantly from normal pace {meta_median_ms:.0f}ms.",
            "Lap {lap_no} exceptional performance: {meta_laptime_ms}ms lap time, deviating {meta_robust_z:.1f} standard deviations from median {meta_median_ms:.0f}ms."
        ],
        "section_outlier": [
            "Lap {lap_no} {section} section anomaly: {meta_duration_ms}ms vs median {meta_median_ms:.0f}ms, {meta_z_direction} by {meta_robust_z:.1f} standard deviations.",
            "Lap {lap_no} {section} section performance stands out: {meta_duration_ms}ms section time, significantly different from baseline {meta_median_ms:.0f}ms.",
            "Lap {lap_no} {section} section unusual rhythm: {meta_duration_ms}ms completion time, {meta_z_direction} notably compared to normal {meta_median_ms:.0f}ms.",
            "Lap {lap_no} {section} section variation: {meta_duration_ms}ms time, {meta_z_direction} significantly from average {meta_median_ms:.0f}ms.",
            "Lap {lap_no} {section} section exceptional: {meta_duration_ms}ms performance, deviating {meta_robust_z:.1f} standard deviations from median {meta_median_ms:.0f}ms."
        ],
        "position_change": [
            "Lap {lap_no} position change: {meta_prev_pos}→{meta_curr_pos}, {meta_delta_direction} by {meta_delta_abs} positions.",
            "Lap {lap_no} ranking adjustment: from {meta_prev_pos}th {meta_delta_direction} to {meta_curr_pos}th, changed {meta_delta_abs} positions.",
            "Lap {lap_no} position variation: {meta_prev_pos}th to {meta_curr_pos}th, {meta_delta_direction} {meta_delta_abs} positions."
        ]
    }
}

# Fallback templates for rule-based mode
FALLBACK_TEMPLATES = {
    "zh-Hant": [
        "賽道分析完成，共完成{n_laps}圈。",
        "最佳單圈時間：{best_ms}ms，中位數：{median_ms:.0f}ms。",
        "配速穩定性：P90-P10差距為{spread_ms}ms。"
    ],
    "en": [
        "Track analysis completed with {n_laps} laps.",
        "Best lap time: {best_ms}ms, median: {median_ms:.0f}ms.",
        "Pace consistency: P90-P10 spread is {spread_ms}ms."
    ]
}


def _get_deterministic_template(event_id: str, event_type: str, lang: str) -> str:
    """
    Select template deterministically using hash-based indexing.
    
    Args:
        event_id: Unique identifier for the event (e.g., "lap_3_section_IM1a")
        event_type: Type of event ("lap_outlier", "section_outlier", "position_change")
        lang: Language code ("zh-Hant" or "en")
        
    Returns:
        Selected template string
    """
    templates = NARRATIVE_TEMPLATES[lang][event_type]
    # Use hash to ensure deterministic selection
    hash_value = int(hashlib.md5(event_id.encode()).hexdigest(), 16)
    index = hash_value % len(templates)
    return templates[index]


def _prepare_template_vars(event: Event, lang: str) -> Dict[str, Any]:
    """
    Prepare variables for template formatting.
    
    Args:
        event: Event object
        lang: Language code
        
    Returns:
        Dictionary of template variables
    """
    vars_dict = {
        "lap_no": event["lap_no"],
        "section": event.get("section", ""),
        "type": event["type"]
    }
    
    # Add meta fields with proper formatting
    meta = event.get("meta", {})
    for key, value in meta.items():
        vars_dict[f"meta_{key}"] = value
    
    # Add derived fields for better narrative
    if "robust_z" in meta:
        if lang == "zh-Hant":
            vars_dict["meta_z_direction"] = "偏快" if meta["robust_z"] < 0 else "偏慢"
        else:
            vars_dict["meta_z_direction"] = "faster" if meta["robust_z"] < 0 else "slower"
    
    if "delta" in meta:
        vars_dict["meta_delta_abs"] = abs(meta["delta"])
        if lang == "zh-Hant":
            vars_dict["meta_delta_direction"] = "上升" if meta["delta"] > 0 else "下降"
        else:
            vars_dict["meta_delta_direction"] = "gained" if meta["delta"] > 0 else "lost"
    
    return vars_dict


def _format_event_with_template(event: Event, lang: str) -> str:
    """
    Format event using language-specific template.
    
    Args:
        event: Event object
        lang: Language code
        
    Returns:
        Formatted narrative string
    """
    event_type = event["type"]
    
    # Create unique event ID for deterministic selection
    event_id_parts = [f"lap_{event['lap_no']}"]
    if event.get("section"):
        event_id_parts.append(f"section_{event['section']}")
    event_id_parts.append(f"type_{event_type}")
    event_id = "_".join(event_id_parts)
    
    # Get deterministic template
    template = _get_deterministic_template(event_id, event_type, lang)
    
    # Prepare variables and format
    template_vars = _prepare_template_vars(event, lang)
    
    try:
        return template.format(**template_vars)
    except KeyError as e:
        # Fallback if template formatting fails
        return f"Lap {event['lap_no']} {event_type.replace('_', ' ')} event."


def _format_fallback_with_template(stats: Dict[str, Any], lang: str) -> List[str]:
    """
    Format session statistics using fallback templates.
    
    Args:
        stats: Session statistics
        lang: Language code
        
    Returns:
        List of formatted narrative lines
    """
    templates = FALLBACK_TEMPLATES[lang]
    lines = []
    
    for template in templates:
        try:
            line = template.format(**stats)
            lines.append(line)
        except KeyError:
            # Skip templates that can't be formatted
            continue
    
    return lines


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


def build_narrative(bundle: SessionBundle, top_events: List[Event], *, lang: str = "zh-Hant", max_lines: int = 3, ai_native: bool = True) -> List[str]:
    """
    Build AI-native narrative for a racing session (v0.2).
    
    Args:
        bundle: Session bundle containing all data
        top_events: List of events (typically top5_events)
        lang: Language code ("zh-Hant" or "en")
        max_lines: Maximum number of narrative lines to return
        ai_native: Whether to use AI-native templates or rule-based fallback
        
    Returns:
        List of narrative lines
    """
    lines = []
    
    # De-dup event types to prefer diversity when possible
    processed_types = set()
    
    if ai_native:
        # AI-native mode: use deterministic template selection
        for event in top_events:
            event_type = event["type"]
            
            # Prefer diversity but don't skip if we need more lines
            if event_type not in processed_types or len(lines) < max_lines:
                formatted_line = _format_event_with_template(event, lang)
                lines.append(formatted_line)
                processed_types.add(event_type)
                
                if len(lines) >= max_lines:
                    break
    else:
        # Rule-based fallback mode
        stats = _compute_session_stats(bundle)
        if stats:
            fallback_lines = _format_fallback_with_template(stats, lang)
            lines.extend(fallback_lines)
    
    # Pad with safe fallbacks if needed
    if len(lines) < max_lines:
        stats = _compute_session_stats(bundle)
        if not stats:
            # No valid stats, add generic fallbacks
            generic_fallbacks = {
                "zh-Hant": ["賽道分析完成。", "未檢測到顯著異常。", "數據分析結束。"],
                "en": ["Track analysis completed.", "No significant anomalies detected.", "Data analysis complete."]
            }
            for i in range(len(lines), max_lines):
                if i < len(generic_fallbacks[lang]):
                    lines.append(generic_fallbacks[lang][i])
                else:
                    lines.append(generic_fallbacks[lang][-1])
        else:
            # Use stats-based fallbacks
            fallback_lines = _format_fallback_with_template(stats, lang)
            for line in fallback_lines:
                if len(lines) >= max_lines:
                    break
                if line not in lines:  # Avoid duplicates
                    lines.append(line)
    
    return lines[:max_lines]


def build_narrative_legacy(bundle: SessionBundle, events: List[Event], on: bool) -> Dict[str, Any]:
    """
    Legacy build_narrative function for backward compatibility.
    
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