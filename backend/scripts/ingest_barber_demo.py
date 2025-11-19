#!/usr/bin/env python3
"""
Ingest Barber demo bundle from official TRD dataset.

This script reads TRD CSV files from data/barber/ and creates
a unified SessionBundle matching existing demo bundle structure.
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
    # Get the repository root directory (parent of backend/)
    repo_root = Path(__file__).parent.parent.parent
    data_dir = repo_root / "data" / "barber"
    output_file = repo_root / "fixtures" / "bundle_sample_barber.json"
    
    # Verify data directory exists
    if not data_dir.exists():
        print(f"Error: Data directory {data_dir} not found")
        print("Please download and unzip TRD Barber dataset to data/barber/")
        print("Expected files:")
        print("  data/barber/telemetry.csv  # TRD long format (timestamp, telemetry_name, telemetry_value)")
        print("  data/barber/weather.csv     # Weather data (TIME_UTC_SECONDS, AIR_TEMP, etc.)")
        print("  data/barber/sections.csv    # MYLAPS sections (LAP_TIME, Position, etc.)")
        sys.exit(1)
    
    # Initialize bundle with session metadata (matches existing demo bundle)
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
        try:
            with open(telemetry_file, 'r') as f:
                result = TRDLongCSVImporter.import_file(f, session.id)
                if result.bundle:
                    bundle.telemetry = result.bundle.telemetry
                    print(f"  Imported {len(bundle.telemetry)} telemetry points")
                    # Print any warnings about skipped rows
                    for warning in result.warnings:
                        if "rows skipped" in warning:
                            print(f"  {warning}")
                else:
                    print(f"  Error: No telemetry data imported")
                    for warning in result.warnings:
                        print(f"    {warning}")
                    sys.exit(1)
        except Exception as e:
            print(f"  Error: Failed to import telemetry: {e}")
            sys.exit(1)
    else:
        print(f"  Error: Telemetry file {telemetry_file} not found")
        print(f"  Expected file: data/barber/telemetry.csv (TRD long format)")
        sys.exit(1)
    
    # Import weather data
    weather_file = data_dir / "weather.csv"
    if weather_file.exists():
        print(f"Importing weather from {weather_file}")
        try:
            with open(weather_file, 'r') as f:
                result = WeatherCSVImporter.import_file(f, session.id)
                if result.bundle:
                    bundle.weather = result.bundle.weather
                    print(f"  Imported {len(bundle.weather)} weather points")
                    # Print any warnings about skipped rows
                    for warning in result.warnings:
                        if "rows skipped" in warning:
                            print(f"  {warning}")
                else:
                    print(f"  Error: No weather data imported")
                    for warning in result.warnings:
                        print(f"    {warning}")
                    sys.exit(1)
        except Exception as e:
            print(f"  Error: Failed to import weather: {e}")
            sys.exit(1)
    else:
        print(f"  Error: Weather file {weather_file} not found")
        print(f"  Expected file: data/barber/weather.csv (weather data)")
        sys.exit(1)
    
    # Import sections and laps data
    sections_file = data_dir / "sections.csv"
    if sections_file.exists():
        print(f"Importing sections from {sections_file}")
        try:
            with open(sections_file, 'r') as f:
                result = MYLAPSSectionsCSVImporter.import_file(f, session.id)
                if result.bundle:
                    bundle.laps = result.bundle.laps
                    bundle.sections = result.bundle.sections
                    print(f"  Imported {len(bundle.laps)} laps")
                    print(f"  Imported {len(bundle.sections)} sections")
                else:
                    print(f"  Error: No sections data imported")
                    for warning in result.warnings:
                        print(f"    {warning}")
                    sys.exit(1)
        except Exception as e:
            print(f"  Error: Failed to import sections: {e}")
            sys.exit(1)
    else:
        print(f"  Error: Sections file {sections_file} not found")
        print(f"  Expected file: data/barber/sections.csv (MYLAPS sections)")
        sys.exit(1)
    
    # Write output bundle
    print(f"Writing bundle to {output_file}")
    with open(output_file, 'w') as f:
        json.dump(bundle.model_dump(), f, indent=2, default=str)
    
    print("Done!")

if __name__ == "__main__":
    main()