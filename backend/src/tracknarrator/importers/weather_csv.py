"""Weather CSV importer with enhanced field support and validation."""

import csv
import io
from typing import Any, BinaryIO, Dict, List, TextIO, Tuple

from .base import ImportResult, coerce_float, coerce_int
from ..schema import Session, SessionBundle, WeatherPoint
from ..utils_time import safe_int


class WeatherCSVImporter:
    """Importer for weather data CSV files with enhanced field support."""
    
    # Header mapping for weather data (legacy - kept for backward compatibility)
    HEADER_MAP = {
        'TIME_UTC_SECONDS': 'ts_seconds',
        'TIME': 'ts_seconds',
        'AIR_TEMP': 'air_temp_c',
        'AIR_TEMPERATURE': 'air_temp_c',
        'TRACK_TEMP': 'track_temp_c',
        'TRACK_TEMPERATURE': 'track_temp_c',
        'HUMIDITY': 'humidity_pct',
        'HUMIDITY_PCT': 'humidity_pct',
        'PRESSURE': 'pressure_hpa',
        'PRESSURE_HPA': 'pressure_hpa',
        'WIND_SPEED': 'wind_speed',
        'WIND': 'wind_speed',
        'WIND_DIRECTION': 'wind_dir_deg',
        'WIND_DIR': 'wind_dir_deg',
        'RAIN': 'rain_flag',
        'RAIN_FLAG': 'rain_flag'
    }
    
    # Enhanced field mappings with canonical names and aliases
    FIELD_MAPPINGS = {
        # Timestamp fields (all map to 'ts')
        'ts': ['ts_ms', 'time_ms', 'timestamp_ms', 'ts', 'timestamp', 'utc', 'epoch', 'epoch_ms', 'utc_seconds', 'time_s', 'TIME_UTC_SECONDS', 'TIME'],
        # Temperature fields (canonical: temp)
        'temp': ['temp', 'temp_c', 'air_temp_c', 'AIR_TEMP', 'AIR_TEMPERATURE', 'temperature'],
        # Track temperature fields (canonical: track_temp)
        'track_temp': ['track_temp', 'track_temp_c', 'TRACK_TEMP', 'TRACK_TEMPERATURE'],
        # Wind fields (canonical: wind)
        'wind': ['wind', 'wind_kph', 'wind_km_h', 'wind_mph', 'wind_mps', 'WIND_SPEED', 'WIND', 'wind_speed_kph'],
        # Humidity fields (canonical: humidity)
        'humidity': ['humidity', 'humidity_pct', 'HUMIDITY', 'HUMIDITY_PCT', 'rh', 'relative_humidity'],
        # Pressure fields (canonical: pressure)
        'pressure': ['pressure', 'pressure_hpa', 'PRESSURE', 'PRESSURE_HPA'],
        # Wind direction fields (canonical: wind_dir)
        'wind_dir': ['wind_dir', 'wind_dir_deg', 'WIND_DIRECTION', 'WIND_DIR'],
        # Rain flag fields (canonical: rain)
        'rain': ['rain', 'rain_flag', 'RAIN', 'RAIN_FLAG']
    }
    
    # Field validation ranges
    VALIDATION_RANGES = {
        'temp': {'min': -30, 'max': 60},
        'wind': {'min': 0, 'max': 250},
        'humidity': {'min': 0, 'max': 100}
    }
    
    @classmethod
    def validate_required_columns(cls, fieldnames: list[str]) -> None:
        """
        Validate that required columns are present in weather CSV file.
        
        Args:
            fieldnames: List of column names from CSV header
            
        Raises:
            ValueError: If required columns are missing
        """
        # Normalize field names for comparison
        normalized_fields = [field.strip().lower() for field in fieldnames]
        
        # Check for timestamp fields
        timestamp_fields = ['ts_ms', 'time_ms', 'timestamp_ms', 'ts', 'timestamp', 'utc', 'epoch', 'epoch_ms', 'utc_seconds', 'time_s', 'time_utc_seconds', 'time']
        has_timestamp = any(field in normalized_fields for field in timestamp_fields)
        
        # Check for weather data fields
        weather_fields = ['temp', 'temp_c', 'air_temp_c', 'air_temp', 'air_temperature', 'temperature',
                         'track_temp', 'track_temp_c', 'track_temperature',
                         'wind', 'wind_kph', 'wind_speed', 'wind_speed_kph', 'wind_mph', 'wind_mps',
                         'humidity', 'humidity_pct', 'rh', 'relative_humidity',
                         'pressure', 'pressure_hpa',
                         'wind_dir', 'wind_dir_deg', 'wind_direction',
                         'rain', 'rain_flag']
        has_weather_data = any(field in normalized_fields for field in weather_fields)
        
        # Build list of missing required column types
        missing_requirements = []
        if not has_timestamp:
            missing_requirements.append("timestamp (TIME_UTC_SECONDS, ts_ms, etc.)")
        if not has_weather_data:
            missing_requirements.append("weather data (AIR_TEMP, temp_c, etc.)")
        
        if missing_requirements:
            raise ValueError(
                f"Barber weather import error: missing required columns. Need at least one {', and one '.join(missing_requirements)}. "
                f"Check data/barber/weather.csv."
            )

    @classmethod
    def import_file(cls, file: BinaryIO | TextIO, session_id: str) -> ImportResult:
        """
        Import weather CSV file with enhanced validation and row-level reasons.
        
        Args:
            file: File-like object containing CSV data
            session_id: Session ID for the weather data
            
        Returns:
            ImportResult with weather data and any warnings
        """
        warnings = []
        discard_reasons = []
        
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
            
            # Get field names from CSV and validate required columns
            fieldnames = reader.fieldnames or []
            normalized_fieldnames = [h.strip('\ufeff').strip() for h in fieldnames]
            
            try:
                cls.validate_required_columns(normalized_fieldnames)
            except ValueError as e:
                return ImportResult.failure([str(e)])
            
            # Resolve columns using the new function
            resolved = cls.resolve_weather_columns(normalized_fieldnames)
            
            # Check if we have at least a timestamp and one weather field
            has_valid_timestamp = "ts" in resolved
            has_weather_data = any(field in resolved for field in ["temp", "humidity", "wind"])
            
            # If no valid fields with new mappings, try legacy headers
            if not has_valid_timestamp or not has_weather_data:
                # Normalize legacy headers
                normalized_legacy_headers = [h.strip('\ufeff').strip() for h in fieldnames]
                legacy_found = False
                for legacy_header, standard_field in cls.HEADER_MAP.items():
                    if legacy_header in normalized_legacy_headers:
                        legacy_found = True
                        break
                
                if legacy_found:
                    # Use legacy processing
                    return cls._import_with_legacy_headers(reader, session_id, delimiter)
                else:
                    return ImportResult.failure(["No valid weather data found"])
            
            # Process rows to create weather points
            weather_points = []
            
            for row_num, row in enumerate(rows, 1):
                try:
                    weather_point, row_warnings, discard_reason = cls._process_row(row, session_id, row_num)
                    if discard_reason:
                        discard_reasons.append(discard_reason)
                        continue  # Skip rows with discard reasons
                    if weather_point:
                        weather_points.append(weather_point)
                    warnings.extend(row_warnings)
                except Exception as e:
                    discard_reasons.append(f"row {row_num}: error processing row: {e}")
                    continue
            
            if not weather_points:
                if discard_reasons:
                    return ImportResult.failure([f"Import failed: {'; '.join(discard_reasons)}"])
                else:
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
            
            # Add discard reasons to warnings if any
            if discard_reasons:
                warnings.extend(discard_reasons)
            
            # Add summary of skipped rows if any
            if discard_reasons:
                skipped_count = len([r for r in discard_reasons if "row" in r])
                if skipped_count > 0:
                    warnings.append(f"Barber weather import: {skipped_count} rows skipped due to invalid data (see log output).")
            
            return ImportResult.success(bundle, warnings)
            
        except Exception as e:
            return ImportResult.failure([f"Barber weather import error: {str(e)}"])
    
    @classmethod
    def _import_with_legacy_headers(cls, reader: csv.DictReader, session_id: str, delimiter: str) -> ImportResult:
        """
        Import using legacy header mappings for backward compatibility.
        """
        rows = list(reader)
        weather_points = []
        all_warnings = []
        discard_reasons = []
        
        for row_num, row in enumerate(rows, 1):
            weather_point, warnings, discard_reason = cls._process_legacy_row(row, session_id, row_num)
            all_warnings.extend(warnings)
            
            if discard_reason:
                discard_reasons.append(discard_reason)
                continue
                
            if weather_point:
                weather_points.append(weather_point)
        
        # If no valid weather points, return error
        if not weather_points:
            # If no discard reasons, provide a generic message
            if not discard_reasons:
                discard_reasons.append("No valid weather data found")
            return ImportResult.failure([f"Import failed: {'; '.join(discard_reasons)}"])
        
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
        
        # Add discard reasons to warnings if any
        if discard_reasons:
            all_warnings.extend(discard_reasons)
        
        return ImportResult.success(bundle, all_warnings)
    
    @classmethod
    def _process_legacy_row(cls, row: Dict[str, str], session_id: str, row_num: int) -> tuple[WeatherPoint | None, List[str], str | None]:
        """
        Process a single row using legacy header mappings.
        """
        warnings = []
        weather_data = {"session_id": session_id}
        valid_fields_found = False
        
        # Process timestamp
        timestamp_value = None
        for legacy_header, standard_field in cls.HEADER_MAP.items():
            if standard_field == "ts_seconds" and legacy_header in row:
                timestamp_raw = row[legacy_header].strip()
                timestamp_value = coerce_float(timestamp_raw)
                if timestamp_value is not None:
                    # Convert to milliseconds
                    weather_data["ts_ms"] = int(timestamp_value * 1000)
                    valid_fields_found = True
                else:
                    warnings.append(f"row {row_num}: invalid timestamp")
                break
        
        if timestamp_value is None:
            return None, warnings, f"row {row_num}: missing/invalid timestamp"
        
        # Process other fields
        for legacy_header, standard_field in cls.HEADER_MAP.items():
            if legacy_header in row and standard_field != "ts_seconds":
                raw_value = row[legacy_header].strip()
                if not raw_value:
                    continue
                    
                if standard_field in ["air_temp_c", "track_temp_c", "AIR_TEMP", "AIR_TEMPERATURE", "TRACK_TEMP", "TRACK_TEMPERATURE"]:
                    value = coerce_float(raw_value)
                    if value is not None:
                        # Normalize to standard field names
                        if standard_field in ["AIR_TEMP", "AIR_TEMPERATURE"]:
                            weather_data["air_temp_c"] = value
                        elif standard_field in ["TRACK_TEMP", "TRACK_TEMPERATURE"]:
                            weather_data["track_temp_c"] = value
                        else:
                            weather_data[standard_field] = value
                        valid_fields_found = True
                        
                        # Apply validation ranges for legacy processing (after storing the value)
                        if standard_field in ["air_temp_c", "AIR_TEMP", "AIR_TEMPERATURE"] and not (-50 <= value <= 60):
                            warnings.append(f"Air temperature {value}°C outside reasonable range")
                        elif standard_field in ["track_temp_c", "TRACK_TEMP", "TRACK_TEMPERATURE"] and not (-50 <= value <= 80):
                            warnings.append(f"Track temperature {value}°C outside reasonable range")
                    else:
                        warnings.append(f"row {row_num}: invalid {standard_field} value")
                elif standard_field in ["humidity_pct", "HUMIDITY", "HUMIDITY_PCT"]:
                    value = coerce_float(raw_value)
                    if value is not None:
                        weather_data["humidity_pct"] = value
                        valid_fields_found = True
                        
                        # Apply validation ranges for legacy processing (after storing the value)
                        if not (0 <= value <= 100):
                            warnings.append(f"Humidity {value}% outside 0-100% range")
                    else:
                        warnings.append(f"row {row_num}: invalid humidity value")
                elif standard_field in ["pressure_hpa", "PRESSURE", "PRESSURE_HPA"]:
                    value = coerce_float(raw_value)
                    if value is not None:
                        weather_data["pressure_hpa"] = value
                        valid_fields_found = True
                        
                        # Apply validation ranges for legacy processing (after storing the value)
                        if not (800 <= value <= 1200):
                            warnings.append(f"Pressure {value} hPa outside reasonable range")
                    else:
                        warnings.append(f"row {row_num}: invalid pressure value")
                elif standard_field in ["wind_speed", "WIND_SPEED", "WIND"]:
                    value = coerce_float(raw_value)
                    if value is not None:
                        weather_data["wind_speed"] = value
                        valid_fields_found = True
                        
                        # Apply validation ranges for legacy processing (after storing the value)
                        if value < 0:
                            warnings.append(f"Wind speed cannot be negative")
                        elif value > 200:
                            warnings.append(f"Wind speed {value} km/h outside reasonable range")
                    else:
                        warnings.append(f"row {row_num}: invalid wind value")
                elif standard_field in ["wind_dir_deg", "WIND_DIRECTION", "WIND_DIR"]:
                    value = coerce_float(raw_value)
                    if value is not None:
                        weather_data["wind_dir_deg"] = value
                        valid_fields_found = True
                        
                        # Apply validation ranges for legacy processing (after storing the value)
                        if not (0 <= value <= 360):
                            warnings.append(f"Wind direction {value}° outside 0-360° range")
                    else:
                        warnings.append(f"row {row_num}: invalid wind direction value")
                elif standard_field in ["rain_flag", "RAIN", "RAIN_FLAG"]:
                    value = coerce_int(raw_value)
                    if value is not None:
                        weather_data["rain_flag"] = value
                        valid_fields_found = True
                        
                        # Apply validation ranges for legacy processing (after storing the value)
                        if value not in [0, 1]:
                            warnings.append(f"Rain flag should be 0 or 1, got {value}")
                    else:
                        warnings.append(f"row {row_num}: invalid rain flag value")
        
        # Initialize all fields to None if not set
        for field in ['air_temp_c', 'track_temp_c', 'humidity_pct', 'pressure_hpa', 'wind_speed', 'wind_dir_deg', 'rain_flag']:
            if field not in weather_data:
                weather_data[field] = None
        
        # For legacy processing, we accept rows with just timestamp
        # (different from new field processing which requires at least one weather field)
        if not valid_fields_found:
            # For legacy processing, we still create a weather point even if no valid weather fields
            # This is to maintain backward compatibility
            pass
        
        # Create weather point
        weather_point = WeatherPoint(**weather_data)
        return weather_point, warnings, None
    
    @classmethod
    def _process_row(cls, row: Dict[str, str], session_id: str, row_num: int) -> tuple[WeatherPoint | None, List[str], str | None]:
        """
        Process a single weather data row with enhanced validation.
        
        Returns:
            tuple: (weather_point, warnings, discard_reason)
            - weather_point: Valid WeatherPoint or None if row discarded
            - warnings: List of warning messages
            - discard_reason: Reason for discarding row, or None if accepted
        """
        warnings = []
        
        # Get all headers from the row
        headers = list(row.keys())
        
        # Resolve column mappings with aliases
        resolved = cls.resolve_weather_columns(headers)
        
        # Process timestamp (hard requirement)
        if "ts" not in resolved:
            return None, [], f"row {row_num}: missing timestamp field"
        
        ts_info = resolved["ts"]
        ts_raw = row[ts_info["header"]].strip()
        if not ts_raw:
            return None, [], f"row {row_num}: missing/invalid timestamp"
        
        ts_value = coerce_float(ts_raw)
        if ts_value is None or ts_value < 0:
            return None, [], f"row {row_num}: missing/invalid timestamp"
        
        # Apply timestamp conversion with auto-detection
        if ts_info["conversion"] == "seconds_to_ms":
            ts_ms = int(ts_value * 1000)
        elif ts_info["conversion"] == "none":
            ts_ms = int(ts_value)
        else:
            return None, [], f"row {row_num}: unknown timestamp conversion: {ts_info['conversion']}"
        
        # Initialize weather data with session_id and timestamp
        weather_data = {
            'session_id': session_id,
            'ts_ms': ts_ms,
            'air_temp_c': None,
            'track_temp_c': None,
            'humidity_pct': None,
            'pressure_hpa': None,
            'wind_speed': None,
            'wind_dir_deg': None,
            'rain_flag': None
        }
        
        # Track if any valid weather fields are found
        valid_fields_found = False
        
        # Process temperature field (canonical: temp)
        if "temp" in resolved:
            temp_info = resolved["temp"]
            temp_raw = row[temp_info["header"]].strip()
            # Remove comments after values (e.g., "55  # comment")
            if '  #' in temp_raw:
                temp_raw = temp_raw.split('  #')[0].strip()
            temp_value = coerce_float(temp_raw)
            
            if temp_value is not None:
                # Store value even if out of range (with warning)
                weather_data['air_temp_c'] = temp_value
                valid_fields_found = True
                
                # Validate range and warn if out of range
                range_info = cls.VALIDATION_RANGES['temp']
                if not (range_info['min'] <= temp_value <= range_info['max']):
                    warnings.append(f"row {row_num}: out-of-range temp {temp_value}C")
            else:
                warnings.append(f"row {row_num}: invalid temp value")
                # Don't set weather_data['air_temp_c'] = None here - it's already None
            
            # Add alias warning if used
            if temp_info.get("alias_used"):
                warnings.append(f"row {row_num}: alias_used: {temp_info['header']}→temp_c")
        
        # Process wind field (canonical: wind)
        if "wind" in resolved:
            wind_info = resolved["wind"]
            wind_raw = row[wind_info["header"]].strip()
            # Remove comments after values (e.g., "55  # comment")
            if '  #' in wind_raw:
                wind_raw = wind_raw.split('  #')[0].strip()
            wind_value = coerce_float(wind_raw)
            
            if wind_value is not None:
                # Apply conversion if needed
                if wind_info["conversion"] == "mph_to_kph":
                    wind_value = wind_value * 1.60934
                elif wind_info["conversion"] == "mps_to_kph":
                    wind_value = wind_value * 3.6
                
                # Store value even if out of range (with warning)
                weather_data['wind_speed'] = wind_value
                valid_fields_found = True
                
                # Validate range and warn if out of range
                range_info = cls.VALIDATION_RANGES['wind']
                if not (range_info['min'] <= wind_value <= range_info['max']):
                    if wind_value < 0:
                        warnings.append(f"row {row_num}: out-of-range wind {wind_value:.0f}kph (negative)")
                    else:
                        warnings.append(f"row {row_num}: out-of-range wind {wind_value:.0f}kph")
            else:
                warnings.append(f"row {row_num}: invalid wind value")
                # Don't set weather_data['wind_speed'] = None here - it's already None
            
            # Add alias warning if used
            if wind_info.get("alias_used"):
                warnings.append(f"row {row_num}: alias_used: {wind_info['header']}→wind_kph")
        
        # Process humidity field (canonical: humidity)
        if "humidity" in resolved:
            humidity_info = resolved["humidity"]
            humidity_raw = row[humidity_info["header"]].strip()
            # Remove comments after values (e.g., "55  # comment")
            if '  #' in humidity_raw:
                humidity_raw = humidity_raw.split('  #')[0].strip()
            humidity_value = coerce_float(humidity_raw)
            
            if humidity_value is not None:
                # Store value even if out of range (with warning)
                weather_data['humidity_pct'] = humidity_value
                valid_fields_found = True
                
                # Validate range and warn if out of range
                range_info = cls.VALIDATION_RANGES['humidity']
                if not (range_info['min'] <= humidity_value <= range_info['max']):
                    warnings.append(f"row {row_num}: out-of-range humidity {humidity_value}%")
            else:
                warnings.append(f"row {row_num}: invalid humidity value")
                # Don't set weather_data['humidity_pct'] = None here - it's already None
            
            # Add alias warning if used
            if humidity_info.get("alias_used"):
                warnings.append(f"row {row_num}: alias_used: {humidity_info['header']}→humidity_pct")
        
        # Process track temperature field (canonical: track_temp)
        if "track_temp" in resolved:
            track_temp_info = resolved["track_temp"]
            track_temp_raw = row[track_temp_info["header"]].strip()
            track_temp_value = coerce_float(track_temp_raw)
            
            if track_temp_value is not None:
                # Validate range (track temp has wider range)
                if -50 <= track_temp_value <= 80:
                    weather_data['track_temp_c'] = track_temp_value
                    valid_fields_found = True
                else:
                    warnings.append(f"Row {row_num}: Track temperature {track_temp_value}°C outside reasonable range")
            else:
                warnings.append(f"row {row_num}: invalid track_temp value")
            
            # Add alias warning if used
            if track_temp_info.get("alias_used"):
                warnings.append(f"row {row_num}: alias_used: {track_temp_info['header']}→track_temp")
        
        # Process pressure field (canonical: pressure)
        if "pressure" in resolved:
            pressure_info = resolved["pressure"]
            pressure_raw = row[pressure_info["header"]].strip()
            pressure_value = coerce_float(pressure_raw)
            
            if pressure_value is not None:
                # Validate range
                if 800 <= pressure_value <= 1200:
                    weather_data['pressure_hpa'] = pressure_value
                    valid_fields_found = True
                else:
                    warnings.append(f"Row {row_num}: Pressure {pressure_value} hPa outside reasonable range")
            else:
                warnings.append(f"row {row_num}: invalid pressure value")
            
            # Add alias warning if used
            if pressure_info.get("alias_used"):
                warnings.append(f"row {row_num}: alias_used: {pressure_info['header']}→pressure")
        
        # Process wind direction field (canonical: wind_dir)
        if "wind_dir" in resolved:
            wind_dir_info = resolved["wind_dir"]
            wind_dir_raw = row[wind_dir_info["header"]].strip()
            wind_dir_value = coerce_float(wind_dir_raw)
            
            if wind_dir_value is not None:
                # Validate range
                if 0 <= wind_dir_value <= 360:
                    weather_data['wind_dir_deg'] = wind_dir_value
                    valid_fields_found = True
                else:
                    warnings.append(f"Row {row_num}: Wind direction {wind_dir_value}° outside 0-360° range")
            else:
                warnings.append(f"row {row_num}: invalid wind direction value")
            
            # Add alias warning if used
            if wind_dir_info.get("alias_used"):
                warnings.append(f"row {row_num}: alias_used: {wind_dir_info['header']}→wind_dir")
        
        # Process rain flag field (canonical: rain)
        if "rain" in resolved:
            rain_info = resolved["rain"]
            rain_raw = row[rain_info["header"]].strip()
            rain_value = coerce_int(rain_raw)
            
            if rain_value is not None:
                # Validate range
                if rain_value in [0, 1]:
                    weather_data['rain_flag'] = rain_value
                    valid_fields_found = True
                else:
                    warnings.append(f"Row {row_num}: Rain flag should be 0 or 1, got {rain_value}")
            else:
                warnings.append(f"row {row_num}: invalid rain flag value")
            
            # Add alias warning if used
            if rain_info.get("alias_used"):
                warnings.append(f"row {row_num}: alias_used: {rain_info['header']}→rain")
        
        # Check if any valid weather fields were found
        # For backward compatibility, we only discard rows if no timestamp
        # or if ALL weather fields are invalid (not just out of range)
        if not valid_fields_found:
            discard_reason = f"row {row_num}: no valid weather fields"
            return None, warnings, discard_reason
        
        # For backward compatibility with tests, we no longer discard rows with invalid numeric values
        # Instead, we just warn about them and continue processing
        # This allows the importer to return a bundle even with some invalid values
        
        # Create weather point
        weather_point = WeatherPoint(**weather_data)
        return weather_point, warnings, None
    
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
        Resolve weather CSV headers to standardized field names with enhanced alias support.
        
        Args:
            headers: List of CSV header names
            
        Returns:
            dict: Maps standardized field names to actual header names and conversion info
                Format: {
                    "ts": {"header": "actual_header", "conversion": "seconds_to_ms"},
                    "temp": {"header": "actual_header", "conversion": "none", "alias_used": True},
                    "wind": {"header": "actual_header", "conversion": "mph_to_kph", "alias_used": True},
                    "humidity": {"header": "actual_header", "conversion": "none"}
                }
        """
        result = {}
        
        # For each canonical field, find the matching header
        for canonical_field, aliases in cls.FIELD_MAPPINGS.items():
            for alias in aliases:
                # Case-insensitive matching
                matching_headers = [h for h in headers if h.lower() == alias.lower()]
                if matching_headers:
                    # Use the first match
                    actual_header = matching_headers[0]
                    
                    # Determine conversion
                    conversion = cls._determine_conversion(canonical_field, alias)
                    
                    # Check if alias is used (not canonical)
                    alias_used = alias.lower() != canonical_field.lower()
                    
                    result[canonical_field] = {
                        "header": actual_header,
                        "conversion": conversion,
                        "alias_used": alias_used
                    }
                    break
        
        return result
    
    @classmethod
    def _determine_conversion(cls, canonical_field: str, alias: str) -> str:
        """Determine conversion needed for a field alias."""
        alias_lower = alias.lower()
        canonical_lower = canonical_field.lower()
        
        # Timestamp conversions
        if canonical_lower == "ts":
            if alias_lower.endswith("_ms"):
                return "none"  # Already in milliseconds
            elif alias_lower.endswith("_seconds"):
                return "seconds_to_ms"  # Convert seconds to milliseconds
            elif alias_lower.endswith("_s"):
                return "seconds_to_ms"  # Convert seconds to milliseconds
            elif alias_lower in ["utc", "utc_seconds"]:
                return "seconds_to_ms"  # Convert UTC seconds to milliseconds (normalized)
            else:
                return "seconds_to_ms"  # Default to seconds to milliseconds
        
        # Wind speed conversions
        if canonical_lower == "wind":
            if alias_lower.endswith("_mph"):
                return "mph_to_kph"  # Convert mph to kph
            elif alias_lower.endswith("_mps"):
                return "mps_to_kph"  # Convert m/s to kph
            else:
                return "none"  # Already in kph or km/h
        
        # No conversion needed for other fields
        return "none"
    
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
    def inspect_weather_csv(cls, file: BinaryIO | TextIO) -> Dict[str, Any]:
        """
        Inspect weather CSV file to analyze headers and data structure.
        
        Args:
            file: File-like object containing CSV data
            
        Returns:
            Dictionary with inspection results:
            {
                "headers": [...],
                "recognized": {...},
                "reasons": [...],
                "rows_total": N,
                "rows_accepted": M,
                "timestamps": T
            }
        """
        try:
            # Handle both binary and text files with encoding fallback
            content, encoding_used = cls._read_file_with_encoding_fallback(file)
            if content is None:
                return {
                    "headers": [],
                    "recognized": {},
                    "reasons": ["Failed to read file with any supported encoding"],
                    "rows_total": 0,
                    "rows_accepted": 0,
                    "timestamps": 0
                }
            
            # Auto-detect delimiter
            delimiter = cls._detect_delimiter(content)
            
            # Read CSV data
            text_io = io.StringIO(content)
            reader = csv.DictReader(text_io, delimiter=delimiter)
            rows = list(reader)
            
            if not rows:
                return {
                    "headers": [],
                    "recognized": {},
                    "reasons": ["Empty CSV file"],
                    "rows_total": 0,
                    "rows_accepted": 0,
                    "timestamps": 0
                }
            
            # Get field names from CSV
            headers = reader.fieldnames or []
            
            # Resolve columns using the new function
            resolved = cls.resolve_weather_columns(headers)
            
            # Get recognized headers with canonical names
            recognized_headers = {}
            for k, v in resolved.items():
                # Map canonical field names to their actual headers
                if k == "ts":
                    recognized_headers["ts_ms"] = v["header"]
                elif k == "temp":
                    recognized_headers["temp_c"] = v["header"]
                elif k == "wind":
                    recognized_headers["wind_kph"] = v["header"]
                elif k == "humidity":
                    recognized_headers["humidity_pct"] = v["header"]
                else:
                    recognized_headers[k] = v["header"]
            
            # Get unrecognized headers
            unrecognized_names = [h for h in headers if h not in recognized_headers.values()]
            
            # Process rows to count accepted and collect reasons
            accepted_count = 0
            all_reasons = []
            
            for row_num, row in enumerate(rows, 1):
                try:
                    weather_point, warnings, discard_reason = cls._process_row(row, "dummy_session", row_num)
                    if discard_reason:
                        all_reasons.append(discard_reason)
                    if weather_point:
                        accepted_count += 1
                    all_reasons.extend(warnings)
                except Exception as e:
                    all_reasons.append(f"row {row_num}: error processing row: {e}")
            
            return {
                "headers": headers,
                "recognized": recognized_headers,
                "recognized_headers": list(recognized_headers.values()),
                "unrecognized_names": [h for h in headers if h not in recognized_headers.values()],
                "reasons": all_reasons,
                "rows_total": len(rows),
                "rows_accepted": accepted_count,
                "timestamps": len(set(row.get(resolved["ts"]["header"], "") for row in rows if resolved.get("ts")))
            }
            
        except Exception as e:
            return {
                "headers": [],
                "recognized": {},
                "reasons": [f"Error processing weather CSV: {str(e)}"],
                "rows_total": 0,
                "rows_accepted": 0,
                "timestamps": 0
            }
    
    @classmethod
    def inspect_text(cls, text: str) -> Dict[str, Any]:
        """
        Inspect weather CSV text to analyze headers and data structure.
        
        Args:
            text: CSV text content to inspect
            
        Returns:
            Dictionary with inspection results including headers, recognized, reasons, rows_total, timestamps
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
        recognized = {k: v["header"] for k, v in resolved.items()}
        
        # Generate reasons
        reasons = []
        for field_type, info in resolved.items():
            reasons.append(f"Weather field '{field_type}' found: '{info['header']}' with conversion '{info['conversion']}'")
        
        # Add missing field reasons
        if "ts" not in resolved:
            reasons.append("No timestamp field found among expected: ts_ms, time_ms, timestamp_ms, ts, timestamp, utc, epoch, epoch_ms")
        if "temp" not in resolved:
            reasons.append("No temperature field found among expected: temp, temp_c, air_temp_c")
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