# Track Narrator

FastAPI backend for racing data import and analysis.

## Features

- Import TRD long CSV telemetry data with pivot functionality
- Import MYLAPS sections data with regex-based header resolution
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
- `POST /ingest/weather` - Import weather CSV
- `GET /session/{session_id}/bundle` - Get complete session bundle

## Testing

Run the test suite:

```bash
make test
```

Run tests with coverage:

```bash
uv run pytest --cov=src/tracknarrator --cov-report=html