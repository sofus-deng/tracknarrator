"""Tests for weather CSV importer alias support and unit conversions."""

import io
import pytest

from src.tracknarrator.importers.weather_csv import WeatherCSVImporter


class TestWeatherCSVImporterAliases:
    """Test cases for weather CSV importer with alias support."""
    
    @pytest.mark.parametrize("headers,expected_mappings", [
        # Test case 1: Standard aliases with comma delimiter
        (["ts_ms", "temp_c", "humidity_pct", "wind_kph"],
         {"ts": {"header": "ts_ms", "conversion": "none"},
          "temp": {"header": "temp_c", "conversion": "none"},
          "humidity": {"header": "humidity_pct", "conversion": "none"},
          "wind": {"header": "wind_kph", "conversion": "none"}}),
        
        # Test case 2: Time aliases with semicolon delimiter
        (["utc_seconds", "temperature", "rh", "wind_mps"],
         {"ts": {"header": "utc_seconds", "conversion": "seconds_to_ms"},
          "temp": {"header": "temperature", "conversion": "none"},
          "humidity": {"header": "rh", "conversion": "none"},
          "wind": {"header": "wind_mps", "conversion": "mps_to_kph"}}),
        
        # Test case 3: Mixed aliases
        (["timestamp", "air_temp_c", "relative_humidity", "wind_speed_kph"],
         {"ts": {"header": "timestamp", "conversion": "seconds_to_ms"},
          "temp": {"header": "air_temp_c", "conversion": "none"},
          "humidity": {"header": "relative_humidity", "conversion": "none"},
          "wind": {"header": "wind_speed_kph", "conversion": "none"}}),
        
        # Test case 4: Short aliases with semicolon delimiter
        (["time_s", "temp", "humidity", "wind"],
         {"ts": {"header": "time_s", "conversion": "seconds_to_ms"},
          "temp": {"header": "temp", "conversion": "none"},
          "humidity": {"header": "humidity", "conversion": "none"},
          "wind": {"header": "wind", "conversion": "none"}}),
        
        # Test case 5: Case insensitive matching
        (["TS_MS", "TEMP_C", "HUMIDITY_PCT", "WIND_KPH"],
         {"ts": {"header": "TS_MS", "conversion": "none"},
          "temp": {"header": "TEMP_C", "conversion": "none"},
          "humidity": {"header": "HUMIDITY_PCT", "conversion": "none"},
          "wind": {"header": "WIND_KPH", "conversion": "none"}}),
        
        # Test case 6: Partial field matching
        (["utc", "temp", "humidity_pct"],
         {"ts": {"header": "utc", "conversion": "seconds_to_ms"},
          "temp": {"header": "temp", "conversion": "none"},
          "humidity": {"header": "humidity_pct", "conversion": "none"}})
    ])
    def test_resolve_weather_columns(self, headers, expected_mappings):
        """Test resolving weather column aliases."""
        result = WeatherCSVImporter.resolve_weather_columns(headers)
        
        # Check that all expected fields are present
        for field_type, expected_info in expected_mappings.items():
            assert field_type in result
            assert result[field_type]["header"] == expected_info["header"]
            assert result[field_type]["conversion"] == expected_info["conversion"]
    
    @pytest.mark.parametrize("csv_content,delimiter,expected_wind_speed", [
        # Test wind_mps to wind_kph conversion
        ("timestamp,temp,humidity,wind_mps\n1722838223,25.5,65.0,5.0", ",", 18.0),
        # Test no conversion needed for wind_kph
        ("timestamp,temp,humidity,wind_kph\n1722838223,25.5,65.0,18.0", ",", 18.0),
        # Test with semicolon delimiter
        ("timestamp;temp;humidity;wind_mps\n1722838223;25.5;65.0;5.0", ";", 18.0)
    ])
    def test_wind_speed_conversion(self, csv_content, delimiter, expected_wind_speed):
        """Test wind speed unit conversion from m/s to kph."""
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.wind_speed == expected_wind_speed
    
    @pytest.mark.parametrize("csv_content,delimiter,expected_ts_ms", [
        # Test seconds to milliseconds conversion
        ("timestamp,temp,humidity,wind\n1722838223,25.5,65.0,18.0", ",", 1722838223000),
        # Test no conversion needed for ms
        ("ts_ms,temp,humidity,wind\n1722838223000,25.5,65.0,18.0", ",", 1722838223000),
        # Test with semicolon delimiter
        ("utc_seconds;temp;humidity;wind\n1722838223;25.5;65.0;18.0", ";", 1722838223000)
    ])
    def test_timestamp_conversion(self, csv_content, delimiter, expected_ts_ms):
        """Test timestamp unit conversion from seconds to milliseconds."""
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.ts_ms == expected_ts_ms
    
    @pytest.mark.parametrize("csv_content,delimiter", [
        # Test comma delimiter
        ("ts_ms,temp_c,humidity_pct,wind_kph\n1722838223000,25.5,65.0,18.0", ","),
        # Test semicolon delimiter
        ("ts_ms;temp_c;humidity_pct;wind_kph\n1722838223000;25.5;65.0;18.0", ";")
    ])
    def test_delimiter_detection(self, csv_content, delimiter):
        """Test CSV delimiter detection."""
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.ts_ms == 1722838223000
        assert weather.air_temp_c == 25.5
        assert weather.humidity_pct == 65.0
        assert weather.wind_speed == 18.0
    
    def test_inspect_text_with_aliases(self):
        """Test inspect_text with various aliases."""
        csv_content = """utc_seconds,temperature,rh,wind_mps
1722838223,25.5,65.0,5.0
1722838283,26.0,63.5,4.8"""
        
        result = WeatherCSVImporter.inspect_text(csv_content)
        
        assert result["header"] == ["utc_seconds", "temperature", "rh", "wind_mps"]
        assert result["recognized"]["ts"] == "utc_seconds"
        assert result["recognized"]["temp"] == "temperature"
        assert result["recognized"]["humidity"] == "rh"
        assert result["recognized"]["wind"] == "wind_mps"
        assert result["rows_total"] == 2
        assert result["timestamps"] == 2
        assert any("seconds_to_ms" in reason for reason in result["reasons"])
        assert any("mps_to_kph" in reason for reason in result["reasons"])
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive header matching."""
        csv_content = """TS_MS,TEMP_C,HUMIDITY_PCT,WIND_KPH
1722838223000,25.5,65.0,18.0"""
        
        file_obj = io.StringIO(csv_content)
        result = WeatherCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.weather) == 1
        
        weather = result.bundle.weather[0]
        assert weather.ts_ms == 1722838223000
        assert weather.air_temp_c == 25.5
        assert weather.humidity_pct == 65.0
        assert weather.wind_speed == 18.0