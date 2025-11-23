#!/usr/bin/env bash
set -euo pipefail

# Ensure we're at repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Check that raw data directory exists
RAW_DIR="$ROOT/data/barber/raw"
if [ ! -d "$RAW_DIR" ]; then
    echo "Error: Raw data directory not found: $RAW_DIR"
    echo ""
    echo "Please unzip the official Barber TRD dataset into this directory."
    echo "Expected files include:"
    echo "  - R1_barber_telemetry_data.csv (or similar telemetry file)"
    echo "  - 26_Weather_Race_1_Anonymized.CSV (or similar weather file)"
    echo "  - 23_AnalysisEnduranceWithSections_Race_1_Anonymized.CSV (or similar sections file)"
    exit 1
fi

echo "[prepare_barber] Using raw data from data/barber/raw"
echo "[prepare_barber] Preparing canonical CSV files..."

# Call the Python script
cd "$ROOT"
if ! uv run python backend/scripts/prepare_barber_from_raw.py; then
    echo ""
    echo "[prepare_barber] Failed to prepare canonical CSV files."
    echo "Check the error message above for details."
    exit 1
fi

echo ""
echo "[prepare_barber] Wrote telemetry.csv, weather.csv, sections.csv to data/barber/"
echo "[prepare_barber] You can now run: ./scripts/ingest_barber_demo.sh"