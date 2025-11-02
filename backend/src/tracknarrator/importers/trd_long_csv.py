"""TRD long CSV importer with pivot functionality."""

import csv
import io
from collections import defaultdict
from typing import BinaryIO, TextIO

from fastapi import HTTPException
from .base import ImportResult, coerce_float, coerce_int
from ..schema import Session, SessionBundle, Telemetry
from ..utils_time import iso_to_ms


class TRDLongCSVImporter:
    """Importer for TRD R1/R2 telemetry long-format CSV files."""
    
    # Pivot map: telemetry_name -> field_name
    PIVOT_MAP = {
        "speed": "speed_kph",
        "aps": "throttle_pct",
        "pbrake_f": "brake_bar",
        "pbrake_r": "brake_bar",  # fallback
        "gear": "gear",
        "accx_can": "acc_long_g",
        "accy_can": "acc_lat_g",
        "Steering_Angle": "steer_deg",
        "VBOX_Lat_Min": "lat_deg",
        "VBOX_Long_Minutes": "lon_deg",
    }
    
    # Synonyms for variant field names (case-insensitive)
    SYNONYMS = {
        "vbox_long_min": "VBOX_Long_Minutes",   # accept both spellings
        "steering_angle": "Steering_Angle"      # case-insensitive variant
    }
    
    # Numeric tolerances and validation rules
    THROTTLE_MIN, THROTTLE_MAX = 0.0, 100.0
    GEAR_MIN, GEAR_MAX = 0, 10
    ACC_MIN, ACC_MAX = -10.0, 10.0
    STEER_MIN, STEER_MAX = -720.0, 720.0
    SPEED_MIN, SPEED_MAX = 0.0, 350.0
    BRAKE_MIN, BRAKE_MAX = 0.0, 200.0
    
    @classmethod
    def import_file(cls, file: BinaryIO | TextIO, session_id: str) -> ImportResult:
        """
        Import TRD long CSV file and pivot to telemetry format.
        
        Args:
            file: File-like object containing CSV data
            session_id: Session ID for the telemetry data
            
        Returns:
            ImportResult with telemetry data and any warnings
        """
        warnings = []
        
        try:
            # Handle both binary and text files
            if hasattr(file, 'read'):
                content = file.read()
                if isinstance(content, bytes):
                    text_io = io.TextIOWrapper(io.BytesIO(content), encoding='utf-8')
                else:
                    text_io = io.StringIO(content)
            else:
                text_io = file
            
            # Read CSV data
            reader = csv.DictReader(text_io)
            rows = list(reader)
            
            if not rows:
                return ImportResult.failure(["Empty CSV file"])
            
            # Detect field mappings
            fieldnames = reader.fieldnames or []
            
            # Try to detect ts_ms, name, value fields
            ts_field = None
            name_field = None
            value_field = None
            
            # Check for simplified format (ts_ms, name, value)
            for field in fieldnames:
                field_lower = field.lower().strip()
                if field_lower in ['ts_ms', 'timestamp_ms', 'timestamp', 'meta_time', 'time_ms']:
                    ts_field = field
                elif field_lower in ['name', 'telemetry_name', 'channel', 'signal']:
                    name_field = field
                elif field_lower in ['value', 'telemetry_value', 'val']:
                    value_field = field
            
            # If simplified format not found, check for TRD format
            if not (ts_field and name_field and value_field):
                # Check for TRD format with timestamp and telemetry_name
                for field in fieldnames:
                    field_lower = field.lower().strip()
                    if field_lower in ['timestamp', 'meta_time']:
                        ts_field = field
                    elif field_lower == 'telemetry_name':
                        name_field = field
                    elif field_lower == 'telemetry_value':
                        value_field = field
            
            # If still not found, raise error
            if not (ts_field and name_field and value_field):
                return ImportResult.failure(["Required headers not found. Expected: ts_ms,name,value or timestamp,telemetry_name,telemetry_value"])
            
            # Group by timestamp and pivot
            telemetry_by_timestamp = defaultdict(dict)
            unknown_names = set()
            
            for row in rows:
                # Get timestamp
                ts_value = row.get(ts_field, '').strip()
                if not ts_value:
                    warnings.append("Row missing timestamp, skipping")
                    continue
                
                # Convert to ms if needed
                try:
                    if ts_field.lower() in ['ts_ms', 'timestamp_ms', 'time_ms']:
                        # Parse as integer milliseconds
                        ts_ms = int(ts_value)
                    else:
                        # Try to parse as ISO timestamp
                        ts_ms = iso_to_ms(ts_value)
                except ValueError as e:
                    warnings.append(f"Invalid timestamp '{ts_value}': {e}")
                    continue
                
                # Get and normalize channel name
                telemetry_name = row.get(name_field, '').strip()
                telemetry_value = row.get(value_field, '').strip()
                
                if not telemetry_name:
                    continue
                
                # Apply synonyms (case-insensitive)
                channel_lower = telemetry_name.lower()
                if channel_lower in cls.SYNONYMS:
                    telemetry_name = cls.SYNONYMS[channel_lower]
                
                # Map telemetry name to field
                field_name = cls.PIVOT_MAP.get(telemetry_name)
                if not field_name:
                    unknown_names.add(telemetry_name)
                    continue
                
                # Store multiple values for the same field to handle duplicates
                if field_name not in telemetry_by_timestamp[ts_ms]:
                    telemetry_by_timestamp[ts_ms][field_name] = []
                telemetry_by_timestamp[ts_ms][field_name].append(telemetry_value)
            
            # Add warning for unknown telemetry names
            if unknown_names:
                warnings.append(f"Unknown telemetry names: {', '.join(sorted(unknown_names))}")
            
            # Convert grouped data to Telemetry objects with de-duplication
            telemetry_list = []
            
            # Group timestamps into buckets within ±1 ms
            timestamp_buckets = cls._bucket_timestamps(telemetry_by_timestamp)
            
            for bucket_ts, timestamps in timestamp_buckets.items():
                # Find the best timestamp (one with most non-None fields)
                best_ts_ms = None
                best_field_count = -1
                best_field_values = None
                
                for ts_ms in timestamps:
                    field_values = telemetry_by_timestamp[ts_ms]
                    non_none_count = sum(1 for values in field_values.values()
                                        if values and any(cls._process_field_value(field_name, v) is not None
                                                        for v in values))
                    
                    if non_none_count > best_field_count:
                        best_field_count = non_none_count
                        best_ts_ms = ts_ms
                        best_field_values = field_values
                
                # Use the best timestamp and field values
                ts_ms = best_ts_ms
                field_values = best_field_values
                # Apply pbrake_r fallback if pbrake_f missing
                if 'brake_bar' not in field_values:
                    # Look for pbrake_r in original rows for this timestamp
                    for row in rows:
                        if (row.get('timestamp') or row.get('meta_time')) and \
                           iso_to_ms(row.get('timestamp') or row.get('meta_time')) == ts_ms:
                            if row.get('telemetry_name') == 'pbrake_r':
                                field_values['brake_bar'] = [row.get('telemetry_value', '')]
                                break
                
                # Process field values - handle multiple values per field
                telemetry_data = {'session_id': session_id, 'ts_ms': ts_ms}
                valid_fields_count = 0
                
                total_fields_count = 0
                
                for field_name, raw_values in field_values.items():
                    # Check all values - if any are outliers, reject the field
                    field_valid = True
                    final_value = None
                    
                    for raw_value in raw_values:
                        processed_value = cls._process_field_value(field_name, raw_value, check_outlier_only=True)
                        if processed_value is False:  # This means it's an outlier (False, not None)
                            field_valid = False
                            break
                    
                    # If field is valid, get the first valid value
                    if field_valid:
                        for raw_value in raw_values:
                            processed_value = cls._process_field_value(field_name, raw_value, check_outlier_only=False)
                            if processed_value is not None:
                                final_value = processed_value
                                break
                    else:
                        # For outlier fields, set to None but still count as a field
                        final_value = None
                    
                    # Always include the field, but set to None if it's an outlier
                    telemetry_data[field_name] = final_value
                    total_fields_count += 1
                    if final_value is not None:
                        valid_fields_count += 1
                
                # Keep row only if at least 5 mapped numeric fields (excluding outliers)
                if valid_fields_count >= 5:
                    telemetry_list.append(Telemetry(**telemetry_data))
            
            if not telemetry_list:
                return ImportResult.failure(["No valid telemetry rows found"])
            
            # Create session and bundle
            session = Session(
                id=session_id,
                source="trd_csv",
                track_id="unknown",  # Will be updated by other importers
            )
            
            bundle = SessionBundle(
                session=session,
                telemetry=telemetry_list
            )
            
            return ImportResult.success(bundle, warnings)
            
        except Exception as e:
            return ImportResult.failure([f"Error processing TRD CSV: {str(e)}"])
    
    @classmethod
    def _process_field_value(cls, field_name: str, raw_value: str, check_outlier_only: bool = False):
        """Process and validate a single field value."""
        if not raw_value or raw_value.lower() in ('', 'nan', 'inf', '-inf'):
            return None
        
        try:
            if field_name in ['speed_kph', 'throttle_pct', 'brake_bar', 'acc_long_g', 'acc_lat_g', 'steer_deg', 'lat_deg', 'lon_deg']:
                value = float(raw_value)
                if check_outlier_only:
                    return cls._validate_numeric_field(field_name, value, check_outlier_only=True)
                else:
                    return cls._validate_numeric_field(field_name, value)
            elif field_name == 'gear':
                value = int(float(raw_value))  # Handle "6.0" -> 6
                if check_outlier_only:
                    return cls._validate_gear(value, check_outlier_only=True)
                else:
                    return cls._validate_gear(value)
            else:
                return None
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def _validate_numeric_field(cls, field_name: str, value: float, check_outlier_only: bool = False):
        """Validate and clamp numeric fields according to specifications."""
        if field_name == 'throttle_pct':
            # Clamp throttle to [0, 100]
            if check_outlier_only:
                return True  # Throttle is clamped, never rejected as outlier
            return max(cls.THROTTLE_MIN, min(cls.THROTTLE_MAX, value))
        elif field_name == 'speed_kph':
            # Set None for outliers outside expected range
            if cls.SPEED_MIN <= value <= cls.SPEED_MAX:
                return value if not check_outlier_only else True
            return None if not check_outlier_only else False
        elif field_name == 'brake_bar':
            # Set None for outliers outside expected range
            if cls.BRAKE_MIN <= value <= cls.BRAKE_MAX:
                return value if not check_outlier_only else True
            return None if not check_outlier_only else False
        elif field_name in ['acc_long_g', 'acc_lat_g']:
            # Set None for outliers outside ±10g
            if cls.ACC_MIN <= value <= cls.ACC_MAX:
                return value if not check_outlier_only else True
            return None if not check_outlier_only else False
        elif field_name == 'steer_deg':
            # Set None for outliers outside ±720 degrees
            if cls.STEER_MIN <= value <= cls.STEER_MAX:
                return value if not check_outlier_only else True
            return None if not check_outlier_only else False
        elif field_name == 'lat_deg':
            # Validate latitude bounds [-90, 90]
            if -90.0 <= value <= 90.0:
                return value if not check_outlier_only else True
            return None if not check_outlier_only else False
        elif field_name == 'lon_deg':
            # Validate longitude bounds [-180, 180]
            if -180.0 <= value <= 180.0:
                return value if not check_outlier_only else True
            return None if not check_outlier_only else False
        else:
            return value if not check_outlier_only else True
    
    @classmethod
    def _validate_gear(cls, value: int, check_outlier_only: bool = False):
        """Validate gear value."""
        if cls.GEAR_MIN <= value <= cls.GEAR_MAX:
            return value if not check_outlier_only else True
        return None if not check_outlier_only else False
    
    @classmethod
    def _bucket_timestamps(cls, telemetry_by_timestamp: dict) -> dict:
        """
        Group timestamps into buckets within ±1 ms range.
        
        Args:
            telemetry_by_timestamp: Dictionary mapping timestamp -> field_values
            
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
    
    @classmethod
    def inspect_trd_csv(cls, text: str) -> dict:
        """
        Inspect TRD CSV file to diagnose channel mappings.
        
        Args:
            text: CSV content as string
            
        Returns:
            Dictionary with inspection results
        """
        import csv
        import io
        from collections import defaultdict
        
        # Parse CSV
        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        except Exception as e:
            raise ValueError(f"Invalid CSV format: {str(e)}")
        
        if not rows:
            return {
                "recognized_channels": [],
                "missing_expected": list(cls.PIVOT_MAP.keys()),
                "unrecognized_names": [],
                "rows_total": 0,
                "timestamps": 0,
                "min_fields_per_ts": 0
            }
        
        # Detect field mappings
        fieldnames = reader.fieldnames or []
        
        # Try to detect ts_ms, name, value fields
        ts_field = None
        name_field = None
        value_field = None
        
        # Check for simplified format (ts_ms, name, value)
        for field in fieldnames:
            field_lower = field.lower().strip()
            if field_lower in ['ts_ms', 'timestamp_ms', 'timestamp', 'meta_time', 'time_ms']:
                ts_field = field
            elif field_lower in ['name', 'telemetry_name', 'channel', 'signal']:
                name_field = field
            elif field_lower in ['value', 'telemetry_value', 'val']:
                value_field = field
        
        # If simplified format not found, check for TRD format
        if not (ts_field and name_field and value_field):
            # Check for TRD format with timestamp and telemetry_name
            for field in fieldnames:
                field_lower = field.lower().strip()
                if field_lower in ['timestamp', 'meta_time']:
                    ts_field = field
                elif field_lower == 'telemetry_name':
                    name_field = field
                elif field_lower == 'telemetry_value':
                    value_field = field
        
        # If still not found, raise error
        if not (ts_field and name_field and value_field):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "bad_trd_csv",
                    "required_headers": [
                        ["ts_ms", "name", "value"],
                        ["timestamp_ms", "telemetry_name", "telemetry_value"]
                    ]
                }
            )
        
        # Process rows and collect channel names
        names = set()
        timestamps = set()
        counts_per_ts = defaultdict(int)
        
        for row in rows:
            # Get timestamp
            ts_value = row.get(ts_field, '').strip()
            if not ts_value:
                continue
                
            # Convert to ms if needed
            try:
                if ts_field.lower() in ['time', 'time_ms']:
                    # If it looks like seconds (max value < 1e10), convert to ms
                    ts_float = float(ts_value)
                    if ts_float < 1e10:  # Likely seconds
                        ts_ms = int(ts_float * 1000)
                    else:  # Already ms
                        ts_ms = int(ts_float)
                else:
                    # Try to parse as ISO timestamp
                    from ..utils_time import iso_to_ms
                    try:
                        ts_ms = iso_to_ms(ts_value)
                    except ValueError:
                        # If ISO parsing fails, try to parse as int
                        ts_ms = int(ts_value)
                timestamps.add(ts_ms)
            except (ValueError, TypeError):
                continue
            
            # Get and normalize channel name
            channel_name = row.get(name_field, '').strip()
            if not channel_name:
                continue
                
            # Apply synonyms (case-insensitive)
            channel_lower = channel_name.lower()
            if channel_lower in cls.SYNONYMS:
                channel_name = cls.SYNONYMS[channel_lower]
            
            names.add(channel_name)
            counts_per_ts[ts_ms] += 1
        
        # Analyze channels
        recognized = sorted(list(set(names) & set(cls.PIVOT_MAP.keys())))
        missing = sorted(list(set(cls.PIVOT_MAP.keys()) - set(recognized)))
        unrecognized = sorted(list(set(names) - set(cls.PIVOT_MAP.keys())))[:20]
        
        # Calculate statistics
        rows_total = len(rows)
        ts_count = len(timestamps)
        per_bucket_min_fields = min(counts_per_ts.values()) if counts_per_ts else 0
        
        return {
            "recognized_channels": recognized,
            "missing_expected": missing,
            "unrecognized_names": unrecognized,
            "rows_total": rows_total,
            "timestamps": ts_count,
            "min_fields_per_ts": per_bucket_min_fields
        }
    
    @staticmethod
    def inspect_text(text: str) -> dict:
        """
        Alias for inspect_trd_csv method.
        
        Args:
            text: CSV content as string
            
        Returns:
            Dictionary with inspection results
        """
        return TRDLongCSVImporter.inspect_trd_csv(text)