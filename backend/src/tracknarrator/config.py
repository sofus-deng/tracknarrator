"""Configuration module for Track Narrator."""

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field


# Share configuration defaults
SHARE_SECRET: str = os.getenv("TN_SHARE_SECRET", "dev-share-secret")
SHARE_TTL_S_DEFAULT: int = int(os.getenv("TN_SHARE_TTL_S", "86400"))  # 1 day


class Settings(BaseModel):
    """Application settings."""
    
    ai_native: bool = Field(
        default=True,
        description="Whether AI-native features are enabled"
    )
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        ai_native_val = os.getenv("AI_NATIVE", "on").lower()
        ai_native = ai_native_val in ("on", "true", "1", "yes", "enabled")
        return cls(ai_native=ai_native)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_env()


# Event Detection Constants
ROBUST_Z_LAP = 2.5
ROBUST_Z_SECTION = 2.8
EVENT_TYPE_ORDER = ["lap_outlier", "section_outlier", "position_change"]
DEFAULT_SECTION_LABELS = ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]

# Database path configuration
TN_DB_PATH = os.getenv("TN_DB_PATH", "tracknarrator.db")
TN_CORS_ORIGINS = os.getenv("TN_CORS_ORIGINS", "")  # e.g. "http://127.0.0.1:4100,https://<user>.github.io" or "*"