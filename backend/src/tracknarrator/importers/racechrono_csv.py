"""RaceChrono CSV importer with encoding and delimiter detection."""

import csv
import io
from collections import defaultdict
from typing import BinaryIO, TextIO, Dict, List, Tuple

from .base import ImportResult, coerce_float, coerce_int
from ..schema import Session, SessionBundle, Telemetry


class RaceChronoCSVImporter:
    """Importer for RaceChrono CSV telemetry files."""
    
    # Header mapping for RaceChrono CSV
    HEADER_MAP = {
        'Time (s)': 'time_s',
        'Speed (km/h)': 'speed_kph',
        'Longitude': 'lon_deg',
        'Latitude': 'lat_deg',
        'Throttle pos (%)': 'throttle_pct',
        'Brake pos (%)': 'brake_pos_pct'  # Will be ignored with warning
    }
    
    # Validation ranges
    SPEED_MIN, SPEED_MAX = 0.0, 400.0
    THROTTLE_MIN, THROTTLE_MAX = 0.0, 100.0
    LAT_MIN, LAT_MAX = -90.0, 90.0
    LON_MIN, LON_MAX = -180.0, 180.0
    
    @classmethod
    def import_file(cls, file: BinaryIO | TextIO, session_id: str) -> ImportResult:
        """
        Import RaceChrono CSV file.
        
        Args:
            file: File-like object containing CSV data
            session_id: Session ID for the telemetry data
            
        Returns:
            ImportResult with telemetry data and any warnings
        """
        warnings = []
        
        try:
            # Handle both binary and text files with encoding fallback
            content, encoding_used = cls._read_file_with_encoding_fallback(file)
            if content is None:
                return ImportResult.failure(["Failed to read file with any supported encoding"])
            
            # Auto-detect delimiter
            delimiter = cls._detect_delimiter(content)
            
            # Parse CSV
            text_io = io.StringIO(content)
            reader = csv.DictReader(text_io, delimiter=delimiter)
            rows = list(reader)
            
            
            if not rows:
                return ImportResult.failure(["Empty CSV file"])
            
            # Check for brake column and add warning if present
            fieldnames = reader.fieldnames or []
            has_brake_column = any('brake' in field.lower() for field in fieldnames)
            if has_brake_column:
                warnings.append("racechrono: brake_pos_pct not mapped to Telemetry.brake_bar (different units), dropped")
            
            # Process rows with de-duplication
            telemetry_by_timestamp = defaultdict(list)
            
            for row_num, row in enumerate(rows, 1):
                try:
                    telemetry_data = cls._process_row(row, session_id, row_num, warnings)
                    if telemetry_data:
                        telemetry_by_timestamp[telemetry_data['ts_ms']].append(telemetry_data)
                except Exception as e:
                    warnings.append(f"Row {row_num}: Error processing row: {e}")
                    continue
            
            if not telemetry_by_timestamp:
                return ImportResult.failure(["No valid telemetry rows found"])
            
            # De-duplicate timestamps within ±1ms
            telemetry_list = cls._deduplicate_telemetry(telemetry_by_timestamp)
            
            if not telemetry_list:
                return ImportResult.failure(["No valid telemetry rows after de-duplication"])
            
            # Sort by timestamp
            telemetry_list.sort(key=lambda t: t.ts_ms)
            
            # Create session and bundle
            session = Session(
                id=session_id,
                source="racechrono_csv",
                track_id="unknown",  # Will be updated by other importers
            )
            
            bundle = SessionBundle(
                session=session,
                telemetry=telemetry_list
            )
            
            return ImportResult.success(bundle, warnings)
            
        except Exception as e:
            return ImportResult.failure([f"Error processing RaceChrono CSV: {str(e)}"])
    
    @classmethod
    def _read_file_with_encoding_fallback(cls, file: BinaryIO | TextIO) -> Tuple[str, str]:
        """
        Read file with encoding fallback: utf-8 -> utf-8-sig -> latin1.
        
        Returns:
            tuple: (content, encoding_used) or (None, None) if all fail
        """
        encodings = ['utf-8', 'utf-8-sig', 'latin1']
        
        # Handle binary file
        if hasattr(file, 'read'):
            content = file.read()
            if isinstance(content, bytes):
                for encoding in encodings:
                    try:
                        decoded = content.decode(encoding)
                        # Remove BOM if present
                        if decoded.startswith('\ufeff'):
                            decoded = decoded[1:]
                        return decoded, encoding
                    except UnicodeDecodeError:
                        continue
                return None, None
            else:
                # Already text, remove BOM if present
                text = content
                if text.startswith('\ufeff'):
                    text = text[1:]
                return text, 'utf-8'
        else:
            # Already text, remove BOM if present
            text = str(file)
            if text.startswith('\ufeff'):
                text = text[1:]
            return text, 'utf-8'
    
    @classmethod
    def _detect_delimiter(cls, content: str) -> str:
        """
        Auto-detect CSV delimiter based on first line.
        
        Returns:
            ';' if more semicolons than commas, otherwise ','
        """
        first_line = content.split('\n')[0] if '\n' in content else content
        semicolon_count = first_line.count(';')
        comma_count = first_line.count(',')
        
        return ';' if semicolon_count > comma_count else ','
    
    @classmethod
    def _process_row(cls, row: Dict[str, str], session_id: str, row_num: int, warnings: List[str]) -> Dict | None:
        """Process a single CSV row and return telemetry data."""
        # Get and validate timestamp
        time_s_raw = row.get('Time (s)', '').strip()
        if not time_s_raw:
            return None
        
        try:
            time_s = float(time_s_raw)
            if not (0 <= time_s <= 86400):  # Max 24 hours in seconds
                warnings.append(f"Row {row_num}: Time {time_s}s outside reasonable range")
                return None
            ts_ms = round(time_s * 1000)
        except ValueError:
            warnings.append(f"Row {row_num}: Invalid time format '{time_s_raw}'")
            return None
        
        # Extract and validate fields
        telemetry_data = {
            'session_id': session_id,  # Set session_id here
            'ts_ms': ts_ms,
            'speed_kph': cls._validate_speed(row.get('Speed (km/h)', '').strip()),
            'throttle_pct': cls._validate_throttle(row.get('Throttle pos (%)', '').strip()),
            'lat_deg': cls._validate_latitude(row.get('Latitude', '').strip()),
            'lon_deg': cls._validate_longitude(row.get('Longitude', '').strip()),
            # Other fields remain None
            'brake_bar': None,
            'gear': None,
            'acc_long_g': None,
            'acc_lat_g': None,
            'steer_deg': None,
        }
        
        # Count non-None fields (excluding session_id and ts_ms)
        non_none_count = sum(1 for k, v in telemetry_data.items() 
                           if k not in ['session_id', 'ts_ms'] and v is not None)
        
        # Return None if no valid telemetry fields
        if non_none_count == 0:
            return None
        
        return telemetry_data
    
    @classmethod
    def _validate_speed(cls, value: str) -> float | None:
        """Validate and clamp speed in km/h."""
        if not value:
            return None
        
        try:
            speed = float(value)
            # Clamp to valid range
            return max(cls.SPEED_MIN, min(cls.SPEED_MAX, speed))
        except ValueError:
            return None
    
    @classmethod
    def _validate_throttle(cls, value: str) -> float | None:
        """Validate and clamp throttle percentage."""
        if not value:
            return None
        
        try:
            throttle = float(value)
            return max(cls.THROTTLE_MIN, min(cls.THROTTLE_MAX, throttle))
        except ValueError:
            return None
    
    @classmethod
    def _validate_latitude(cls, value: str) -> float | None:
        """Validate and clamp latitude in degrees."""
        if not value:
            return None
        
        try:
            lat = float(value)
            # Clamp to valid range
            return max(cls.LAT_MIN, min(cls.LAT_MAX, lat))
        except ValueError:
            return None
    
    @classmethod
    def _validate_longitude(cls, value: str) -> float | None:
        """Validate and clamp longitude in degrees."""
        if not value:
            return None
        
        try:
            lon = float(value)
            # Clamp to valid range
            return max(cls.LON_MIN, min(cls.LON_MAX, lon))
        except ValueError:
            return None
    
    @classmethod
    def _deduplicate_telemetry(cls, telemetry_by_timestamp: Dict[int, List[Dict]]) -> List[Telemetry]:
        """
        De-duplicate telemetry within ±1ms buckets.
        
        For each bucket, keep the row with more non-None fields.
        
        Args:
            telemetry_by_timestamp: Dictionary mapping ts_ms -> list of telemetry data
            
        Returns:
            List of Telemetry objects
        """
        # Group timestamps into buckets within ±1ms
        timestamp_buckets = cls._bucket_timestamps(telemetry_by_timestamp)
        
        result = []
        for bucket_ts, timestamps in timestamp_buckets.items():
            # Find the best timestamp (one with most non-None fields)
            best_data = None
            best_non_none_count = -1
            
            for ts_ms in timestamps:
                for telemetry_data in telemetry_by_timestamp[ts_ms]:
                    non_none_count = sum(1 for k, v in telemetry_data.items()
                                       if k not in ['session_id', 'ts_ms'] and v is not None)
                    
                    if non_none_count > best_non_none_count:
                        best_non_none_count = non_none_count
                        best_data = telemetry_data
            
            if best_data:
                result.append(Telemetry(**best_data))
        
        return result
    
    @classmethod
    def _bucket_timestamps(cls, telemetry_by_timestamp: Dict[int, List[Dict]]) -> Dict[int, List[int]]:
        """
        Group timestamps into buckets within ±1ms range.
        
        Args:
            telemetry_by_timestamp: Dictionary mapping timestamp -> list of telemetry data
            
        Returns:
            Dictionary mapping bucket_timestamp -> list of original timestamps
        """
        if not telemetry_by_timestamp:
            return {}
        
        # Sort timestamps
        sorted_timestamps = sorted(telemetry_by_timestamp.keys())
        
        # Create buckets
        buckets = {}
        current_bucket = []
        bucket_start = None
        
        for ts_ms in sorted_timestamps:
            if bucket_start is None:
                # Start first bucket
                bucket_start = ts_ms
                current_bucket = [ts_ms]
            elif ts_ms - bucket_start <= 1:
                # Within ±1 ms, add to current bucket
                current_bucket.append(ts_ms)
            else:
                # Too far, start new bucket
                buckets[bucket_start] = current_bucket
                bucket_start = ts_ms
                current_bucket = [ts_ms]
        
        # Add the last bucket
        if current_bucket:
            buckets[bucket_start] = current_bucket
        
        return buckets