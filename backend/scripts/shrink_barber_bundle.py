#!/usr/bin/env python3
"""
Script to downsample high-frequency telemetry data from a full TrackNarrator bundle.

This script creates a smaller version of the bundle suitable for GitHub distribution
while preserving all laps, sections, events, and metadata.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Default downsample factor
DOWNSAMPLE_FACTOR = 10

# Threshold for considering an array "large"
LARGE_ARRAY_THRESHOLD = 2000

def downsample_array(arr, factor):
    """
    Downsample an array by keeping every Nth element.
    
    Args:
        arr: List to downsample
        factor: Downsample factor (keep every Nth element)
    
    Returns:
        Downsampled array
    """
    if not isinstance(arr, list) or len(arr) <= LARGE_ARRAY_THRESHOLD:
        return arr
    
    return arr[::factor]

def downsample_bundle(bundle, factor):
    """
    Apply downsampling to telemetry and weather data in a bundle.
    
    Args:
        bundle: The session bundle dictionary
        factor: Downsample factor
    
    Returns:
        Modified bundle with downsampled telemetry and weather
    """
    # Create a copy to avoid modifying the original
    result = bundle.copy()
    
    # Downsample the telemetry array if it exists
    if "telemetry" in result:
        original_count = len(result["telemetry"])
        result["telemetry"] = downsample_array(result["telemetry"], factor)
        print(f"Downsampled telemetry from {original_count} to {len(result['telemetry'])} points")
    
    # Downsample the weather array if it exists
    if "weather" in result:
        original_count = len(result["weather"])
        result["weather"] = downsample_array(result["weather"], factor)
        print(f"Downsampled weather from {original_count} to {len(result['weather'])} points")
    
    return result

def main():
    """Main function to handle command line arguments and execute downsampling."""
    parser = argparse.ArgumentParser(description="Downsample TrackNarrator bundle for GitHub distribution")
    parser.add_argument("--input", default="data/barber/bundle_full_barber.json",
                        help="Input bundle file path")
    parser.add_argument("--output", default="fixtures/bundle_sample_barber.json",
                        help="Output sample bundle file path")
    parser.add_argument("--factor", type=int, default=DOWNSAMPLE_FACTOR,
                        help=f"Downsample factor (default: {DOWNSAMPLE_FACTOR})")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        print("Please run ./scripts/ingest_barber_demo.sh first to generate the full bundle.")
        sys.exit(1)
    
    # Load the bundle
    with open(args.input, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    
    # Apply downsampling
    downsampled_bundle = downsample_bundle(bundle, args.factor)
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the downsampled bundle
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(downsampled_bundle, f, ensure_ascii=False)
    
    # Get file size for reporting
    input_size = os.path.getsize(args.input) / (1024 * 1024)  # Size in MB
    output_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
    
    print(f"Downsampled bundle written to {output_path}")
    print(f"Input size: {input_size:.2f} MB")
    print(f"Output size: {output_size:.2f} MB")
    print(f"Size reduction: {(1 - output_size/input_size)*100:.1f}%")

if __name__ == "__main__":
    main()