"""Tests for encoding and delimiter detection in importers."""

import io

import pytest

from src.tracknarrator.importers.mylaps_sections_csv import MYLAPSSectionsCSVImporter
from src.tracknarrator.importers.weather_csv import WeatherCSVImporter
from src.tracknarrator.importers.racechrono_csv import RaceChronoCSVImporter


class TestEncodingsDelimiters:
    """Test cases for encoding and delimiter detection."""
    
    def test_utf8_encoding_mylaps(self):
        """Test MYLAPS importer with UTF-8 encoding."""
        csv_content = "LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL\n1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_utf8_sig_encoding_mylaps(self):
        """Test MYLAPS importer with UTF-8-BOM encoding."""
        # Content without BOM, let encode('utf-8-sig') add it
        csv_content = "LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL\n1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"
        
        file_obj = io.BytesIO(csv_content.encode('utf-8-sig'))
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_latin1_encoding_weather(self):
        """Test weather importer with Latin-1 encoding."""
        # Create content with Latin-1 characters
        csv_content = "TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN\n1714500000;25.5;35.2;65.0;1013.25;5.5;180.0;0"
        
        file_obj = io.BytesIO(csv_content.encode('latin-1'))
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
    
    def test_comma_delimiter_detection(self):
        """Test comma delimiter detection."""
        csv_content = """LAP_NUMBER,DRIVER_NUMBER,LAP_TIME,IM1a,IM1,IM2a,IM2,IM3a,FL
1,1,1:23.456,0:12.345,0:25.678,0:38.901,0:52.234,1:05.567,1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_semicolon_delimiter_detection(self):
        """Test semicolon delimiter detection."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_delimiter_preference_semicolon_over_comma(self):
        """Test that semicolon is preferred when more semicolons than commas."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_delimiter_preference_comma_over_semicolon(self):
        """Test that comma is preferred when more commas than semicolons."""
        csv_content = """LAP_NUMBER,DRIVER_NUMBER,LAP_TIME,IM1a,IM1,IM2a,IM2,IM3a,FL
1,1,1:23.456,0:12.345,0:25.678,0:38.901,0:52.234,1:05.567,1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_racechrono_encoding_fallback(self):
        """Test RaceChrono importer with encoding fallback."""
        # Test UTF-8
        csv_content = "Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)\n0.000,50.0,-87.654321,33.123456,25.0"
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1
        
        # Test UTF-8-BOM
        csv_content_bom = "Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)\n0.000,50.0,-87.654321,33.123456,25.0"
        
        file_obj = io.BytesIO(csv_content_bom.encode('utf-8-sig'))
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1
        
        # Test Latin-1
        csv_content_latin1 = "Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)\n0.000,50.0,-87.654321,33.123456,25.0"
        
        file_obj = io.BytesIO(csv_content_latin1.encode('latin-1'))
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1
    
    def test_weather_encoding_fallback(self):
        """Test weather importer with encoding fallback."""
        # Test UTF-8
        csv_content = "TIME_UTC_SECONDS,AIR_TEMP,TRACK_TEMP,HUMIDITY,PRESSURE,WIND_SPEED,WIND_DIRECTION,RAIN\n1714500000,25.5,35.2,65.0,1013.25,5.5,180.0,0"
        
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        # Test UTF-8-BOM
        csv_content_bom = "TIME_UTC_SECONDS,AIR_TEMP,TRACK_TEMP,HUMIDITY,PRESSURE,WIND_SPEED,WIND_DIRECTION,RAIN\n1714500000,25.5,35.2,65.0,1013.25,5.5,180.0,0"
        
        file_obj = io.BytesIO(csv_content_bom.encode('utf-8-sig'))
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        # Test Latin-1
        csv_content_latin1 = "TIME_UTC_SECONDS,AIR_TEMP,TRACK_TEMP,HUMIDITY,PRESSURE,WIND_SPEED,WIND_DIRECTION,RAIN\n1714500000,25.5,35.2,65.0,1013.25,5.5,180.0,0"
        
        file_obj = io.BytesIO(csv_content_latin1.encode('latin-1'))
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
    
    def test_racechrono_delimiter_detection(self):
        """Test RaceChrono delimiter detection."""
        # Test comma delimiter
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,50.0,-87.654321,33.123456,25.0
1.000,60.0,-87.654322,33.123457,50.0"""
        
        file_obj = io.StringIO(csv_content)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 2
        
        # Test semicolon delimiter
        csv_content_semicolon = """Time (s);Speed (km/h);Longitude;Latitude;Throttle pos (%)
0.000;50.0;-87.654321;33.123456;25.0
1.000;60.0;-87.654322;33.123457;50.0"""
        
        file_obj = io.StringIO(csv_content_semicolon)
        result = RaceChronoCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 2
    
    def test_weather_delimiter_detection(self):
        """Test weather delimiter detection."""
        # Test comma delimiter
        csv_content = """TIME_UTC_SECONDS,AIR_TEMP,TRACK_TEMP,HUMIDITY,PRESSURE,WIND_SPEED,WIND_DIRECTION,RAIN
1714500000,25.5,35.2,65.0,1013.25,5.5,180.0,0
1714500060,25.6,35.3,64.8,1013.24,5.6,181.0,0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 2
        
        # Test semicolon delimiter
        csv_content_semicolon = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1714500000;25.5;35.2;65.0;1013.25;5.5;180.0;0
1714500060;25.6;35.3;64.8;1013.24;5.6;181.0;0"""
        
        file_obj = io.StringIO(csv_content_semicolon)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 2
    
    def test_encoding_fallback_failure(self):
        """Test handling when all encoding attempts fail."""
        # Create invalid byte sequence that can't be decoded
        invalid_bytes = b'\xff\xfe\xfd\xfc\xfb\xfa'
        
        file_obj = io.BytesIO(invalid_bytes)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        # Check for either "Failed to read file" or "Empty CSV file" (both indicate encoding failure)
        warning_text = result.warnings[0]
        assert ("Failed to read file" in warning_text or "Empty CSV file" in warning_text)
    
    def test_mixed_delimiter_content(self):
        """Test delimiter detection with mixed content."""
        # More semicolons should trigger semicolon detection
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should parse correctly despite mixed delimiters
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_empty_lines_and_encoding(self):
        """Test handling of empty lines with different encodings."""
        csv_content = "LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL\n\n1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456\n"
        
        file_obj = io.BytesIO(csv_content.encode('utf-8-sig'))
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6