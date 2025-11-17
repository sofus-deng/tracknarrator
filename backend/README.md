# Track Narrator
![Backend CI](https://github.com/TrackNarrator/backend/workflows/backend-ci/badge.svg)

FastAPI backend for racing data import and analysis.

> ℹ️ GitHub Pages 行為：此專案若為 **Private**，Actions 會自動跳過 Pages 部署；將 repo 設為 **Public** 或升級到 Pro/Team 後即可啟用。

## Features

- Import TRD long CSV telemetry data with pivot functionality
- Import MYLAPS sections data with regex-based header resolution
- Import RaceChrono CSV telemetry data with encoding and delimiter auto-detection
- Import weather data with semicolon delimiter support
- In-memory session store with deterministic merge strategy
- RESTful API for data ingestion and retrieval
- Comprehensive test coverage

## Development

### Setup

```bash
# Install dependencies
uv sync

# Run development server
make dev

# Run tests
make test
```

### API Endpoints

- `GET /health` - Health check
- `GET /config` - Get configuration
- `POST /ingest/mylaps-sections` - Import MYLAPS sections CSV
- `POST /ingest/trd-long` - Import TRD long CSV telemetry
- `POST /ingest/racechrono` - Import RaceChrono CSV telemetry
- `POST /ingest/weather` - Import weather CSV
- `GET /session/{session_id}/bundle` - Get complete session bundle

### Ingest Endpoints

#### MYLAPS Sections
```bash
curl -X POST "http://localhost:8000/ingest/mylaps-sections?session_id=my-session" \
  -F "file=@mylaps_sections.csv"
```
- Supports both comma and semicolon delimiters
- Encoding fallback: utf-8 → utf-8-sig → latin1
- Size limit: 2MB

#### TRD Long CSV
```bash
curl -X POST "http://localhost:8000/ingest/trd-long?session_id=my-session" \
  -F "file=@trd_telemetry.csv"
```
- Requires ISO8601Z timestamps
- Accepts meta_time as fallback for invalid timestamps
- Keeps rows with ≥5 mapped numeric fields

#### RaceChrono CSV
```bash
curl -X POST "http://localhost:8000/ingest/racechrono?session_id=my-session" \
  -F "file=@racechrono_telemetry.csv"
```
- Supports both comma and semicolon delimiters
- Encoding fallback: utf-8 → utf-8-sig → latin1
- Size limit: 10MB
- Maps: Time(s)→ts_ms, Speed(km/h)→speed_kph, Longitude/Latitude→coordinates, Throttle(%)→throttle_pct
- Note: Brake pos (%) is ignored (different units than TRD brake_bar)

#### Weather Data
```bash
curl -X POST "http://localhost:8000/ingest/weather?session_id=my-session" \
  -F "file=@weather.csv"
```
- Supports both comma and semicolon delimiters
- Encoding fallback: utf-8 → utf-8-sig → latin1
- Accepts various header variants for weather fields
- Enhanced field support: ts_ms, time_ms, timestamp_ms, ts, timestamp, utc, epoch, epoch_ms
- Field normalization: temp_c/air_temp_c, wind_kph/wind_km_h/wind_mph, humidity_pct/humidity
- Validation ranges: temp_c ∈ [-30, 60]°C, wind_kph ∈ [0, 250] kph, humidity_pct ∈ [0, 100]%
- Row-level validation with detailed reasons for discarded rows

#### Weather Inspection
```bash
curl -X POST "http://localhost:8000/dev/inspect/weather" \
  -F "file=@weather.csv"
```
- Analyzes weather CSV structure and field mappings
- Returns recognized headers, unrecognized names, row counts, and validation reasons
- Sample response:
```json
{
  "status": "ok",
  "inspect": {
    "recognized_headers": ["ts_ms", "temp_c", "wind_kph", "humidity_pct"],
    "unrecognized_names": [],
    "rows_total": 3,
    "rows_accepted": 3,
    "reasons": []
  }
}
```

### Data Merge Strategy

The store uses deterministic merge with source precedence:
- **Telemetry**: trd_long_csv > racechrono_csv > gpx > mylaps_sections_csv > weather_csv
- **Laps/Sections**: mylaps_sections_csv > trd_csv > racechrono_csv > gpx > weather_csv
- **Weather**: weather_csv > trd_long_csv > racechrono_csv > gpx > mylaps_sections_csv

Field-level merge rules:
- Non-None values override None values
- If both non-None and differ beyond tolerance, higher precedence wins
- Telemetry timestamps are bucketed within ±1ms for de-duplication

## Testing

Run the test suite:

```bash
make test
```

Run tests with coverage:

```bash
uv run pytest --cov=src/tracknarrator --cov-report=html
```

## Diagnostics

### TRD CSV Inspector

The API provides a diagnostic endpoint to inspect TRD CSV files and analyze channel mappings:

```bash
curl -X POST "http://localhost:8000/dev/inspect/trd-long" \
  -F "file=@trd_telemetry.csv"
```

The inspector supports both the original TRD format and a simplified format:

#### Supported Formats

1. **Original TRD Format** (with timestamp and telemetry_name columns):
```
expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
```

2. **Simplified Format** (with ts_ms, name, value columns):
```
ts_ms,name,value
0,speed,120.5
0,aps,75.2
0,pbrake_f,15.8
0,gear,3
```

#### Field Name Synonyms

The inspector automatically maps variant field names:

- `vbox_long_min` → `VBOX_Long_Minutes`
- `steering_angle` → `Steering_Angle`

#### Sample Response

```json
{
  "status": "ok",
  "inspect": {
    "recognized_channels": [
      "Steering_Angle",
      "VBOX_Long_Minutes",
      "speed",
      "aps",
      "gear"
    ],
    "missing_expected": [
      "accx_can",
      "accy_can",
      "pbrake_f",
      "VBOX_Lat_Min"
    ],
    "unrecognized_names": [
      "unknown_channel"
    ],
    "rows_total": 18,
    "timestamps": 2,
    "min_fields_per_ts": 9
  }
}
```

#### Response Fields

- `recognized_channels`: Channels that match the expected TRD telemetry names
- `missing_expected`: Expected channels that were not found in the file
- `unrecognized_names`: Up to 20 unrecognized channel names found
- `rows_total`: Total number of rows in the CSV
- `timestamps`: Number of distinct timestamps found
- `min_fields_per_ts`: Minimum number of fields per timestamp (indicates data completeness)

## AI-Native Module

The AI-Native module provides deterministic, multilingual narrative generation for racing sessions.

### Features

- **Multilingual Support**: Supports Traditional Chinese (zh-Hant) and English (en)
- **Deterministic Output**: Uses hash-based template selection for consistent results
- **Template Banks**: Multiple variants per event type for diversity
- **Fallback Mode**: Rule-based generation when AI-native is disabled
- **Event Type Diversity**: Prefers different event types when possible

### Usage

#### Enable/Disable AI-Native

Set the `AI_NATIVE` environment variable:

```bash
# Enable AI-native (default)
export AI_NATIVE=on

# Disable AI-native
export AI_NATIVE=off
```

#### API Endpoints

**Get Narrative**
```bash
# Traditional Chinese (default)
curl "http://localhost:8000/session/{session_id}/narrative?lang=zh-Hant"

# English
curl "http://localhost:8000/session/{session_id}/narrative?lang=en"

# Override AI-native mode
curl "http://localhost:8000/session/{session_id}/narrative?ai_native=off"
```

**Get Summary with Narrative**
```bash
# Include narrative field
curl "http://localhost:8000/session/{session_id}/summary?ai_native=on"

# Legacy summary (no narrative field)
curl "http://localhost:8000/session/{session_id}/summary"
```

**Export with Narrative**
```bash
# Export with narrative (includes narrative.json)
curl "http://localhost:8000/session/{session_id}/export?lang=en" -o session_export.zip
```

### Response Format

#### Narrative Endpoint
```json
{
  "lines": [
    "第2圈節奏異常：配速130000ms，比中位數100500ms偏慢了3.0個標準差。",
    "第2圈IM2a路段異常：通過時間45000ms，比中位數25000ms偏慢了2.8個標準差。",
    "第2圈位置變化：5位→3位，上升了2個位置。"
  ],
  "lang": "zh-Hant",
  "ai_native": true
}
```

#### Summary Extension
When `ai_native=on`, the summary response includes a `narrative` field with the same structure as the narrative endpoint.

### Determinism

The narrative generation is deterministic:
- Same session data always produces the same narrative lines
- Template selection uses hash-based indexing: `index = hash(event_id) % len(templates[type])`
- No randomness is involved in the selection process

### Fallback Behavior

When `AI_NATIVE=off` or `ai_native=false`:
- Uses rule-based templates with session statistics
- Returns safe, predictable content
- No AI-specific phrasing or variations

### Supported Languages

- **zh-Hant**: Traditional Chinese (default)
- **en**: English

Language affects all template text and fallback messages.