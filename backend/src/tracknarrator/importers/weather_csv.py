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
            
            # Check if we have any valid weather headers
            fieldnames = reader.fieldnames or []
            has_valid_timestamp = any(
                header in fieldnames for header in ['TIME_UTC_SECONDS', 'TIME', 'TIMESTAMP']
            )
            
            # Also check for at least one weather data field
            weather_fields = ['AIR_TEMP', 'AIR_TEMPERATURE', 'TRACK_TEMP', 'TRACK_TEMPERATURE',
                          'HUMIDITY', 'HUMIDITY_PCT', 'PRESSURE', 'PRESSURE_HPA',
                          'WIND_SPEED', 'WIND', 'WIND_DIRECTION', 'WIND_DIR',
                          'RAIN', 'RAIN_FLAG']
            has_weather_data = any(
                header in fieldnames for header in weather_fields
            )
            
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
        
        # Get timestamp in seconds
        ts_seconds_raw = cls._find_header_value(row, ['TIME_UTC_SECONDS', 'TIME', 'TIMESTAMP'])
        if not ts_seconds_raw:
            warnings.append("Missing timestamp")
            return None, warnings
        
        ts_seconds = coerce_float(ts_seconds_raw)
        if ts_seconds is None:
            warnings.append("Invalid timestamp")
            return None, warnings
        
        # Convert to milliseconds
        ts_ms = int(ts_seconds * 1000)
        
        # Extract weather fields
        air_temp_c = cls._find_header_value(row, ['AIR_TEMP', 'AIR_TEMPERATURE'])
        track_temp_c = cls._find_header_value(row, ['TRACK_TEMP', 'TRACK_TEMPERATURE'])
        humidity_pct = cls._find_header_value(row, ['HUMIDITY', 'HUMIDITY_PCT'])
        pressure_hpa = cls._find_header_value(row, ['PRESSURE', 'PRESSURE_HPA'])
        wind_speed = cls._find_header_value(row, ['WIND_SPEED', 'WIND'])
        wind_dir_deg = cls._find_header_value(row, ['WIND_DIRECTION', 'WIND_DIR'])
        rain_flag = cls._find_header_value(row, ['RAIN', 'RAIN_FLAG'])
        
        # Convert and validate fields
        weather_data = {
            'session_id': session_id,
            'ts_ms': ts_ms,
            'air_temp_c': coerce_float(air_temp_c),
            'track_temp_c': coerce_float(track_temp_c),
            'humidity_pct': coerce_float(humidity_pct),
            'pressure_hpa': coerce_float(pressure_hpa),
            'wind_speed': coerce_float(wind_speed),
            'wind_dir_deg': coerce_float(wind_dir_deg),
            'rain_flag': coerce_int(rain_flag)
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
        
        # Check for timestamp field
        timestamp_field = None
        for ts_field in ['TIME_UTC_SECONDS', 'TIME', 'TIMESTAMP', 'ts_ms', 'UTC']:
            if ts_field in headers:
                timestamp_field = ts_field
                mapping['ts'] = ts_field
                reasons.append(f"Timestamp field found: '{ts_field}' mapped to 'ts'")
                break
        
        if not timestamp_field:
            reasons.append("No timestamp field found among expected: TIME_UTC_SECONDS, TIME, TIMESTAMP, ts_ms, UTC")
        
        # Check for weather data fields
        weather_field_mapping = {
            'temp': ['AIR_TEMP', 'AIR_TEMPERATURE'],
            'humidity': ['HUMIDITY', 'HUMIDITY_PCT'],
            'wind': ['WIND_SPEED', 'WIND']
        }
        
        for field_key, possible_headers in weather_field_mapping.items():
            found = False
            for header in possible_headers:
                if header in headers:
                    mapping[field_key] = header
                    reasons.append(f"Weather field '{field_key}' found: '{header}'")
                    found = True
                    break
            
            if not found:
                reasons.append(f"Weather field '{field_key}' not found among expected: {', '.join(possible_headers)}")
        
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
        mapping, reasons = cls.resolve_columns(headers)
        
        # Count unique timestamps if timestamp field is found
        timestamps = 0
        if 'ts' in mapping:
            timestamp_field = mapping['ts']
            unique_timestamps: Set[str] = set()
            for row in rows:
                ts_value = row.get(timestamp_field, '').strip()
                if ts_value:
                    unique_timestamps.add(ts_value)
            timestamps = len(unique_timestamps)
        
        return {
            "header": headers,
            "recognized": mapping,
            "reasons": reasons,
            "rows_total": len(rows),
            "timestamps": timestamps
        }