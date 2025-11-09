#!/usr/bin/env python3
"""Export session data from TrackNarrator API."""

import argparse
import json
import sys
from pathlib import Path
import requests
from urllib.parse import urljoin


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Export session data from TrackNarrator API")
    parser.add_argument("--session", required=True, help="Session ID to export")
    parser.add_argument("--out", required=True, help="Output file path")
    parser.add_argument("--lang", default="zh-Hant", choices=["zh-Hant", "en"], 
                       help="Language for coaching tips (default: zh-Hant)")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL for TrackNarrator API (default: http://localhost:8000)")
    
    args = parser.parse_args()
    
    # Construct API URL
    export_url = urljoin(args.base_url.rstrip("/") + "/", f"session/{args.session}/export")
    
    try:
        # Make API request
        response = requests.get(
            export_url,
            params={"lang": args.lang},
            headers={"Accept": "application/zip"}
        )
        
        response.raise_for_status()
        
        # Write to file
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Export saved to: {output_path}")
        print(f"Session ID: {args.session}")
        print(f"Language: {args.lang}")
        print(f"Size: {len(response.content)} bytes")
        
        # Verify it's a valid ZIP file
        import zipfile
        try:
            with zipfile.ZipFile(output_path, 'r') as zip_file:
                file_list = zip_file.namelist()
                print(f"Files in export: {', '.join(file_list)}")
        except zipfile.BadZipFile:
            print("Error: Exported file is not a valid ZIP file", file=sys.stderr)
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()