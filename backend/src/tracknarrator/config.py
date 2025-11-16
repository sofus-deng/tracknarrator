"""Configuration module for Track Narrator."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# --- minimal .env loader (stdlib only) ---
def _load_dotenv():
    p = Path(".env")
    if not p.exists():
        return
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip()
            # keep existing OS env if already set
            if k and (k not in os.environ):
                os.environ[k] = v
    except Exception:
        # fail open: env loading is best-effort
        pass

_load_dotenv()


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
TN_UI_KEY = os.getenv("TN_UI_KEY", "")  # when empty => /ui disabled (404)
# UI cookie TTL and 'Secure' flag (set to "1" under HTTPS/proxy)
TN_UI_TTL_S = int(os.getenv("TN_UI_TTL_S", "3600"))
TN_COOKIE_SECURE = os.getenv("TN_COOKIE_SECURE", "0") == "1"
# Step 18: optional Admin API-key allowlist (comma-separated, empty means off)
TN_UI_KEYS = [x.strip() for x in os.getenv("TN_UI_KEYS", "").split(",") if x.strip()]
# Step 19: CSRF & export signing secrets (fallback to share secret if available)
TN_CSRF_SECRET = os.getenv("TN_CSRF_SECRET", os.getenv("TN_SHARE_SECRET", os.getenv("SHARE_SECRET", "tn-csrf")) )
TN_EXPORT_SIGNING = os.getenv("TN_EXPORT_SIGNING", "1") == "1"