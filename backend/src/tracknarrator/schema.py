"""Pydantic schema models for Track Narrator v0.1.2."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Session(BaseModel):
    """Session model representing a racing session."""
    
    id: str
    source: Literal["trd_csv", "mylaps_csv", "racechrono_csv", "gpx", "weather_csv", "trd_long_csv"]
    track: Optional[str] = None
    track_id: str
    track_map_version: Optional[str] = None
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    schema_version: str = Field(default="0.1.2", frozen=True)


class Lap(BaseModel):
    """Lap model with timing information."""
    
    session_id: str
    lap_no: int
    driver: str
    laptime_ms: int
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    position: Optional[int] = None


class Section(BaseModel):
    """Section model for track segments."""
    
    session_id: str
    lap_no: int
    name: Literal["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]
    t_start_ms: int
    t_end_ms: int
    delta_ms: Optional[int] = None
    meta: dict = Field(default={"source": "map"})


class Telemetry(BaseModel):
    """Telemetry model with vehicle sensor data."""
    
    session_id: str
    ts_ms: int
    speed_kph: Optional[float] = None
    throttle_pct: Optional[float] = None
    brake_bar: Optional[float] = None
    gear: Optional[int] = None
    acc_long_g: Optional[float] = None
    acc_lat_g: Optional[float] = None
    steer_deg: Optional[float] = None
    lat_deg: Optional[float] = None
    lon_deg: Optional[float] = None


class WeatherPoint(BaseModel):
    """Weather data point model."""
    
    session_id: Optional[str] = None
    ts_ms: int
    air_temp_c: Optional[float] = None
    track_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_dir_deg: Optional[float] = None
    rain_flag: Optional[int] = None


class SessionBundle(BaseModel):
    """Complete session bundle with all related data."""
    
    session: Session
    laps: list[Lap] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    telemetry: list[Telemetry] = Field(default_factory=list)
    weather: list[WeatherPoint] = Field(default_factory=list)