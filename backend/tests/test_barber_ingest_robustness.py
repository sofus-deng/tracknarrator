"""Tests for Barber CSV ingestion robustness."""

import io
import pytest

from src.tracknarrator.importers.trd_long_csv import TRDLongCSVImporter
from src.tracknarrator.importers.weather_csv import WeatherCSVImporter
from src.tracknarrator.importers.mylaps_sections_csv import MYLAPSSectionsCSVImporter


class TestBarberIngestRobustness:
    """Test cases for Barber CSV ingestion robustness."""
    
    def test_telemetry_missing_required_columns(self):
        """Test that telemetry importer raises clear error for missing required columns."""
        # CSV with missing telemetry_value column
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "missing required columns: telemetry_value" in result.warnings[0]
        assert "data/barber/telemetry.csv" in result.warnings[0]
    
    def test_telemetry_empty_file(self):
        """Test that telemetry importer raises clear error for empty file."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "Empty telemetry.csv file" in result.warnings[0]
    
    def test_telemetry_invalid_numeric_skipped(self):
        """Test that telemetry importer skips rows with invalid numeric values."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,invalid_value,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1  # Only the valid row should be kept
        
        # Should have warning about skipped rows
        skipped_warnings = [w for w in result.warnings if "rows skipped" in w]
        assert len(skipped_warnings) == 1
        assert "1 rows skipped" in skipped_warnings[0]
    
    def test_weather_missing_required_columns(self):
        """Test that weather importer raises clear error for missing required columns."""
        # CSV with only invalid columns
        csv_content = """invalid_column1,invalid_column2,invalid_column3
1,2,3
4,5,6"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "missing required columns" in result.warnings[0]
        assert "timestamp" in result.warnings[0]
        assert "weather data" in result.warnings[0]
        assert "data/barber/weather.csv" in result.warnings[0]
    
    def test_weather_empty_file(self):
        """Test that weather importer raises clear error for empty file."""
        csv_content = """TIME_UTC_SECONDS,AIR_TEMP,TRACK_TEMP,HUMIDITY,PRESSURE,WIND_SPEED,WIND_DIRECTION,RAIN
"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "Empty CSV file" in result.warnings[0]
    
    def test_weather_invalid_numeric_skipped(self):
        """Test that weather importer includes rows with invalid numeric values but warns about them."""
        csv_content = """TIME_UTC_SECONDS,AIR_TEMP,WIND_SPEED,HUMIDITY
0,25.5,5.0,55.0
3600,invalid,6.0,60.0
7200,27.0,invalid,65.0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 3  # All rows are included but with warnings
        
        # Should have warnings about invalid values
        invalid_warnings = [w for w in result.warnings if "invalid" in w]
        assert len(invalid_warnings) >= 2  # At least 2 warnings for invalid values
    
    def test_sections_missing_required_columns(self):
        """Test that sections importer raises clear error for missing required columns."""
        # CSV with missing LAP_TIME column
        csv_content = """LAP_NUMBER,DRIVER_NUMBER,IM1a,IM1,IM2a,IM2,IM3a,FL
1,1,0:12.345,0:25.678,0:38.901,0:52.234,1:05.567,1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "missing required columns: LAP_TIME" in result.warnings[0]
        assert "data/barber/sections.csv" in result.warnings[0]
    
    def test_sections_empty_file(self):
        """Test that sections importer raises clear error for empty file."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "Empty CSV file" in result.warnings[0]
    
    def test_sections_invalid_numeric_error(self):
        """Test that sections importer raises error for invalid numeric values in critical fields."""
        csv_content = """LAP_NUMBER,DRIVER_NUMBER,LAP_TIME,IM1a,IM1,IM2a,IM2,IM3a,FL
1,1,invalid,0:12.345,0:25.678,0:38.901,0:52.234,1:05.567,1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        # Should have error about invalid LAP_TIME
        lap_time_errors = [w for w in result.warnings if "Invalid LAP_TIME" in w]
        assert len(lap_time_errors) == 1
        assert "invalid" in lap_time_errors[0]