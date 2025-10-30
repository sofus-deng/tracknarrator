"""Tests for RaceChrono CSV importer."""

import io

import pytest

from src.tracknarrator.importers.racechrono_csv import RaceChronoCSVImporter
from src.tracknarrator.schema import Telemetry


class TestRaceChronoCSVImporter:
    """Test cases for RaceChrono CSV importer."""
    
    def test_import_basic_telemetry(self):
        """Test importing basic telemetry data with all required fields."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%),Brake pos (%)
0.000,10.0,0.0,33.123456,0.0,0.0
1.000,50.5,0.0,33.123457,25.5,10.2
2.000,120.5,0.0,33.123458,75.2,50.8"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.warnings) == 1  # Should have warning about brake column
        assert "brake_pos_pct not mapped" in result.warnings[0]
        assert len(result.bundle.telemetry) == 3
        
        # Check first telemetry point
        telemetry = result.bundle.telemetry[0]
        assert telemetry.session_id == "test-session"
        assert telemetry.ts_ms == 0  # 0.000s * 1000
        assert telemetry.speed_kph == 10.0
        assert telemetry.lat_deg == 33.123456
        assert telemetry.lon_deg == 0.0
        assert telemetry.throttle_pct == 0.0
        assert telemetry.brake_bar is None  # Should be None (not mapped)
        
        # Check second telemetry point
        telemetry = result.bundle.telemetry[1]
        assert telemetry.ts_ms == 1000  # 1.000s * 1000
        assert telemetry.speed_kph == 50.5
        assert telemetry.throttle_pct == 25.5
        assert telemetry.brake_bar is None  # Should be None (not mapped)
    
    def test_speed_bounds_validation(self):
        """Test speed bounds validation (0-400 km/h)."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,-10.0,-87.654321,33.123456,0.0
1.000,500.0,-87.654322,33.123457,25.5
2.000,200.0,-87.654323,33.123458,75.2"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 3  # All rows should be clamped
        
        # Check first row (speed clamped to 0)
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 0  # 0.000s * 1000
        assert telemetry.speed_kph == 0.0  # Clamped to minimum
        
        # Check second row (speed clamped to 400)
        telemetry = result.bundle.telemetry[1]
        assert telemetry.ts_ms == 1000  # 1.000s * 1000
        assert telemetry.speed_kph == 400.0  # Clamped to maximum
        
        # Check third row (valid speed)
        telemetry = result.bundle.telemetry[2]
        assert telemetry.ts_ms == 2000  # 2.000s * 1000
        assert telemetry.speed_kph == 200.0  # Valid speed
    
    def test_throttle_clamping(self):
        """Test throttle percentage clamping to [0, 100]."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,50.0,-87.654321,33.123456,-25.0
1.000,60.0,-87.654322,33.123457,150.0
2.000,70.0,-87.654323,33.123458,50.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 3
        
        # Check first telemetry point (clamped to 0)
        telemetry = result.bundle.telemetry[0]
        assert telemetry.throttle_pct == 0.0
        
        # Check second telemetry point (clamped to 100)
        telemetry = result.bundle.telemetry[1]
        assert telemetry.throttle_pct == 100.0
        
        # Check third telemetry point (unchanged)
        telemetry = result.bundle.telemetry[2]
        assert telemetry.throttle_pct == 50.0
    
    def test_coordinate_bounds_validation(self):
        """Test coordinate bounds validation."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,50.0,-200.0,33.123456,25.0
