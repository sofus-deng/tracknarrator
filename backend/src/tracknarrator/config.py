"""Configuration module for Track Narrator."""

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings."""
    
    ai_native: bool = Field(
        default=False,
        description="Whether AI-native features are enabled"
    )
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        ai_native_val = os.getenv("AI_NATIVE", "off").lower()
        ai_native = ai_native_val in ("on", "true", "1", "yes", "enabled")
        return cls(ai_native=ai_native)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_env()