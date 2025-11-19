# Plan: Ingest Barber Demo Bundle from Official TRD Dataset

## Overview
This plan describes how to extend TrackNarrator to regenerate the Barber demo bundle from the official TRD Barber dataset zip, while keeping all existing tests and CI acceptance scripts passing. The public repo will only contain the derived demo bundle and code, not the original TRD dataset.

## Current State Analysis

### Existing Importers
- `TRDLongCSVImporter`: Handles TRD long-format CSV telemetry data with pivot functionality
- `WeatherCSVImporter`: Handles weather data CSV files with enhanced field support
- `MYLAPSSectionsCSVImporter`: Handles MYLAPS sections CSV files

### Current Demo Bundle
- Located at `fixtures/bundle_sample_barber.json`
- Contains session, laps, sections, telemetry, and weather data
- Uses track_id "barber-motorsports-park"
- Section names: IM1a, IM1, IM2a, IM2, IM3a, FL
- Source marked as "mylaps_csv" for laps/sections and mixed sources for other data

### Demo Flow
- `demo/run_demo.sh`: Seeds the demo bundle and generates exports
- `scripts/sync_demo_to_docs.sh`: Syncs demo artifacts to docs for Pages
- Multiple acceptance scripts validate the demo flow

## Schema Compliance (SPEC-schema-v0.1.2.md)

### Key Requirements from SPEC
- **Units**: speed_kph (km/h), brake_bar (bar), steer_deg (degrees), acc_long_g/acc_lat_g (g)
- **Timestamps**: UTC ISO8601 for *_ts, milliseconds for *_ms
- **Coordinates**: lat_deg/lon_deg in WGS-84 decimal degrees
- **TRD Field Mappings**:
  - `speed` → Telemetry.speed_kph
  - `aps` → Telemetry.throttle_pct
  - `pbrake_f` → Telemetry.brake_bar (fallback to `pbrake_r`)
  - `accx_can`/`accy_can` → Telemetry.acc_long_g/acc_lat_g
  - `Steering_Angle` → Telemetry.steer_deg
  - `VBOX_Lat_Min`/`VBOX_Long_Minutes` → Telemetry.lat_deg/lon_deg
- **Section Names**: IM1a, IM1, IM2a, IM2, IM3a, FL (official IM names)
- **Weather**: wind_speed in m/s, rain_flag 0/1

## Implementation Plan

### 1. New Ingestion Logic

#### Location
- Python helper: `backend/scripts/ingest_barber_demo.py`
- Shell wrapper: `scripts/ingest_barber_demo.sh`

#### Data Structure Assumptions
Based on the existing demo bundle and TRD importers, we assume the official TRD Barber dataset contains:
- TRD long CSV telemetry file (for vehicle sensor data)
- Weather CSV file (for weather conditions)
- MYLAPS sections CSV file (for lap times and section splits)
- Possibly additional metadata files

#### Dataset Organization
Users will:
1. Download `barber-motorsports-park.zip` from hackathon resources
2. Unzip it under `data/barber/` (already gitignored)
3. Run the ingestion script

Expected structure:
```
data/barber/
├── telemetry.csv          # TRD long format (timestamp, telemetry_name, telemetry_value)
├── weather.csv           # Weather data (TIME_UTC_SECONDS, AIR_TEMP, etc.)
├── sections.csv          # MYLAPS sections (LAP_TIME, Position, etc.)
└── metadata.json        # Optional track info
```

### 2. Script Implementation

#### `backend/scripts/ingest_barber_demo.py`
```python
#!/usr/bin/env python3
"""
Ingest Barber demo bundle from official TRD dataset.

This script reads TRD CSV files from data/barber/ and creates
a unified SessionBundle matching the existing demo bundle structure.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tracknarrator.importers.trd_long_csv import TRDLongCSVImporter
from tracknarrator.importers.weather_csv import WeatherCSVImporter
from tracknarrator.importers.mylaps_sections_csv import MYLAPSSectionsCSVImporter
from tracknarrator.schema import Session, SessionBundle

def main():
    # Define paths
    data_dir = Path("data/barber")
    output_file = Path("fixtures/bundle_sample_barber.json")
    
    # Verify data directory exists
    if not data_dir.exists():
        print(f"Error: Data directory {data_dir} not found")
        print("Please download and unzip the TRD Barber dataset to data/barber/")
        sys.exit(1)
    
    # Initialize bundle with session metadata
    session = Session(
        id="barber-demo-r1",
        source="mylaps_csv",  # Match existing demo
        track="Barber Motorsports Park",
        track_id="barber-motorsports-park",
        track_map_version="pdf:Barber_Circuit_Map",
        schema_version="0.1.2"
    )
    
    bundle = SessionBundle(session=session)
    
    # Import telemetry data
    telemetry_file = data_dir / "telemetry.csv"
    if telemetry_file.exists():
        print(f"Importing telemetry from {telemetry_file}")
        with open(telemetry_file, 'r') as f:
            result = TRDLongCSVImporter.import_file(f, session.id)
            if result.bundle:
                bundle.telemetry = result.bundle.telemetry
                print(f"  Imported {len(bundle.telemetry)} telemetry points")
            else:
                print(f"  Warning: No telemetry data imported")
                print(f"  Warnings: {result.warnings}")
    
    # Import weather data
    weather_file = data_dir / "weather.csv"
    if weather_file.exists():
        print(f"Importing weather from {weather_file}")
        with open(weather_file, 'r') as f:
            result = WeatherCSVImporter.import_file(f, session.id)
            if result.bundle:
                bundle.weather = result.bundle.weather
                print(f"  Imported {len(bundle.weather)} weather points")
            else:
                print(f"  Warning: No weather data imported")
                print(f"  Warnings: {result.warnings}")
    
    # Import sections and laps data
    sections_file = data_dir / "sections.csv"
    if sections_file.exists():
        print(f"Importing sections from {sections_file}")
        with open(sections_file, 'r') as f:
            result = MYLAPSSectionsCSVImporter.import_file(f, session.id)
            if result.bundle:
                bundle.laps = result.bundle.laps
                bundle.sections = result.bundle.sections
                print(f"  Imported {len(bundle.laps)} laps")
                print(f"  Imported {len(bundle.sections)} sections")
            else:
                print(f"  Warning: No sections data imported")
                print(f"  Warnings: {result.warnings}")
    
    # Write output bundle
    print(f"Writing bundle to {output_file}")
    with open(output_file, 'w') as f:
        json.dump(bundle.model_dump(), f, indent=2, default=str)
    
    print("Done!")

if __name__ == "__main__":
    main()
```

