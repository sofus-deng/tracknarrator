#!/usr/bin/env python3
"""
Prepare canonical Barber CSV files from raw TRD dataset.

This script converts raw TRD dataset files into the three canonical inputs
expected by ingest_barber_demo.sh:
- data/barber/telemetry.csv   (TRD long format: timestamp, telemetry_name, telemetry_value)
- data/barber/weather.csv
- data/barber/sections.csv

Usage:
    uv run python backend/scripts/prepare_barber_from_raw.py
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def find_raw_file(raw_dir: Path, candidates: List[str]) -> Optional[Path]:
    """Find the first existing file from a list of candidate filenames."""
    for candidate in candidates:
        file_path = raw_dir / candidate
        if file_path.exists():
            return file_path
    return None


def read_csv_with_encoding(file_path: Path) -> Tuple[List[Dict[str, str]], str]:
    """Read CSV file with encoding fallback: utf-8 -> utf-8-sig -> latin1."""
    encodings = ['utf-8', 'utf-8-sig', 'latin1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Remove BOM if present
                content = f.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                # Auto-detect delimiter
                first_line = content.split('\n')[0] if '\n' in content else content
                delimiter = ';' if first_line.count(';') > first_line.count(',') else ','
                
                # Parse CSV
                from io import StringIO
                reader = csv.DictReader(StringIO(content), delimiter=delimiter)
                rows = list(reader)
                return rows, encoding
        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Failed to read {file_path} with any supported encoding")


def detect_telemetry_format(fieldnames: List[str]) -> str:
    """Detect if telemetry file is in long or wide format."""
    # Normalize field names for comparison
    normalized = [field.strip().lower() for field in fieldnames]
    
    # Check for long format indicators
    long_format_indicators = ['timestamp', 'telemetry_name', 'telemetry_value']
    long_format_count = sum(1 for indicator in long_format_indicators if indicator in normalized)
    
    # Check for simplified long format indicators
    simplified_indicators = ['ts_ms', 'name', 'value']
    simplified_count = sum(1 for indicator in simplified_indicators if indicator in normalized)
    
    if long_format_count >= 3 or simplified_count >= 3:
        return 'long'
    else:
        return 'wide'


def normalize_header(header: str) -> str:
    """Normalize header names to canonical form."""
    header_lower = header.strip().lower()
    
    # Timestamp mappings
    if header_lower in ['timestamp', 'meta_time', 'ts_ms', 'timestamp_ms', 'time_ms', 'time_utc_seconds']:
        return 'ts_ms'
    
    # Telemetry name mappings
    if header_lower in ['telemetry_name', 'name', 'channel', 'signal']:
        return 'name'
    
    # Telemetry value mappings
    if header_lower in ['telemetry_value', 'value', 'val']:
        return 'value'
    
    return header.strip()


def process_telemetry_long_format(rows: List[Dict[str, str]], fieldnames: List[str]) -> List[Dict[str, str]]:
    """Process telemetry data that's already in long format."""
    # Create header mapping to canonical names
    header_map = {}
    for field in fieldnames:
        normalized = normalize_header(field)
        if normalized in ['ts_ms', 'name', 'value']:
            header_map[field] = normalized
    
    # Process rows
    processed_rows = []
    for row in rows:
        new_row = {}
        for canonical_name, original_name in {v: k for k, v in header_map.items()}.items():
            if original_name in row:
                new_row[canonical_name] = row[original_name].strip()
        
        # Only include rows with all required fields
        if all(field in new_row and new_row[field] for field in ['ts_ms', 'name', 'value']):
            processed_rows.append(new_row)
    
    return processed_rows


