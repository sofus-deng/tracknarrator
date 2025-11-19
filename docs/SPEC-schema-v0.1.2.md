# TrackNarrator SPEC — schema v0.1.2 (Barber‑aligned, unified)
Updated: 2025-10-28

> This document describes schema v0.1.2, the unified SessionBundle spec for TrackNarrator, aligned to the TRD 2025 Hack the Track Barber dataset.
> This version merges v0.1.1 (Barber sample aligned) with "TRD Telemetry CSV (R1/R2) long table import notes" into a single specification.
> Maintains v0.1/v0.1.1 compatibility while supplementing fields and import strategies.

## Goals
Based on the data provided by TRD 2025 Hackathon, establish v0 unified data structure and import standards:
- Sources: TRD/MYLAPS/RaceChrono/GPX/Weather (CSV/ZIP/PDF map)
- Purposes: Event detection (lap anomalies, position changes), narrative/sharing cards, AI-Native (can be disabled)
- Output: SessionBundle (Session+Lap+Section+Telemetry+Weather)

## Units and Time
- Timestamps `*_ts`: UTC ISO8601 (e.g., `2025-04-04T18:10:23.456Z`); lap/section/telemetry duration in milliseconds (`*_ms`).
- Speed `speed_kph`: km/h; Brake `brake_bar`: bar; Steering angle `steer_deg`: degrees; Acceleration `acc_long_g/acc_lat_g`: g.
- Latitude/longitude `lat_deg/lon_deg`: WGS-84 decimal degrees. TRD fields `VBOX_Lat_Min / VBOX_Long_Minutes` are actually decimal degrees.

## Standard Data Structure (Pydantic shape)
```python
Session:
  id: str
  source: Literal["trd_csv","mylaps_csv","racechrono_csv","gpx"]
  track: Optional[str]
  track_id: str                         # e.g.: barber-motorsports-park
  track_map_version: Optional[str]      # e.g.: pdf:Barber_Circuit_Map
  start_ts: Optional[datetime]
  end_ts: Optional[datetime]
  schema_version: str = "0.1.2"

Lap:
  session_id: str
  lap_no: int
  driver: str
  laptime_ms: int
  start_ts: Optional[datetime]
  end_ts: Optional[datetime]
  position: Optional[int]

Section:
  session_id: str
  lap_no: int
  name: Literal["IM1a","IM1","IM2a","IM2","IM3a","FL"]
  t_start_ms: int
  t_end_ms: int
  delta_ms: Optional[int]
  meta: dict = {"source":"map"}         # "map" | "fallback"

Telemetry:
  session_id: str
  ts_ms: int
  speed_kph: Optional[float]
  throttle_pct: Optional[float]         # aps (%)
  brake_bar: Optional[float]            # pbrake_f; fallback to pbrake_r if missing
  gear: Optional[int]
  acc_long_g: Optional[float]
  acc_lat_g: Optional[float]
  steer_deg: Optional[float]
  lat_deg: Optional[float]
  lon_deg: Optional[float]

WeatherPoint:
  session_id: str
  ts_ms: int
  air_temp_c: Optional[float]
  track_temp_c: Optional[float]
  humidity_pct: Optional[float]
  pressure_hpa: Optional[float]
  wind_speed: Optional[float]           # m/s
  wind_dir_deg: Optional[float]         # 0-360
  rain_flag: Optional[int]              # 0/1

SessionBundle:
  session: Session
  laps: list[Lap]
  sections: list[Section]
  telemetry: list[Telemetry]
  weather: list[WeatherPoint]
```

## Source to Standard Field Mapping (v0)
### TRD (telemetry / lap / time)
- `speed` → Telemetry.speed_kph (~66-190 km/h)
- `gear` → Telemetry.gear (1-5)
- `aps` → Telemetry.throttle_pct (0-100%); `ath` can be used as fallback
- `pbrake_f` → Telemetry.brake_bar (0-~150 bar); fallback to `pbrake_r` if missing
- `accx_can`/`accy_can` → Telemetry.acc_long_g/acc_lat_g (approx -1.6~1.5 / -2.9~2.1)
- `Steering_Angle` → Telemetry.steer_deg (approx -114°~+130°)
- `VBOX_Lat_Min`/`VBOX_Long_Minutes` → Telemetry.lat_deg/lon_deg (decimal degrees)
- `Laptrigger_lapdist_dls` → Lap/section auxiliary indicator (not directly in Telemetry)
- `timestamp` (ECU) and `meta_time` (received): prioritize `timestamp`, fallback to `meta_time` on anomalies

### MYLAPS (official timing CSV)
- `LapTime`/`BestLap` → Lap.laptime_ms (convert to milliseconds)
- `Position` → Lap.position
- `Driver`/`Car` → Lap.driver (`CarNo` can be noted)
- If only lap duration without absolute time, `start_ts/end_ts` can be left empty

### RaceChrono (CSV) / GPX
- `Speed (km/h)` → Telemetry.speed_kph
- `Throttle pos (%)` → Telemetry.throttle_pct
- `Brake pos (%)` (if available) → Can be estimated, v0 can ignore or note as remark
- `Longitude/Latitude` → Telemetry.lon_deg/lat_deg
- GPX trackpoints → Convert to Telemetry (only lat/lon + ts_ms), for map display

### Track maps (PDF/table)
- Use official IM names: `IM1a, IM1, IM2a, IM2, IM3a, FL`.
- With map → `Section.meta.source="map"`; without map → Use Laptrigger or time ratio as **fallback**.

## Import Strategy (including TRD R1/R2 long tables)
- **Encoding**: Support `utf-8` / `utf-8-sig` / `latin1`; automatically remove BOM.
- **Delimiter**: Both `,` and `;` accepted (barber's analysis/sections/weather mostly use semicolon).
- **Time format**: `m:ss.mmm`, `ss.mmm` → milliseconds; `timestamp` ISO8601Z → `ts_ms`.
- **TRD long tables (R1/R2)**: Fields are  
  `expire_at, lap, meta_event, meta_session, meta_source, meta_time, original_vehicle_id, outing, telemetry_name, telemetry_value, timestamp, vehicle_id, vehicle_number`.  
  - Aggregate by `timestamp`; pivot `telemetry_name → telemetry_value` into Telemetry fields (see mapping above).
  - When multiple vehicles mixed, **recommend creating one SessionBundle per vehicle_id**; for `vehicle_number==0`, use `vehicle_id` as unique key.
- **Error tolerance**: Empty string → `None`; non-numeric → ignore/warn; lap number 32768/missing → keep original value and tolerate outliers in event detection phase (v0).

## Event Detection (v0 prerequisite)
- **Lap anomalies**: Moving median + IQR/MAD; `z_like > 2.5` as candidate.
- **Position changes**: Changes ≥2 positions within ≤3 laps as candidate; severity determined by magnitude and speed.
- **Top-5 ranking**: Severity → diversity → recency.

## AI-Native (v0 can be disabled)
- `AI_NATIVE=on|off`; when on, generates 3-sentence narratives and brief Q&A; when off, outputs purely rule-based/statistical.
- README should note AI purpose, disable method, and fallback strategy.

## Submission Notes
- README should note data sources (TRD/MYLAPS/RaceChrono/GPX/Weather/Track maps) and known pitfalls (timestamp/meta_time, car number 000, lap number 32768).
- Available on mobile/tablet/desktop; English documentation; complete Devpost fields.
