"""Time utility functions for parsing and converting timestamps."""

import re
from datetime import datetime, timezone
from typing import Optional


def parse_laptime_to_ms(laptime: str) -> int:
    """
    Parse laptime string in "m:ss.mmm" or "ss.mmm" format to milliseconds.
    
    Args:
        laptime: Time string in "m:ss.mmm" or "ss.mmm" format
        
    Returns:
        int: Time in milliseconds
        
    Raises:
        ValueError: If the format is invalid
    """
    if not laptime or not isinstance(laptime, str):
        raise ValueError("Laptime must be a non-empty string")
    
    laptime = laptime.strip()
    
    # Pattern for m:ss.mmm format
    mss_pattern = r'^(\d+):([0-5]?\d\.\d{3})$'
    # Pattern for ss.mmm format  
    ss_pattern = r'^([0-5]?\d\.\d{3})$'
    
    if match := re.match(mss_pattern, laptime):
        minutes = int(match.group(1))
        seconds_str = match.group(2)
        seconds = float(seconds_str)
        return int((minutes * 60 + seconds) * 1000)
    elif match := re.match(ss_pattern, laptime):
        seconds = float(match.group(1))
        return int(seconds * 1000)
    else:
        raise ValueError(f"Invalid laptime format: {laptime}. Expected 'm:ss.mmm' or 'ss.mmm'")


def iso_to_ms(iso_str: str) -> int:
    """
    Convert ISO8601Z timestamp string to epoch milliseconds.
    
    Args:
        iso_str: ISO8601Z timestamp string (e.g., "2025-04-04T18:10:23.456Z")
        
    Returns:
        int: Epoch milliseconds
        
    Raises:
        ValueError: If the format is invalid
    """
    if not iso_str or not isinstance(iso_str, str):
        raise ValueError("ISO string must be a non-empty string")
    
    iso_str = iso_str.strip()
    
    try:
        # Parse with timezone awareness (Z = UTC)
        if iso_str.endswith('Z'):
            # Handle Z suffix properly - replace Z with +00:00 for fromisoformat
            dt = datetime.fromisoformat(iso_str[:-1] + '+00:00')
        else:
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError as e:
        raise ValueError(f"Invalid ISO8601Z format: {iso_str}. Error: {e}")


def safe_int(value: Optional[str], default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert a string to int, returning default on failure.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        int or None: Converted value or default
    """
    if value is None or value == "" or value.lower() in ("nan", "inf", "-inf"):
        return default
    
    try:
        return int(float(value))  # Handle "123.0" -> 123
    except (ValueError, TypeError):
        return default


def safe_float(value: Optional[str], default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert a string to float, returning default on failure.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        float or None: Converted value or default
    """
    if value is None or value == "" or value.lower() in ("nan", "inf", "-inf"):
        return default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def clean_str(value: Optional[str]) -> Optional[str]:
    """
    Clean and trim a string value.
    
    Args:
        value: String value to clean
        
    Returns:
        str or None: Cleaned string or None
    """
    if value is None:
        return None
    
    cleaned = value.strip()
    return cleaned if cleaned else None