"""Weather CSV importer with semicolon delimiter support."""

import csv
import io
from typing import Any, BinaryIO, Dict, List, TextIO, Tuple

from .base import ImportResult, coerce_float, coerce_int
from ..schema import Session, SessionBundle, WeatherPoint
from ..utils_time import safe_int


class WeatherCSVImporter:
    """Importer for weather data CSV files."""
    
    # Header mapping for weather data
    HEADER_MAP = {
        'TIME_UTC_SECONDS': 'ts_seconds',
        'AIR_TEMP': 'air_temp_c',
        'TRACK_TEMP': 'track_temp_c', 
        'HUMIDITY': 'humidity_pct',
        'PRESSURE': 'pressure_hpa',
        'WIND_SPEED': 'wind_speed',
        'WIND_DIRECTION': 'wind_dir_deg',
        'RAIN': 'rain_flag'
    }
    
    @classmethod
    def import_file(cls, file: BinaryIO | TextIO, session_id: str) -> ImportResult:
        """
        Import weather CSV file.
        
        Args:
            file: File-like object containing CSV data
            session_id: Session ID for the weather data
            
        Returns:
            ImportResult with weather data and any warnings
        """
        warnings = []
        
        try:
            # Handle both binary and text files with encoding fallback
            content, encoding_used = cls._read_file_with_encoding_fallback(file)
            if content is None:
                return ImportResult.failure(["Failed to read file with any supported encoding"])
            
            # Auto-detect delimiter
            delimiter = cls._detect_delimiter(content)
            
            # Read CSV data
            text_io = io.StringIO(content)
            reader = csv.DictReader(text_io, delimiter=delimiter)
            rows = list(reader)
            
            if not rows:
                return ImportResult.failure(["Empty CSV file"])
            
            # Check if we have any valid weather headers using the new alias resolution
            fieldnames = reader.fieldnames or []
            resolved = cls.resolve_weather_columns(fieldnames)
            
            # Check if we have at least a timestamp and one weather field
            has_valid_timestamp = "ts" in resolved
            has_weather_data = any(field in resolved for field in ["temp", "humidity", "wind"])
            
            if not has_valid_timestamp or not has_weather_data:
                return ImportResult.failure(["No valid weather data found"])
            
            # Process rows to create weather points
            weather_points = []
            
            for row_num, row in enumerate(rows, 1):
                try:
                    weather_point, row_warnings = cls._process_row(row, session_id, row_num)
                    if weather_point:
                        weather_points.append(weather_point)
                    warnings.extend(row_warnings)
                except Exception as e:
                    warnings.append(f"Row {row_num}: Error processing row: {e}")
                    continue
            
            if not weather_points:
                return ImportResult.failure(["No valid weather data found"])
            
            # Create session and bundle
            session = Session(
                id=session_id,
                source="weather_csv",
                track_id="unknown",  # Will be updated by other importers
            )
            
            bundle = SessionBundle(
                session=session,
                weather=weather_points
            )
            
            return ImportResult.success(bundle, warnings)
            
        except Exception as e:
            return ImportResult.failure([f"Error processing weather CSV: {str(e)}"])
    
    @classmethod
    def _process_row(cls, row: Dict[str, str], session_id: str, row_num: int) -> tuple[WeatherPoint | None, List[str]]:
        """Process a single weather data row."""
        warnings = []
        
        # Get all headers from the row
        headers = list(row.keys())
        
        # Resolve column mappings with aliases
        resolved = cls.resolve_weather_columns(headers)
        
        # Process timestamp
        if "ts" not in resolved:
            warnings.append("Missing timestamp")
            return None, warnings
        
        ts_info = resolved["ts"]
        ts_raw = row[ts_info["header"]].strip()
        if not ts_raw:
            warnings.append("Missing timestamp")
            return None, warnings
        
        ts_value = coerce_float(ts_raw)
        if ts_value is None:
            warnings.append("Invalid timestamp")
            return None, warnings
        
        # Apply timestamp conversion
        if ts_info["conversion"] == "seconds_to_ms":
            ts_ms = int(ts_value * 1000)
        elif ts_info["conversion"] == "none":
            ts_ms = int(ts_value)
        else:
            warnings.append(f"Unknown timestamp conversion: {ts_info['conversion']}")
            return None, warnings
        
        # Extract and convert weather fields
        air_temp_c = None
        track_temp_c = None
        humidity_pct = None
        pressure_hpa = None
        wind_speed = None
        wind_dir_deg = None
        rain_flag = None
        
        # Temperature
        if "temp" in resolved:
            temp_info = resolved["temp"]
            temp_raw = row[temp_info["header"]].strip()
            air_temp_c = coerce_float(temp_raw)
        
        # Track temperature (if available)
        track_temp_headers = ['TRACK_TEMP', 'TRACK_TEMPERATURE']
        for header in track_temp_headers:
            if header in row:
                track_temp_raw = row[header].strip()
                track_temp_c = coerce_float(track_temp_raw)
                break
        
        # Humidity
        if "humidity" in resolved:
            humidity_info = resolved["humidity"]
            humidity_raw = row[humidity_info["header"]].strip()
            humidity_pct = coerce_float(humidity_raw)
        
        # Pressure (if available)
        pressure_headers = ['PRESSURE', 'PRESSURE_HPA']
        for header in pressure_headers:
            if header in row:
                pressure_raw = row[header].strip()
                pressure_hpa = coerce_float(pressure_raw)
                break
        
        # Wind speed with conversion
        if "wind" in resolved:
            wind_info = resolved["wind"]
            wind_raw = row[wind_info["header"]].strip()
            wind_value = coerce_float(wind_raw)
            if wind_value is not None:
                if wind_info["conversion"] == "mps_to_kph":
                    wind_speed = wind_value * 3.6  # Convert m/s to kph
                elif wind_info["conversion"] == "none":
                    wind_speed = wind_value
                else:
                    warnings.append(f"Unknown wind conversion: {wind_info['conversion']}")
        
        # Wind direction (if available)
        wind_dir_headers = ['WIND_DIRECTION', 'WIND_DIR']
        for header in wind_dir_headers:
            if header in row:
                wind_dir_raw = row[header].strip()
                wind_dir_deg = coerce_float(wind_dir_raw)
                break
        
        # Rain flag (if available)
        rain_headers = ['RAIN', 'RAIN_FLAG']
        for header in rain_headers:
            if header in row:
                rain_raw = row[header].strip()
                rain_flag = coerce_int(rain_raw)
                break
        
        # Convert and validate fields
        weather_data = {
            'session_id': session_id,
            'ts_ms': ts_ms,
            'air_temp_c': air_temp_c,
            'track_temp_c': track_temp_c,
            'humidity_pct': humidity_pct,
            'pressure_hpa': pressure_hpa,
            'wind_speed': wind_speed,
            'wind_dir_deg': wind_dir_deg,
            'rain_flag': rain_flag
        }
        
        # Validate ranges and add warnings if needed
        cls._validate_weather_data(weather_data, row_num, warnings)
        
        # Create weather point
        weather_point = WeatherPoint(**weather_data)
        return weather_point, warnings
    
    @classmethod
    def _find_header_value(cls, row: Dict[str, str], possible_headers: List[str]) -> str:
        """Find value in row using possible header names."""
        for header in possible_headers:
            if header in row:
                value = row[header].strip()
                if value:
                    return value
        return ''
    
    @classmethod
    def _validate_weather_data(cls, weather_data: Dict, row_num: int, warnings: List[str]):
        """Validate weather data ranges and add warnings."""
        # Temperature validation (reasonable ranges)
        if weather_data['air_temp_c'] is not None:
            if not -50 <= weather_data['air_temp_c'] <= 60:
                warnings.append(f"Row {row_num}: Air temperature {weather_data['air_temp_c']}°C outside reasonable range")
        
        if weather_data['track_temp_c'] is not None:
            if not -50 <= weather_data['track_temp_c'] <= 80:
                warnings.append(f"Row {row_num}: Track temperature {weather_data['track_temp_c']}°C outside reasonable range")
        
        # Humidity validation (0-100%)
        if weather_data['humidity_pct'] is not None:
            if not 0 <= weather_data['humidity_pct'] <= 100:
                warnings.append(f"Row {row_num}: Humidity {weather_data['humidity_pct']}% outside 0-100% range")
        
        # Pressure validation (reasonable atmospheric pressure range)
        if weather_data['pressure_hpa'] is not None:
            if not 800 <= weather_data['pressure_hpa'] <= 1200:
                warnings.append(f"Row {row_num}: Pressure {weather_data['pressure_hpa']} hPa outside reasonable range")
        
        # Wind speed validation (0-200 km/h)
        if weather_data['wind_speed'] is not None:
            if weather_data['wind_speed'] < 0:
                warnings.append(f"Row {row_num}: Wind speed cannot be negative")
            elif weather_data['wind_speed'] > 200:
                warnings.append(f"Row {row_num}: Wind speed {weather_data['wind_speed']} km/h outside reasonable range")
        
        # Wind direction validation (0-360 degrees)
        if weather_data['wind_dir_deg'] is not None:
            if not 0 <= weather_data['wind_dir_deg'] <= 360:
                warnings.append(f"Row {row_num}: Wind direction {weather_data['wind_dir_deg']}° outside 0-360° range")
        
        # Rain flag validation (0 or 1)
        if weather_data['rain_flag'] is not None:
            if weather_data['rain_flag'] not in [0, 1]:
                warnings.append(f"Row {row_num}: Rain flag should be 0 or 1, got {weather_data['rain_flag']}")
    
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
    def resolve_weather_columns(cls, headers: list[str]) -> dict:
        """
        Resolve weather CSV headers to standardized field names with alias support.
        
        Args:
            headers: List of CSV header names
            
        Returns:
            dict: Maps standardized field names to actual header names and conversion info
                Format: {
                    "ts": {"header": "actual_header", "conversion": "seconds_to_ms"},
                    "temp": {"header": "actual_header", "conversion": "none"},
                    "humidity": {"header": "actual_header", "conversion": "none"},
                    "wind": {"header": "actual_header", "conversion": "mps_to_kph"}
                }
        """
        # Define all supported aliases for each field
        alias_map = {
            "ts": ["ts_ms", "utc", "utc_seconds", "timestamp", "time_s", "time_ms", "TIME_UTC_SECONDS", "TIME", "TIMESTAMP"],
            "temp": ["temp", "temp_c", "temperature", "air_temp_c", "AIR_TEMP", "AIR_TEMPERATURE"],
            "humidity": ["humidity", "humidity_pct", "rh", "relative_humidity", "HUMIDITY", "HUMIDITY_PCT"],
            "wind": ["wind", "wind_kph", "wind_speed_kph", "wind_mps", "WIND_SPEED", "WIND"]
        }
        
        # Define conversions needed for each alias
        conversion_map = {
            "ts_ms": "none",
            "utc": "seconds_to_ms",
            "utc_seconds": "seconds_to_ms",
            "timestamp": "seconds_to_ms",
            "time_s": "seconds_to_ms",
            "time_ms": "none",
            "TIME_UTC_SECONDS": "seconds_to_ms",
            "TIME": "seconds_to_ms",
            "TIMESTAMP": "seconds_to_ms",
            "temp": "none",
            "temp_c": "none",
            "temperature": "none",
            "air_temp_c": "none",
            "AIR_TEMP": "none",
            "AIR_TEMPERATURE": "none",
            "humidity": "none",
            "humidity_pct": "none",
            "rh": "none",
            "relative_humidity": "none",
            "HUMIDITY": "none",
            "HUMIDITY_PCT": "none",
            "wind": "none",
            "wind_kph": "none",
            "wind_speed_kph": "none",
            "wind_mps": "mps_to_kph",
            "WIND_SPEED": "none",
            "WIND": "none"
        }
        
        result = {}
        
        # For each field type, find the matching header
        for field_type, aliases in alias_map.items():
            for alias in aliases:
                # Case-insensitive matching
                matching_headers = [h for h in headers if h.lower() == alias.lower()]
                if matching_headers:
                    # Use the first match
                    actual_header = matching_headers[0]
                    conversion = conversion_map.get(alias, "none")
                    result[field_type] = {
                        "header": actual_header,
                        "conversion": conversion
                    }
                    break
        
        return result
    
    @classmethod
    def resolve_columns(cls, headers: list[str]) -> tuple[dict, list[str]]:
        """
        Resolve weather CSV headers to standardized field names.
        
        Args:
            headers: List of CSV header names
            
        Returns:
            tuple: (mapping_dict, reasons_list)
                mapping_dict: Maps standardized field names to actual header names
                reasons_list: List of strings explaining why each field was recognized
        """
        mapping = {}
        reasons = []
        
        # Use the new resolve_weather_columns function
        resolved = cls.resolve_weather_columns(headers)
        
        # Convert to the old format for backward compatibility
        for field_type, info in resolved.items():
            mapping[field_type] = info["header"]
            reasons.append(f"Weather field '{field_type}' found: '{info['header']}' with conversion '{info['conversion']}'")
        
        # Add missing field reasons
        if "ts" not in resolved:
            reasons.append("No timestamp field found among expected: ts_ms, utc, utc_seconds, timestamp, time_s, time_ms")
        if "temp" not in resolved:
            reasons.append("No temperature field found among expected: temp, temp_c, temperature, air_temp_c")
        if "humidity" not in resolved:
            reasons.append("No humidity field found among expected: humidity, humidity_pct, rh, relative_humidity")
        if "wind" not in resolved:
            reasons.append("No wind field found among expected: wind, wind_kph, wind_speed_kph, wind_mps")
        
        return mapping, reasons
    
    @classmethod
    def inspect_text(cls, text: str) -> Dict[str, Any]:
        """
        Inspect weather CSV text to analyze headers and data structure.
        
        Args:
            text: CSV text content to inspect
            
        Returns:
            Dictionary with inspection results including headers, mapping, and reasons
        """
        import io
        from typing import Any, Dict, Set
        
        # Auto-detect delimiter
        delimiter = cls._detect_delimiter(text)
        
        # Read CSV data
        text_io = io.StringIO(text)
        reader = csv.DictReader(text_io, delimiter=delimiter)
        rows = list(reader)
        
        # Get field names from CSV
        headers = reader.fieldnames or []
        
        # Resolve columns using the new function
        resolved = cls.resolve_weather_columns(headers)
        
        # Convert to the expected format for the API
        recognized = {}
        for field_type, info in resolved.items():
            # Map to the standardized field names expected by the API
            if field_type == "ts":
                recognized["ts"] = "ts_ms"  # Standardize to ts_ms
            elif field_type == "temp":
                recognized["temp"] = "temp_c"  # Standardize to temp_c
            elif field_type == "humidity":
                recognized["humidity"] = "humidity_pct"  # Standardize to humidity_pct
            elif field_type == "wind":
                recognized["wind"] = "wind_kph"  # Standardize to wind_kph
        
        # Generate reasons
        reasons = []
        for field_type, info in resolved.items():
            reasons.append(f"Weather field '{field_type}' found: '{info['header']}' with conversion '{info['conversion']}'")
        
        # Add missing field reasons
        if "ts" not in resolved:
            reasons.append("No timestamp field found among expected: ts_ms, utc, utc_seconds, timestamp, time_s, time_ms")
        if "temp" not in resolved:
            reasons.append("No temperature field found among expected: temp, temp_c, temperature, air_temp_c")
        if "humidity" not in resolved:
            reasons.append("No humidity field found among expected: humidity, humidity_pct, rh, relative_humidity")
        if "wind" not in resolved:
            reasons.append("No wind field found among expected: wind, wind_kph, wind_speed_kph, wind_mps")
        
        # Count unique timestamps if timestamp field is found
        timestamps = 0
        if 'ts' in resolved:
            timestamp_field = resolved['ts']['header']
            unique_timestamps: Set[str] = set()
            for row in rows:
                ts_value = row.get(timestamp_field, '').strip()
                if ts_value:
                    unique_timestamps.add(ts_value)
            timestamps = len(unique_timestamps)
        
        return {
            "header": headers,
            "recognized": recognized,
            "reasons": reasons,
            "rows_total": len(rows),
            "timestamps": timestamps
        }