def process_telemetry_wide_format(rows: List[Dict[str, str]], fieldnames: List[str]) -> List[Dict[str, str]]:
    """Process telemetry data in wide format by pivoting to long format."""
    # Find timestamp column
    timestamp_column = None
    for field in fieldnames:
        normalized = normalize_header(field)
        if normalized == 'timestamp':
            timestamp_column = field
            break
    
    if not timestamp_column:
        raise ValueError("Could not detect timestamp column in wide format telemetry data")
    
    # Identify telemetry columns (all non-timestamp columns)
    telemetry_columns = [field for field in fieldnames if field != timestamp_column]
    
    # Pivot to long format
    processed_rows = []
    for row_num, row in enumerate(rows, 1):
        timestamp_value = row.get(timestamp_column, '').strip()
        if not timestamp_value:
            continue
        
        for column in telemetry_columns:
            telemetry_name = column.strip()
            telemetry_value = row.get(column, '').strip()
            
            # Skip empty values
            if not telemetry_value:
                continue
            
            processed_rows.append({
                'ts_ms': timestamp_value,
                'name': telemetry_name,
                'value': telemetry_value
            })
    
    return processed_rows


def process_telemetry(raw_dir: Path, out_dir: Path) -> Tuple[int, str]:
    """Process telemetry data and return (row_count, source_file)."""
    # Find telemetry file
    candidates = [
        'R1_barber_telemetry_data.csv',
        'R1_barber_telemetry_long.csv',
        'R1_barber_telemetry.csv',
        'R2_barber_telemetry_data.csv',
        'R2_barber_telemetry_long.csv',
        'R2_barber_telemetry.csv'
    ]
    
    # Also try wildcard pattern
    telemetry_files = list(raw_dir.glob('*_telemetry_data.csv'))
    if telemetry_files:
        candidates.extend([f.name for f in telemetry_files])
    
    telemetry_file = find_raw_file(raw_dir, candidates)
    if not telemetry_file:
        raise ValueError(
            "No telemetry file found. Expected one of:\n"
            + "\n".join(f"  - {candidate}" for candidate in candidates[:6])
        )
    
    print(f"Processing telemetry from: {telemetry_file.name}")
    
    # Read CSV
    rows, encoding = read_csv_with_encoding(telemetry_file)
    if not rows:
        raise ValueError(f"Empty telemetry file: {telemetry_file}")
    
    fieldnames = list(rows[0].keys())
    format_type = detect_telemetry_format(fieldnames)
    
    print(f"  Detected format: {format_type}")
    
    # Process based on format
    if format_type == 'long':
        processed_rows = process_telemetry_long_format(rows, fieldnames)
    else:
        processed_rows = process_telemetry_wide_format(rows, fieldnames)
    
    # Write output
    output_file = out_dir / 'telemetry.csv'
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ts_ms', 'name', 'value'])
        writer.writeheader()
        writer.writerows(processed_rows)
    
    print(f"  Wrote {len(processed_rows)} rows to {output_file}")
    return len(processed_rows), telemetry_file.name


def process_weather(raw_dir: Path, out_dir: Path) -> Tuple[int, str]:
    """Process weather data and return (row_count, source_file)."""
    candidates = [
        '26_Weather_Race_1_Anonymized.CSV',
        '26_Weather_Race_2_Anonymized.CSV',
        '26_Weather_Race_1.csv',
        '26_Weather_Race_2.csv'
    ]
    
    weather_file = find_raw_file(raw_dir, candidates)
    if not weather_file:
        raise ValueError(
            "No weather file found. Expected one of:\n"
            + "\n".join(f"  - {candidate}" for candidate in candidates)
        )
    
    print(f"Processing weather from: {weather_file.name}")
    
    # Read CSV
    rows, encoding = read_csv_with_encoding(weather_file)
    if not rows:
        raise ValueError(f"Empty weather file: {weather_file}")
    
    # Normalize headers - ensure we have a time column
    fieldnames = list(rows[0].keys())
    normalized_rows = []
    
    # Create header mapping
    header_map = {}
    for field in fieldnames:
        field_lower = field.strip().lower()
        # Map various time column names to a standard
        if field_lower in ['time_utc_seconds', 'time', 'timestamp', 'ts']:
            header_map[field] = 'TIME_UTC_SECONDS'
        else:
            header_map[field] = field.strip()
    
    # Process rows with normalized headers
    for row in rows:
        normalized_row = {}
        for original, normalized in header_map.items():
            if original in row:
                normalized_row[normalized] = row[original].strip()
        normalized_rows.append(normalized_row)
    
    # Write output
    output_file = out_dir / 'weather.csv'
    if normalized_rows:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(normalized_rows[0].keys()))
            writer.writeheader()
            writer.writerows(normalized_rows)
    
    print(f"  Wrote {len(normalized_rows)} rows to {output_file}")
    return len(normalized_rows), weather_file.name


