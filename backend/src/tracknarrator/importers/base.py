"""Base importer class and helper functions."""

from dataclasses import dataclass
from typing import Optional

from ..schema import SessionBundle
from ..utils_time import clean_str, safe_float, safe_int


@dataclass
class ImportResult:
    """Result of an import operation."""
    
    bundle: Optional[SessionBundle]
    warnings: list[str]
    
    @classmethod
    def success(cls, bundle: SessionBundle, warnings: Optional[list[str]] = None) -> "ImportResult":
        """Create a successful import result."""
        return cls(bundle=bundle, warnings=warnings or [])
    
    @classmethod
    def failure(cls, warnings: list[str]) -> "ImportResult":
        """Create a failed import result."""
        return cls(bundle=None, warnings=warnings)


def coerce_float(value: Optional[str], default: Optional[float] = None) -> Optional[float]:
    """Coerce a string value to float with validation."""
    return safe_float(value, default)


def coerce_int(value: Optional[str], default: Optional[int] = None) -> Optional[int]:
    """Coerce a string value to int with validation."""
    return safe_int(value, default)


def clean_string(value: Optional[str]) -> Optional[str]:
    """Clean and validate a string value."""
    return clean_str(value)