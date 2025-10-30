# Track Narrator

FastAPI backend for racing data import and analysis.

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