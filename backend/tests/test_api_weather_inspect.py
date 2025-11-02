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
    
    def test_inspect_weather_with_ts(self):
        """Test weather inspector with standard ts field."""
        csv_content = """TIME_UTC_SECONDS,AIR_TEMP,TRACK_TEMP,HUMIDITY,PRESSURE,WIND_SPEED,WIND_DIRECTION,RAIN
1722838223,25.5,35.2,65.0,1013.25,5.2,180.0,0
1722838283,26.0,36.1,63.5,1013.15,4.8,175.5,0"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["header"] == ["TIME_UTC_SECONDS", "AIR_TEMP", "TRACK_TEMP", "HUMIDITY", "PRESSURE", "WIND_SPEED", "WIND_DIRECTION", "RAIN"]
        assert inspect["recognized"]["ts"] == "TIME_UTC_SECONDS"
        assert inspect["recognized"]["temp"] == "AIR_TEMP"
        assert inspect["recognized"]["humidity"] == "HUMIDITY"
        assert inspect["recognized"]["wind"] == "WIND_SPEED"
        assert len(inspect["reasons"]) > 0
        assert any("Timestamp field found" in reason for reason in inspect["reasons"])
    
    def test_inspect_weather_with_ts_ms(self):
        """Test weather inspector with ts_ms field."""
        csv_content = """ts_ms,AIR_TEMPERATURE,HUMIDITY_PCT,WIND
1722838223000,25.5,65.0,5.2
1722838283000,26.0,63.5,4.8"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["header"] == ["ts_ms", "AIR_TEMPERATURE", "HUMIDITY_PCT", "WIND"]
        assert inspect["recognized"]["ts"] == "ts_ms"
        assert inspect["recognized"]["temp"] == "AIR_TEMPERATURE"
        assert inspect["recognized"]["humidity"] == "HUMIDITY_PCT"
        assert inspect["recognized"]["wind"] == "WIND"
        assert len(inspect["reasons"]) > 0
        assert any("Timestamp field found" in reason for reason in inspect["reasons"])
    
    def test_inspect_weather_with_utc(self):
        """Test weather inspector with UTC timestamp field."""
        csv_content = """UTC,AIR_TEMP,HUMIDITY,WIND_SPEED
1722838223,25.5,65.0,5.2
1722838223,26.0,63.5,4.8
1722838283,25.8,64.0,5.0"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["header"] == ["UTC", "AIR_TEMP", "HUMIDITY", "WIND_SPEED"]
        assert inspect["recognized"]["ts"] == "UTC"
        assert inspect["recognized"]["temp"] == "AIR_TEMP"
        assert inspect["recognized"]["humidity"] == "HUMIDITY"
        assert inspect["recognized"]["wind"] == "WIND_SPEED"
        assert len(inspect["reasons"]) > 0
        assert any("Timestamp field found" in reason for reason in inspect["reasons"])
    
    def test_inspect_weather_with_semicolon_delimiter(self):
        """Test weather inspector with semicolon delimiter."""
        csv_content = """TIME_UTC_SECONDS;AIR_TEMP;HUMIDITY;WIND_SPEED
1722838223;25.5;65.0;5.2
1722838283;26.0;63.5;4.8"""
        
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["header"] == ["TIME_UTC_SECONDS", "AIR_TEMP", "HUMIDITY", "WIND_SPEED"]
        assert inspect["recognized"]["ts"] == "TIME_UTC_SECONDS"
        assert inspect["recognized"]["temp"] == "AIR_TEMP"
        assert inspect["recognized"]["humidity"] == "HUMIDITY"
        assert inspect["recognized"]["wind"] == "WIND_SPEED"
        assert len(inspect["reasons"]) > 0
        assert any("Timestamp field found" in reason for reason in inspect["reasons"])
    
    def test_inspect_weather_empty_file(self):
        """Test weather inspector with empty file."""
        response = self.client.post(
            "/dev/inspect/weather",
            files={"file": ("weather.csv", "", "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["header"] == []
        assert inspect["recognized"] == {}
        assert len(inspect["reasons"]) > 0
        assert any("No timestamp field found" in reason for reason in inspect["reasons"])
    
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
        assert inspect["header"] == ["invalid", "csv", "format"]
        assert inspect["recognized"] == {}
        assert len(inspect["reasons"]) > 0
        assert any("No timestamp field found" in reason for reason in inspect["reasons"])
    
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
        assert inspect["header"] == ["AIR_TEMP", "HUMIDITY", "WIND_SPEED"]
        # Should still recognize weather fields but no timestamp
        assert "ts" not in inspect["recognized"]
        assert inspect["recognized"]["temp"] == "AIR_TEMP"
        assert inspect["recognized"]["humidity"] == "HUMIDITY"
        assert inspect["recognized"]["wind"] == "WIND_SPEED"
        assert len(inspect["reasons"]) > 0
        assert any("No timestamp field found" in reason for reason in inspect["reasons"])
    
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
        assert inspect["header"] == ["TIME_UTC_SECONDS", "AIR_TEMP"]
        assert inspect["recognized"]["ts"] == "TIME_UTC_SECONDS"
        assert inspect["recognized"]["temp"] == "AIR_TEMP"
        # Should not have humidity or wind fields
        assert "humidity" not in inspect["recognized"]
        assert "wind" not in inspect["recognized"]
        assert len(inspect["reasons"]) > 0
        assert any("Timestamp field found" in reason for reason in inspect["reasons"])
        assert any("Weather field 'humidity' not found" in reason for reason in inspect["reasons"])
        assert any("Weather field 'wind' not found" in reason for reason in inspect["reasons"])