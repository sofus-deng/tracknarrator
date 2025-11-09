"""Share card generation for racing session summaries."""

from typing import TypedDict, List, Dict, Any, Optional
from .schema import SessionBundle
from .events import top5_events


class ShareCard(TypedDict):
    """Share card structure for event visualization."""
    event_id: str
    type: str
    lap_no: Optional[int]
    title: str
    metric: str
    delta_ms: Optional[int]
    icon: str
    severity: float
    ts_ms: Optional[int]
    meta: Dict[str, Any]


def build_share_cards(bundle: SessionBundle) -> List[ShareCard]:
    """
    Build share cards from session bundle events.
    
    Args:
        bundle: Session bundle containing all data
        
    Returns:
        List of share cards for visualization
    """
    # Get top events from the bundle
    top_events = top5_events(bundle)
    
    cards = []
    for i, event in enumerate(top_events):
        # Generate unique event ID
        event_id = f"{event['type']}-{event['lap_no']}-{i}"
        
        # Determine icon based on event type
        icon_map = {
            "lap_outlier": "⏱️",      # Clock/timer for lap time issues
            "section_outlier": "📍",   # Location pin for section issues
            "position_change": "🏁"     # Checkered flag for position changes
        }
        icon = icon_map.get(event["type"], "📊")
        
        # Generate title and metric based on event type
        if event["type"] == "lap_outlier":
            title = "Slow Lap Detected"
            laptime_ms = event["meta"]["laptime_ms"]
            median_ms = event["meta"]["median_ms"]
            metric = f"Lap time: {laptime_ms/1000:.1f}s vs median {median_ms/1000:.1f}s"
            delta_ms = laptime_ms - median_ms
            ts_ms = None  # Lap events don't have specific timestamps
            
        elif event["type"] == "section_outlier":
            title = "Slow Section"
            section_name = event["meta"]["section_name"]
            duration_ms = event["meta"]["duration_ms"]
            median_ms = event["meta"]["median_ms"]
            metric = f"{section_name}: {duration_ms/1000:.1f}s vs median {median_ms/1000:.1f}s"
            delta_ms = duration_ms - median_ms
            ts_ms = None  # Section events don't have specific timestamps
            
        elif event["type"] == "position_change":
            title = "Position Change"
            delta = event["meta"]["delta"]
            if delta < 0:
                title = "Position Gain"
                metric = f"P{event['meta']['prev_pos']} → P{event['meta']['curr_pos']}"
            else:
                title = "Position Loss"
                metric = f"P{event['meta']['prev_pos']} → P{event['meta']['curr_pos']}"
            delta_ms = None  # Position changes don't have time deltas
            ts_ms = None  # Position events don't have specific timestamps
        else:
            title = "Unknown Event"
            metric = "Event detected"
            delta_ms = None
            ts_ms = None
        
        # Create share card
        card = ShareCard(
            event_id=event_id,
            type=event["type"],
            lap_no=event["lap_no"],
            title=title,
            metric=metric,
            delta_ms=delta_ms,
            icon=icon,
            severity=event["severity"],
            ts_ms=ts_ms,
            meta=event["meta"]
        )
        
        cards.append(card)
    
    return cards