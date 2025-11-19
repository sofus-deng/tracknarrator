#!/usr/bin/env bash
set -euo pipefail

# Ensure we're at repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "Ingesting Barber demo bundle from TRD dataset..."

# Check data directory
if [ ! -d "data/barber" ]; then
    echo "Error: data/barber directory not found"
    echo "Please download TRD Barber dataset and unzip it to data/barber/"
    echo "Expected files:"
    echo "  data/barber/telemetry.csv  # TRD long format (timestamp, telemetry_name, telemetry_value)"
    echo "  data/barber/weather.csv     # Weather data (TIME_UTC_SECONDS, AIR_TEMP, etc.)"
    echo "  data/barber/sections.csv    # MYLAPS sections (LAP_TIME, Position, etc.)"
    exit 1
fi

# Run ingestion script
cd backend
python scripts/ingest_barber_demo.py

echo "Barber demo bundle regenerated at fixtures/bundle_sample_barber.json"
echo ""
echo "To test the new bundle:"
echo "  bash demo/run_demo.sh"