1.000,60.0,-87.654322,100.0,50.0
2.000,70.0,-87.654323,33.123458,75.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 3  # All rows should be clamped
        
        # Check first row (longitude clamped to -180)
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 0  # 0.000s * 1000
        assert telemetry.lon_deg == -180.0  # Clamped to minimum
        assert telemetry.lat_deg == 33.123456  # Valid latitude
        
        # Check second row (latitude clamped to 90)
        telemetry = result.bundle.telemetry[1]
        assert telemetry.ts_ms == 1000  # 1.000s * 1000
        assert telemetry.lon_deg == -87.654322  # Valid longitude
        assert telemetry.lat_deg == 90.0  # Clamped to maximum
        
        # Check third row (valid coordinates)
        telemetry = result.bundle.telemetry[2]
        assert telemetry.ts_ms == 2000  # 2.000s * 1000
        assert telemetry.lon_deg == -87.654323  # Valid longitude
        assert telemetry.lat_deg == 33.123458  # Valid latitude
    
    def test_timestamp_deduplication_within_1ms(self):
        """Test telemetry de-duplication within ±1 ms buckets."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,50.0,-87.654321,33.123456,25.0
0.001,60.0,-87.654322,33.123457,50.0
0.002,70.0,-87.654323,33.123458,75.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should have 2 telemetry points: one from bucket (0ms), one from separate timestamp (2ms)
        assert len(result.bundle.telemetry) == 2
        
        # First telemetry should be from 0ms bucket with more fields
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 0  # Should use first timestamp
        assert telemetry.speed_kph == 50.0  # From first row
        
        # Second telemetry should be from 2ms
        telemetry = result.bundle.telemetry[1]
        assert telemetry.ts_ms == 2  # 0.002s * 1000, but rounded to 2ms
        assert telemetry.speed_kph == 70.0
    
    def test_timestamp_deduplication_keeps_more_fields(self):
        """Test that de-duplication keeps the row with more non-None fields."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,50.0,,,25.0
0.001,60.0,-87.654322,33.123457,50.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1  # Should be deduped to single point
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 1  # Should use second timestamp (more fields)
        assert telemetry.speed_kph == 60.0
        assert telemetry.lon_deg == -87.654322  # Should have coordinates
        assert telemetry.lat_deg == 33.123457
        assert telemetry.throttle_pct == 50.0
    
    def test_semicolon_delimiter(self):
        """Test importing with semicolon delimiter."""
        csv_content = """Time (s);Speed (km/h);Longitude;Latitude;Throttle pos (%)
0.000;50.0;-87.654321;33.123456;25.0
1.000;60.0;-87.654322;33.123457;50.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 2
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.speed_kph == 50.0
        assert telemetry.lon_deg == -87.654321
        assert telemetry.lat_deg == 33.123456
        assert telemetry.throttle_pct == 25.0
    
    def test_empty_csv(self):
        """Test handling of empty CSV."""
        csv_content = ""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "Empty CSV file" in result.warnings[0]
    
    def test_invalid_time_format(self):
        """Test handling of invalid time format."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
invalid,50.0,-87.654321,33.123456,25.0
1.000,60.0,-87.654322,33.123457,50.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1  # Only valid row
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 1000  # 1.000s * 1000
        assert telemetry.speed_kph == 60.0
    
    def test_no_valid_telemetry_fields(self):
        """Test handling when no valid telemetry fields are present."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,invalid,invalid,invalid,invalid"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert "No valid telemetry rows found" in result.warnings[0]
    
    def test_brake_column_warning(self):
        """Test that brake column generates appropriate warning."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%),Brake pos (%)
0.000,50.0,-87.654321,33.123456,25.0,10.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should have warning about brake column
        brake_warnings = [w for w in result.warnings if "brake_pos_pct not mapped" in w]
        assert len(brake_warnings) == 1
        
        # brake_bar should remain None
        telemetry = result.bundle.telemetry[0]
        assert telemetry.brake_bar is None
    
    def test_time_out_of_range(self):
        """Test handling of time values outside reasonable range."""
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
100000.0,50.0,-87.654321,33.123456,25.0
1.000,60.0,-87.654322,33.123457,50.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1  # Only valid row
        assert "outside reasonable range" in result.warnings[0]
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 1000  # 1.000s * 1000
    
    def test_missing_time_column(self):
        """Test handling when Time column is missing."""
        csv_content = """Speed (km/h),Longitude,Latitude,Throttle pos (%)
50.0,-87.654321,33.123456,25.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert "No valid telemetry rows found" in result.warnings[0]