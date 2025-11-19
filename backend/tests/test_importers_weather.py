"""Tests for enhanced weather CSV importer."""

import io

import pytest

from src.tracknarrator.importers.weather_csv import WeatherCSVImporter
from src.tracknarrator.schema import WeatherPoint


class TestWeatherCSVImporter:
    """Test cases for enhanced weather CSV importer."""
    
    def test_import_weather_ok_csv(self):
        """Test importing weather_ok.csv sample file."""
        csv_content = """ts_ms,temp_c,wind_kph,humidity_pct
0,26,5,55
3600000,27,6,60
7200000,25,7,65"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 3
        
        # Check first weather point
        weather1 = result.bundle.weather[0]
        assert weather1.session_id == "test-session"
        assert weather1.ts_ms == 0
        assert weather1.air_temp_c == 26.0
        assert weather1.wind_speed == 5.0
        assert weather1.humidity_pct == 55.0
        
        # Check second weather point
        weather2 = result.bundle.weather[1]
        assert weather2.ts_ms == 3600000
        assert weather2.air_temp_c == 27.0
        assert weather2.wind_speed == 6.0
        assert weather2.humidity_pct == 60.0
    
    def test_import_weather_utc_csv(self):
        """Test importing weather_utc.csv sample file with UTC timestamp."""
        csv_content = """utc,temp_c,wind_kph
0,26,5
3600,27,6
7200,25,7"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 3
        
        # Check first weather point (UTC seconds converted to ms)
        weather1 = result.bundle.weather[0]
        assert weather1.ts_ms == 0  # 0 seconds * 1000
        assert weather1.air_temp_c == 26.0
        assert weather1.wind_speed == 5.0
        
        # Check second weather point (UTC seconds converted to ms)
        weather2 = result.bundle.weather[1]
        assert weather2.ts_ms == 3600000  # 3600 seconds * 1000
        assert weather2.air_temp_c == 27.0
        assert weather2.wind_speed == 6.0
    
    def test_import_weather_semicolon_csv(self):
        """Test importing weather_semicolon.csv sample file with semicolon delimiter."""
        csv_content = """ts_ms;temp_c;wind_kph
0;26;5
3600000;27;6"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 2
        
        # Check first weather point
        weather1 = result.bundle.weather[0]
        assert weather1.ts_ms == 0
        assert weather1.air_temp_c == 26.0
        assert weather1.wind_speed == 5.0
        
        # Check second weather point
        weather2 = result.bundle.weather[1]
        assert weather2.ts_ms == 3600000
        assert weather2.air_temp_c == 27.0
        assert weather2.wind_speed == 6.0
    
    def test_import_with_aliases(self):
        """Test importing with field aliases."""
        csv_content = """ts,air_temp_c,wind_mph,humidity
0,25.5,3.1,65
3600,26.0,3.4,63"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 2
        
        # Check alias usage warnings
        assert any("alias_used: air_temp_c→temp" in w for w in result.warnings)
        assert any("alias_used: wind_mph→wind" in w for w in result.warnings)
        # humidity is the canonical name, so no alias warning
        
        # Check first weather point (mph converted to kph)
        weather1 = result.bundle.weather[0]
        assert weather1.ts_ms == 0  # seconds converted to ms
        assert weather1.air_temp_c == 25.5
        assert weather1.wind_speed == 3.1 * 1.60934  # mph to kph conversion
        assert weather1.humidity_pct == 65.0
    
    def test_import_with_invalid_timestamp(self):
        """Test importing with invalid timestamp."""
        csv_content = """ts,temp_c,wind_kph,humidity_pct
invalid,26,5,55
3600,27,6,60"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1  # Only second row should be accepted
        
        # Check discard reason for first row
        assert any("row 1: missing/invalid timestamp" in w for w in result.warnings)
    
    def test_import_with_out_of_range_values(self):
        """Test importing with out-of-range values."""
        csv_content = """ts_ms,temp_c,wind_kph,humidity_pct
0,85,5,55  # Out of range temperature
3600000,26,300,60  # Out of range wind
7200000,25,6,120  # Out of range humidity"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None  # Bundle should still be created with warnings
        assert len(result.bundle.weather) == 3  # All rows should be accepted with warnings
        
        # Check out-of-range warnings
        assert any("row 1: out-of-range temp 85.0C" in w for w in result.warnings)
        assert any("row 2: out-of-range wind 300kph" in w for w in result.warnings)
        assert any("row 3: out-of-range humidity 120.0%" in w for w in result.warnings)
    
    def test_import_with_no_valid_fields(self):
        """Test importing with no valid weather fields."""
        csv_content = """ts_ms,invalid_field,another_invalid
0,1,2
3600000,3,4"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None  # Should fail
        assert any("missing required columns" in w for w in result.warnings)
    
    def test_comma_delimiter(self):
        """Test importing with comma delimiter."""
        csv_content = """TIME_UTC_SECONDS,AIR_TEMP,TRACK_TEMP,HUMIDITY,PRESSURE,WIND_SPEED,WIND_DIRECTION,RAIN
