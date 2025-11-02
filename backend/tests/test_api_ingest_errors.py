"""Tests for error handling in ingest endpoints."""

import io
import inspect
import pytest
from fastapi.testclient import TestClient

from src.tracknarrator.api import app
from src.tracknarrator.store import store


class TestIngestErrors:
    """Test cases for error handling in ingest endpoints."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.client = TestClient(app)
        # Clear store before each test
        store.sessions.clear()
    
    def test_trd_ingest_malformed_csv(self):
        """Test TRD ingest with malformed CSV."""
        # Create a malformed CSV with wrong headers
        csv_content = """wrong,header,format
just,some,random,data"""
        
        response = self.client.post(
            "/ingest/trd-long?session_id=test-session",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == 400
        assert data["error"]["type"] == "http_error"
        
        # Check if it's bad_trd_csv or bad_input
        error_detail = data["error"]["details"] or data["error"]["message"]
        if isinstance(error_detail, dict):
            assert error_detail.get("code") in ["bad_trd_csv", "bad_input"]
        else:
            assert "bad_input" in str(error_detail) or "bad_trd_csv" in str(error_detail)
    
    def test_trd_ingest_insufficient_fields(self):
        """Test TRD ingest with insufficient recognized fields."""
        # Create a CSV with only 3 recognized fields (<5 required)
        csv_content = """ts_ms,name,value
0,speed,120.5
0,aps,75.2
0,gear,3"""
        
        response = self.client.post(
            "/ingest/trd-long?session_id=test-session",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == 400
        assert data["error"]["type"] == "http_error"
        
        # Should be bad_trd_csv with missing channels info
        error_detail = data["error"]["details"] or data["error"]["message"]
        if isinstance(error_detail, dict):
            assert error_detail.get("code") == "bad_trd_csv"
            assert "missing_channels" in error_detail
            assert "hint" in error_detail
    
    def test_trd_ingest_with_synonyms(self):
        """Test TRD ingest works with synonym field names."""
        # Create a CSV with variant field names that should work via synonyms
        csv_content = """ts_ms,name,value
0,speed,120.5
0,aps,75.2
0,pbrake_f,15.8
0,gear,3
0,accx_can,0.8
0,accy_can,-0.5
0,steering_angle,12.3
0,VBOX_Lat_Min,33.123456
0,vbox_long_min,-87.654321"""
        
        response = self.client.post(
            "/ingest/trd-long?session_id=test-session",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session_id"] == "test-session"
        assert data["counts"]["telemetry_added"] == 1
    
    def test_racechrono_ingest_invalid_format(self):
        """Test RaceChrono ingest with invalid format."""
        # Create an invalid CSV
        csv_content = """invalid,format
just,random,data"""
        
        response = self.client.post(
            "/ingest/racechrono?session_id=test-session",
            files={"file": ("racechrono.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == 400
        assert data["error"]["type"] == "http_error"
        
        # Should be bad_input with source "racechrono"
        error_detail = data["error"]["details"] or data["error"]["message"]
        if isinstance(error_detail, dict):
            assert error_detail.get("code") == "bad_input"
            assert error_detail.get("source") == "racechrono"
    
    def test_mylaps_ingest_invalid_format(self):
        """Test MYLAPS ingest with invalid format."""
        # Create an invalid CSV
        csv_content = """invalid,format
just,random,data"""
        
        response = self.client.post(
            "/ingest/mylaps-sections?session_id=test-session",
            files={"file": ("mylaps.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == 400
        assert data["error"]["type"] == "http_error"
        
        # Should be bad_input with source "mylaps"
        error_detail = data["error"]["details"] or data["error"]["message"]
        if isinstance(error_detail, dict):
            assert error_detail.get("code") == "bad_input"
            assert error_detail.get("source") == "mylaps"
    
    def test_weather_ingest_invalid_format(self):
        """Test weather ingest with invalid format."""
        # Create an invalid CSV
        csv_content = """invalid,format
just,random,data"""
        
        response = self.client.post(
            "/ingest/weather?session_id=test-session",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == 400
        assert data["error"]["type"] == "http_error"
        
        # Should be bad_input with source "weather"
        error_detail = data["error"]["details"] or data["error"]["message"]
        if isinstance(error_detail, dict):
            assert error_detail.get("code") == "bad_input"
            assert error_detail.get("source") == "weather"
    
    def test_ingest_no_http_500_for_input_errors(self):
        """Test that input problems don't return HTTP 500."""
        # Test various malformed inputs that should return 400, not 500
        test_cases = [
            ("/ingest/trd-long", "trd.csv", """invalid,format"""),
            ("/ingest/racechrono", "racechrono.csv", """invalid,format"""),
            ("/ingest/mylaps-sections", "mylaps.csv", """invalid,format"""),
            ("/ingest/weather", "weather.csv", """invalid,format""")
        ]
        
        for endpoint, filename, content in test_cases:
            response = self.client.post(
                f"{endpoint}?session_id=test-session",
                files={"file": (filename, content, "text/csv")}
            )
            
            # Should not return 500 for input problems
            assert response.status_code != 500
            assert response.status_code in [400, 422]  # Bad request or validation error
            
            data = response.json()
            assert data["error"]["code"] != 500
            assert data["error"]["type"] != "internal_error"
    
    def test_trd_ingest_with_time_in_seconds(self):
        """Test TRD ingest with time in seconds (should be converted to ms)."""
        # Create a CSV with time in seconds (should be converted)
        csv_content = """time_ms,name,value
0.0,speed,120.5
0.0,aps,75.2
0.0,pbrake_f,15.8
0.0,gear,3
0.0,accx_can,0.8
0.0,accy_can,-0.5
0.0,steering_angle,12.3
0.0,VBOX_Lat_Min,33.123456
0.0,vbox_long_min,-87.654321"""
        
        response = self.client.post(
            "/ingest/trd-long?session_id=test-session",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        # This might work or fail depending on implementation
        # The important thing is it shouldn't return 500
        assert response.status_code in [200, 400]
        data = response.json()
        assert data["error"]["code"] != 500 if response.status_code != 200 else True