"""Coaching tips engine for racing session analysis."""

from typing import List, Dict, Any, Literal
from .schema import SessionBundle
from .events import Event


def coach_tips(bundle: SessionBundle, top_events: List[Event], *, lang: str = "zh-Hant") -> List[Dict[str, Any]]:
    """
    Generate coaching tips from session bundle and top events.
    
    Args:
        bundle: Session bundle containing all data
        top_events: List of top events to analyze
        lang: Language for tips ("zh-Hant" or "en")
        
    Returns:
        List of coaching tips (max 3), each with:
        {
            "tip_id": str,
            "title": str,
            "body": str,
            "severity": float,
            "event_ref": str
        }
    """
    if not top_events:
        return []
    
    # Language templates
    templates = {
        "zh-Hant": {
            "lap_outlier": {
                "title": lambda lap_no: f"第{lap_no}圈配速失衡 - 建議先穩定煞車點",
                "body": "建議關鍵圈節奏、輪胎溫度、入彎煞車點。保持穩定的煞車點有助於提升整體圈速表現。"
            },
            "section_outlier": {
                "title": lambda section_name: f"{section_name} 分段偏慢 - 試著提早回油補油",
                "body": "建議該分段的入彎速度與提早補油。優化入彎節奏和出彎加速可以顯著改善分段時間。"
            },
            "position_change": {
                "title": lambda _: "名次波動 - 調整防守線與出彎加速",
                "body": "建議流暢超車與守線。保持良好的賽道位置和出彎加速有助於穩定名次表現。"
            }
        },
        "en": {
            "lap_outlier": {
                "title": lambda lap_no: f"Lap {lap_no} pace imbalance - focus on braking consistency",
                "body": "Focus on rhythm, tire temperature, and braking points. Stable braking points help improve overall lap times."
            },
            "section_outlier": {
                "title": lambda section_name: f"{section_name} section slow - try earlier throttle application",
                "body": "Focus on corner entry speed and earlier throttle application. Optimizing corner rhythm and exit acceleration can significantly improve sector times."
            },
            "position_change": {
                "title": lambda _: "Position fluctuation - adjust defensive lines and exit acceleration",
                "body": "Focus on smooth overtaking and defensive driving. Maintaining good track position and exit acceleration helps stabilize race performance."
            }
        }
    }
    
    # Get templates for the requested language, fallback to zh-Hant
    lang_templates = templates.get(lang, templates["zh-Hant"])
    
    tips = []
    used_types = set()
    position_change_count = 0
    
    # Process events in order (top_events is already sorted by severity)
    for event in top_events:
        event_type = event["type"]
        
        # Skip if we already have 3 tips
        if len(tips) >= 3:
            break
        
        # Skip duplicate types (except position_change max 1)
        if event_type in used_types:
            continue
            
        # Skip if we already have a position_change tip
        if event_type == "position_change" and position_change_count >= 1:
            continue
        
        # Generate tip
        tip_id = f"{event_type}-{event['lap_no']}"
        severity = event["severity"]
        
        # Get title and body based on event type
        if event_type == "lap_outlier":
            title = lang_templates["lap_outlier"]["title"](event["lap_no"])
            body = lang_templates["lap_outlier"]["body"]
        elif event_type == "section_outlier":
            section_name = event.get("section", "Unknown")
            title = lang_templates["section_outlier"]["title"](section_name)
            body = lang_templates["section_outlier"]["body"]
        elif event_type == "position_change":
            title = lang_templates["position_change"]["title"](event["lap_no"])
            body = lang_templates["position_change"]["body"]
            position_change_count += 1
        else:
            continue  # Skip unknown event types
        
        tip = {
            "tip_id": tip_id,
            "title": title,
            "body": body,
            "severity": severity,
            "event_ref": tip_id  # Use tip_id as event_ref
        }
        
        tips.append(tip)
        used_types.add(event_type)
    
    # Sort tips by severity (descending) and return max 3
    tips.sort(key=lambda x: x["severity"], reverse=True)
    return tips[:3]