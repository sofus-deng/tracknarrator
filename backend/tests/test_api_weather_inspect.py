"""Tests for weather inspector API endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.tracknarrator.api import app
from src.tracknarrator.store import store


class TestWeatherInspectAPI:
    """Test cases for weather inspector API endpoint."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.client = TestClient(app)
        # Clear store before each test
        store.sessions.clear()
    
    def test_inspect_weather_ok_csv(self):
        """Test weather inspector with weather_ok.csv format."""
        csv_content = """ts_ms,temp_c,wind_kph,humidity_pct
0,26,5,55
3600000,27,6,60
7200000,25,7,65"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == ["ts_ms", "temp_c", "wind_kph", "humidity_pct"]
        assert inspect["rows_total"] == 3
        assert inspect["rows_accepted"] == 3
        assert len(inspect["recognized_headers"]) == 4
        assert "ts_ms" in inspect["recognized_headers"]
        assert "temp_c" in inspect["recognized_headers"]
        assert "wind_kph" in inspect["recognized_headers"]
        assert "humidity_pct" in inspect["recognized_headers"]
    
    def test_inspect_weather_utc_csv(self):
        """Test weather inspector with weather_utc.csv format."""
        csv_content = """utc,temp_c,wind_kph
0,26,5
3600,27,6
7200,25,7"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == ["utc", "temp_c", "wind_kph"]
        assert inspect["rows_total"] == 3
        assert inspect["rows_accepted"] == 3
        assert "utc" in inspect["recognized_headers"]
        assert "temp_c" in inspect["recognized_headers"]
        assert "wind_kph" in inspect["recognized_headers"]
    
    def test_inspect_weather_semicolon_csv(self):
        """Test weather inspector with weather_semicolon.csv format."""
        csv_content = """ts_ms;temp_c;wind_kph
0;26;5
3600000;27;6"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == ["ts_ms", "temp_c", "wind_kph"]
        assert inspect["rows_total"] == 2
        assert inspect["rows_accepted"] == 2
        assert "ts_ms" in inspect["recognized_headers"]
        assert "temp_c" in inspect["recognized_headers"]
        assert "wind_kph" in inspect["recognized_headers"]
    
    def test_inspect_weather_with_aliases(self):
        """Test weather inspector with field aliases."""
        csv_content = """ts,air_temp_c,wind_mph,humidity
0,25.5,3.1,65
3600,26.0,3.4,63"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == ["ts", "air_temp_c", "wind_mph", "humidity"]
        assert inspect["rows_total"] == 2
        assert inspect["rows_accepted"] == 2
        assert "ts" in inspect["recognized_headers"]
        assert "air_temp_c" in inspect["recognized_headers"]
        assert "wind_mph" in inspect["recognized_headers"]
        assert "humidity" in inspect["recognized_headers"]
        
        # Check for alias usage warnings
        reasons = inspect.get("reasons", [])
        assert any("alias_used: air_temp_c→temp_c" in reason for reason in reasons)
        assert any("alias_used: wind_mph→wind_kph" in reason for reason in reasons)
        # Note: "humidity" is a canonical name, not an alias, so no warning expected
    
    def test_inspect_weather_empty_file(self):
        """Test weather inspector with empty file."""
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", "", "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == []
        assert inspect["recognized"] == {}
    
    def test_inspect_weather_no_file(self):
        """Test weather inspector with no file uploaded."""
        response = self.client.post("/dev/inspect/weather")
        
        assert response.status_code == 422  # Validation error
    
    def test_inspect_weather_invalid_format(self):
        """Test weather inspector with invalid CSV format."""
        csv_content = """invalid,csv,format
just,some,random,text"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == ["invalid", "csv", "format"]
        assert inspect["recognized"] == {}
    
    def test_inspect_weather_missing_timestamp(self):
        """Test weather inspector with missing timestamp field."""
        csv_content = """AIR_TEMP,HUMIDITY,WIND_SPEED
25.5,65.0,5.2
26.0,63.5,4.8"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == ["AIR_TEMP", "HUMIDITY", "WIND_SPEED"]
        # Should still recognize weather fields but no timestamp
        assert "ts_ms" not in inspect["recognized"]
        assert inspect["recognized"]["temp_c"] == "AIR_TEMP"
        assert inspect["recognized"]["humidity_pct"] == "HUMIDITY"
        assert inspect["recognized"]["wind_kph"] == "WIND_SPEED"
    
    def test_inspect_weather_partial_fields(self):
        """Test weather inspector with only some weather fields."""
        csv_content = """TIME_UTC_SECONDS,AIR_TEMP
1722838223,25.5
1722838283,26.0"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["headers"] == ["TIME_UTC_SECONDS", "AIR_TEMP"]
        # Check standardized field mappings
        assert inspect["recognized"]["ts_ms"] == "TIME_UTC_SECONDS"
        assert inspect["recognized"]["temp_c"] == "AIR_TEMP"
        # Should not have humidity or wind fields
        assert "humidity_pct" not in inspect["recognized"]
        assert "wind_kph" not in inspect["recognized"]