1722838223,25.5,35.2,65.0,1013.25,5.2,180.0,0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.air_temp_c == 25.5
        assert weather.ts_ms == 1722838223000
    
    def test_alternative_headers(self):
        """Test importing with alternative header names."""
        csv_content = """TIME;AIR_TEMPERATURE;TRACK_TEMPERATURE;HUMIDITY_PCT;PRESSURE_HPA;WIND;WIND_DIR;RAIN_FLAG
1722838223;25.5;35.2;65.0;1013.25;5.2;180.0;1"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.air_temp_c == 25.5
        assert weather.track_temp_c == 35.2
        assert weather.humidity_pct == 65.0
        assert weather.pressure_hpa == 1013.25
        assert weather.wind_speed == 5.2
        assert weather.wind_dir_deg == 180.0
        assert weather.rain_flag == 1
    
    def test_missing_values(self):
        """Test handling of missing values."""
        csv_content = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1722838223;25.5;;65.0;;5.2;180.0;0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.air_temp_c == 25.5
        assert weather.track_temp_c is None  # Missing
        assert weather.humidity_pct == 65.0
        assert weather.pressure_hpa is None  # Missing
        assert weather.wind_speed == 5.2
        assert weather.wind_dir_deg == 180.0
        assert weather.rain_flag == 0
    
    def test_invalid_numeric_values(self):
        """Test handling of invalid numeric values."""
        csv_content = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1722838223;invalid;35.2;invalid;1013.25;invalid;180.0;invalid"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.air_temp_c is None  # Invalid
        assert weather.track_temp_c == 35.2
        assert weather.humidity_pct is None  # Invalid
        assert weather.pressure_hpa == 1013.25
        assert weather.wind_speed is None  # Invalid
        assert weather.wind_dir_deg == 180.0
        assert weather.rain_flag is None  # Invalid
    
    def test_out_of_range_warnings(self):
        """Test warnings for out-of-range values."""
        csv_content = """TIME;AIR_TEMPERATURE;TRACK_TEMPERATURE;HUMIDITY_PCT;PRESSURE_HPA;WIND;WIND_DIR;RAIN_FLAG
1722838223;-60.0;90.0;120.0;700.0;-5.0;400.0;2"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        # This test uses legacy headers, so it should work with legacy processing
        # which accepts out-of-range values with warnings
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        # Should have multiple warnings for out-of-range values
        warnings = result.warnings
        assert any("out-of-range temp -60.0C" in w for w in warnings)
        assert any("Track temperature 90.0°C outside reasonable range" in w for w in warnings)
        assert any("out-of-range humidity 120.0%" in w for w in warnings)
        assert any("Pressure 700.0 hPa outside reasonable range" in w for w in warnings)
        assert any("out-of-range wind" in w for w in warnings)
        assert any("Wind direction 400.0° outside 0-360° range" in w for w in warnings)
        assert any("Rain flag should be 0 or 1, got 2" in w for w in warnings)
    
    def test_missing_timestamp(self):
        """Test handling of missing timestamp."""
        csv_content = """AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
25.5;35.2;65.0;1013.25;5.2;180.0;0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None  # Should fail
        assert any("missing required columns" in w for w in result.warnings)
    
    def test_invalid_timestamp(self):
        """Test handling of invalid timestamp."""
        csv_content = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
invalid;25.5;35.2;65.0;1013.25;5.2;180.0;0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None  # Should fail
        assert any("row 1: missing/invalid timestamp" in w for w in result.warnings)
    
    def test_empty_csv(self):
        """Test handling of empty CSV."""
        csv_content = ""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "Empty CSV file" in result.warnings[0]
    
    def test_no_valid_weather_data(self):
        """Test handling when no valid weather data is found."""
        csv_content = """TIME_UTC_SECONDS;INVALID_HEADER
1722838223;invalid"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert any("missing required columns" in w for w in result.warnings)
    
    def test_fractional_timestamp(self):
        """Test handling of fractional timestamp seconds."""
        csv_content = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1722838223.5;25.5;35.2;65.0;1013.25;5.2;180.0;0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        # Should convert 1722838223.5 seconds to 1722838223500 ms
        assert weather.ts_ms == 1722838223500
    
    def test_negative_wind_speed_warning(self):
        """Test specific warning for negative wind speed."""
        csv_content = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1722838223;25.5;35.2;65.0;1013.25;-2.5;180.0;0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should have warning about negative wind speed
        warnings = result.warnings
        assert any("out-of-range wind" in w for w in warnings)