#### `scripts/ingest_barber_demo.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

# Ensure we're at repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "Ingesting Barber demo bundle from TRD dataset..."

# Check data directory
if [ ! -d "data/barber" ]; then
    echo "Error: data/barber directory not found"
    echo "Please download the TRD Barber dataset and unzip it to data/barber/"
    echo "Expected files:"
    echo "  data/barber/telemetry.csv  # TRD long format telemetry"
    echo "  data/barber/weather.csv     # Weather data"
    echo "  data/barber/sections.csv    # MYLAPS sections"
    exit 1
fi

# Run ingestion script
cd backend
python scripts/ingest_barber_demo.py

echo "Barber demo bundle regenerated at fixtures/bundle_sample_barber.json"
echo ""
echo "To test the new bundle:"
echo "  bash demo/run_demo.sh"
```

### 3. Testing Strategy

#### Unit Tests
- Add `backend/tests/test_ingest_barber_demo.py` to test the ingestion script
- Test with mock CSV files matching expected TRD format
- Verify output bundle structure matches expected schema

#### Integration Tests
- Update existing acceptance scripts to optionally use regenerated bundle
- Ensure `demo/run_demo.sh` works with regenerated bundle
- Verify `scripts/sync_demo_to_docs.sh` produces expected outputs

### 4. Quality Gates

#### Existing Tests
- Run full test suite: `cd backend && uv run pytest -q`
- Ensure all existing tests still pass

#### Acceptance Scripts
- Run demo validation: `bash scripts/accept_step7.sh`
- Run docs sync: `bash scripts/accept_step14.sh`
- Run full acceptance suite: `bash scripts/accept_all.sh`

### 5. File Organization

#### New Files
- `backend/scripts/ingest_barber_demo.py` - Python ingestion script
- `scripts/ingest_barber_demo.sh` - Shell wrapper
- `backend/tests/test_ingest_barber_demo.py` - Unit tests

#### Modified Files
- `fixtures/bundle_sample_barber.json` - Regenerated from TRD data
- `README.md` - Update with ingestion instructions (optional)

#### Gitignored Files
- `data/` directory (already gitignored)
- Downloaded TRD dataset files

### 6. Documentation Updates

#### Instructions for Users
1. Download `barber-motorsports-park.zip` from hackathon resources
2. Create `data/barber/` directory
3. Unzip dataset into `data/barber/`
4. Run `bash scripts/ingest_barber_demo.sh`
5. Verify with `bash demo/run_demo.sh`

#### File Mapping
- `telemetry.csv` → TRDLongCSVImporter → bundle.telemetry
- `weather.csv` → WeatherCSVImporter → bundle.weather
- `sections.csv` → MYLAPSSectionsCSVImporter → bundle.laps + bundle.sections

### 7. Error Handling

#### Missing Files
- Graceful handling when any CSV file is missing
- Clear error messages directing users to expected file structure
- Continue with available data rather than failing completely

#### Data Validation
- Reuse existing importer validation logic
- Preserve existing warnings and error handling
- Ensure output matches v0.1.2 schema exactly

### 8. Backward Compatibility

#### Existing Demo Flow
- `demo/run_demo.sh` continues to work unchanged
- `fixtures/bundle_sample_barber.json` remains the canonical demo bundle
- All acceptance scripts continue to pass

#### API Compatibility
- No changes to API endpoints
- No changes to existing importer interfaces
- Maintains current SessionBundle schema

## Implementation Steps

1. Create Python ingestion script in `backend/scripts/`
2. Create shell wrapper in `scripts/`
3. Add unit tests for ingestion script
4. Test with sample data
5. Run full quality gate validation
6. Commit with conventional commit style

## Success Criteria

- [ ] Script successfully ingests TRD CSV files into unified bundle
- [ ] Generated bundle matches existing structure and schema
- [ ] All existing tests pass
- [ ] All acceptance scripts pass
- [ ] Demo flow works with regenerated bundle
- [ ] Documentation is clear for users
- [ ] Code follows project conventions