def process_sections(raw_dir: Path, out_dir: Path) -> Tuple[int, str]:
    """Process sections data and return (row_count, source_file)."""
    candidates = [
        '23_AnalysisEnduranceWithSections_Race_1_Anonymized.CSV',
        '23_AnalysisEnduranceWithSections_Race_2_Anonymized.CSV',
        '23_AnalysisEnduranceWithSections_Race_1.csv',
        '23_AnalysisEnduranceWithSections_Race_2.csv'
    ]
    
    sections_file = find_raw_file(raw_dir, candidates)
    if not sections_file:
        raise ValueError(
            "No sections file found. Expected one of:\n"
            + "\n".join(f"  - {candidate}" for candidate in candidates)
        )
    
    print(f"Processing sections from: {sections_file.name}")
    
    # Read CSV
    rows, encoding = read_csv_with_encoding(sections_file)
    if not rows:
        raise ValueError(f"Empty sections file: {sections_file}")
    
    # Normalize headers - ensure LAP_TIME column exists
    fieldnames = list(rows[0].keys())
    normalized_rows = []
    
    # Create header mapping
    header_map = {}
    for field in fieldnames:
        field_lower = field.strip().lower()
        # Map various lap time column names to standard
        if field_lower in ['lap_time', 'laptime', 'time']:
            header_map[field] = 'LAP_TIME'
        else:
            header_map[field] = field.strip()
    
    # Process rows with normalized headers
    for row in rows:
        normalized_row = {}
        for original, normalized in header_map.items():
            if original in row:
                normalized_row[normalized] = row[original].strip()
        normalized_rows.append(normalized_row)
    
    # Write output
    output_file = out_dir / 'sections.csv'
    if normalized_rows:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(normalized_rows[0].keys()))
            writer.writeheader()
            writer.writerows(normalized_rows)
    
    print(f"  Wrote {len(normalized_rows)} rows to {output_file}")
    return len(normalized_rows), sections_file.name


def main():
    """Main function to process all raw TRD files."""
    # Define paths
    raw_dir = Path("data/barber/raw")
    out_dir = Path("data/barber")
    
    # Check raw directory exists
    if not raw_dir.exists():
        print(f"Error: Raw data directory not found: {raw_dir}")
        print("Please unzip the official Barber TRD dataset into this directory.")
        sys.exit(1)
    
    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Preparing Barber canonical CSVs from: {raw_dir}")
    print(f"Output directory: {out_dir}")
    print()
    
    try:
        # Process each file type
        telemetry_count, telemetry_source = process_telemetry(raw_dir, out_dir)
        weather_count, weather_source = process_weather(raw_dir, out_dir)
        sections_count, sections_source = process_sections(raw_dir, out_dir)
        
        print()
        print("Summary:")
        print(f"  Telemetry: {telemetry_count} rows from {telemetry_source}")
        print(f"  Weather:   {weather_count} rows from {weather_source}")
        print(f"  Sections:  {sections_count} rows from {sections_source}")
        print()
        print("Successfully prepared canonical CSV files!")
        print("You can now run: ./scripts/ingest_barber_demo.sh")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()