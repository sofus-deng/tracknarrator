#!/usr/bin/env bash
set -euo pipefail

# Ensure we're at repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "Ingesting Barber demo bundle from TRD dataset..."

# Check data directory
if [ ! -d "$ROOT/data/barber" ]; then
    echo "Error: data/barber directory not found"
    echo "Please download TRD Barber dataset and unzip it to data/barber/"
    echo "Expected files:"
    echo "  $ROOT/data/barber/telemetry.csv  # TRD long format (timestamp, telemetry_name, telemetry_value)"
    echo "  $ROOT/data/barber/weather.csv     # Weather data (TIME_UTC_SECONDS, AIR_TEMP, etc.)"
    echo "  $ROOT/data/barber/sections.csv    # MYLAPS sections (LAP_TIME, Position, etc.)"
    exit 1
fi

# Run ingestion script
cd backend
if ! uv run python scripts/ingest_barber_demo.py; then
    echo ""
    echo "Barber demo ingestion failed – see error above. Check $ROOT/data/barber/*.csv and docs/SPEC-schema-v0.1.2.md."
    exit 1
fi
cd ..

echo "Barber demo bundle regenerated at fixtures/bundle_sample_barber.json"
echo ""
echo "To test the new bundle:"
echo "  bash demo/run_demo.sh"