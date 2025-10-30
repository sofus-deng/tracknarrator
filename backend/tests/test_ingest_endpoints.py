"""Tests for all ingest endpoints."""

import io
import json

import pytest
from fastapi.testclient import TestClient

from src.tracknarrator.api import app
from src.tracknarrator.store import store


class TestIngestEndpoints:
    """Test cases for all ingest endpoints."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.client = TestClient(app)
        # Clear store before each test
        store.sessions.clear()
    
    def test_ingest_mylaps_sections(self):
        """Test MYLAPS sections ingest endpoint."""
        self.setup_method()
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        response = self.client.post(
            "/ingest/mylaps-sections?session_id=test-session",
            files={"file": ("mylaps.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session_id"] == "test-session"
        assert data["counts"]["laps_added"] == 1
        assert data["counts"]["sections_added"] == 6
    
    def test_ingest_trd_long(self):
        """Test TRD long ingest endpoint."""
        self.setup_method()
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Lat_Min,33.123456,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Long_Minutes,-87.654321,2025-04-04T18:10:23.456Z,1,1"""
        
        response = self.client.post(
            "/ingest/trd-long?session_id=test-session",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session_id"] == "test-session"
        assert data["counts"]["telemetry_added"] == 1
    
    def test_ingest_weather(self):
        """Test weather ingest endpoint."""
        self.setup_method()
        csv_content = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1714500000;25.5;35.2;65.0;1013.25;5.5;180.0;0"""
        
        response = self.client.post(
            "/ingest/weather?session_id=test-session",
            files={"file": ("weather.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session_id"] == "test-session"
        assert data["counts"]["weather_added"] == 1
    
    def test_ingest_racechrono(self):
        """Test RaceChrono ingest endpoint."""
        self.setup_method()
        csv_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%),Brake pos (%)
0.000,0.0,-87.654321,33.123456,0.0,0.0
1.000,50.5,-87.654322,33.123457,25.5,10.2
2.000,120.5,-87.654323,33.123458,75.2,50.8"""
        
        response = self.client.post(
            "/ingest/racechrono?session_id=test-session",
            files={"file": ("racechrono.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session_id"] == "test-session"
        assert data["counts"]["telemetry_added"] == 3
        # Should have warning about brake column
        assert any("brake_pos_pct not mapped" in w for w in data["warnings"])
    
    def test_ingest_racechrono_size_limit(self):
        """Test RaceChrono ingest endpoint size limit."""
        self.setup_method()
        # Create a large CSV (>10MB)
        large_content = "Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)\n"
        # Create content that will definitely exceed 10MB
        for i in range(200000):
            large_content += f"{i*0.1},{50.0 + i*0.001},-87.654321,33.123456,{25.0 + i*0.1}\n"
        
        response = self.client.post(
            "/ingest/racechrono?session_id=test-session",
            files={"file": ("large.csv", large_content, "text/csv")}
        )
        
        assert response.status_code == 413  # Request Entity Too Large
        data = response.json()
        assert "File too large" in data["error"]["message"]
    
    def test_get_session_bundle(self):
        """Test getting session bundle after ingesting data."""
        self.setup_method()
        # First ingest some data
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        self.client.post(
            "/ingest/mylaps-sections?session_id=test-session",
            files={"file": ("mylaps.csv", csv_content, "text/csv")}
        )
        
        # Then get the bundle
        response = self.client.get("/session/test-session/bundle")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["id"] == "test-session"
        assert len(data["laps"]) == 1
        assert len(data["sections"]) == 6
        assert data["laps"][0]["lap_no"] == 1
        assert data["laps"][0]["driver"] == "No.1"
    
    def test_multiple_ingests_varying_order(self):
        """Test multiple ingests in varying orders to test merge logic."""
        self.setup_method()
        session_id = "multi-source-session"
        
        # 1. Ingest RaceChrono first
        racechrono_content = """Time (s),Speed (km/h),Longitude,Latitude,Throttle pos (%)
0.000,50.0,-87.654321,33.123456,25.0
1.000,60.0,-87.654322,33.123457,50.0"""
        
        response = self.client.post(
            f"/ingest/racechrono?session_id={session_id}",
            files={"file": ("racechrono.csv", racechrono_content, "text/csv")}
        )
        assert response.status_code == 200
        racechrono_data = response.json()
        assert racechrono_data["counts"]["telemetry_added"] == 2
        
        # 2. Ingest TRD long second (should have higher precedence)
        trd_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,55.0,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.0,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,20.0,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Lat_Min,33.123456,1970-01-01T00:00:00.000Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Long_Minutes,-87.654321,1970-01-01T00:00:00.000Z,1,1"""
        
        response = self.client.post(
            f"/ingest/trd-long?session_id={session_id}",
            files={"file": ("trd.csv", trd_content, "text/csv")}
        )
        if response.status_code != 200:
            print(f"TRD ingest failed with status {response.status_code}")
            print(f"Response: {response.text}")
        assert response.status_code == 200
        trd_data = response.json()
        # Should update existing telemetry due to higher precedence
        assert trd_data["counts"]["telemetry_updated"] == 1
        
        # 3. Ingest weather data
        weather_content = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1714500000;25.5;35.2;65.0;1013.25;5.5;180.0;0"""
        
        response = self.client.post(
            f"/ingest/weather?session_id={session_id}",
            files={"file": ("weather.csv", weather_content, "text/csv")}
        )
        assert response.status_code == 200
        weather_data = response.json()
        assert weather_data["counts"]["weather_added"] == 1
        
        # 4. Ingest MYLAPS sections
        mylaps_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        response = self.client.post(
            f"/ingest/mylaps-sections?session_id={session_id}",
            files={"file": ("mylaps.csv", mylaps_content, "text/csv")}
        )
        assert response.status_code == 200
        mylaps_data = response.json()
        assert mylaps_data["counts"]["laps_added"] == 1
        assert mylaps_data["counts"]["sections_added"] == 6
        
        # 5. Get final bundle and verify deterministic totals
        response = self.client.get(f"/session/{session_id}/bundle")
        assert response.status_code == 200
        bundle = response.json()
        
        # Verify counts are deterministic
        assert len(bundle["laps"]) == 1
        assert len(bundle["sections"]) == 6
        assert len(bundle["telemetry"]) == 2  # 2 from RaceChrono
        assert len(bundle["weather"]) == 1
        
        # Verify telemetry data - TRD should override RaceChrono at same timestamp
        # Sort telemetry by timestamp to make test deterministic
        telemetry_list = sorted(bundle["telemetry"], key=lambda x: x["ts_ms"])
        telemetry = telemetry_list[0]  # Should be TRD data at 0ms (overrides RaceChrono)
        assert telemetry["speed_kph"] == 55.0  # TRD value (higher precedence)
        assert telemetry["throttle_pct"] == 75.0  # TRD value (higher precedence)
        assert telemetry["brake_bar"] == 20.0  # TRD value
    
    def test_ingest_with_different_delimiters(self):
        """Test ingesting files with different delimiters."""
        self.setup_method()
        # Test comma delimiter
        comma_csv = """LAP_NUMBER,DRIVER_NUMBER,LAP_TIME,IM1a,IM1,IM2a,IM2,IM3a,FL
1,1,1:23.456,0:12.345,0:25.678,0:38.901,0:52.234,1:05.567,1:23.456"""
        
        response = self.client.post(
            "/ingest/mylaps-sections?session_id=comma-test",
            files={"file": ("comma.csv", comma_csv, "text/csv")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["counts"]["laps_added"] == 1
        assert data["counts"]["sections_added"] == 6
        
        # Test semicolon delimiter
        semicolon_csv = """Time (s);Speed (km/h);Longitude;Latitude;Throttle pos (%)
0.000;50.0;-87.654321;33.123456;25.0
1.000;60.0;-87.654322;33.123457;50.0"""
        
        response = self.client.post(
            "/ingest/racechrono?session_id=semicolon-test",
            files={"file": ("semicolon.csv", semicolon_csv, "text/csv")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["counts"]["telemetry_added"] == 2
    
    def test_session_not_found(self):
        """Test getting bundle for non-existent session."""
        self.setup_method()
        response = self.client.get("/session/non-existent/bundle")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["error"]["message"].lower()
    
    def test_missing_session_id(self):
        """Test ingest endpoints without session_id."""
        self.setup_method()
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        response = self.client.post(
            "/ingest/mylaps-sections",
            files={"file": ("mylaps.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_csv_format(self):
        """Test ingest endpoints with invalid CSV format."""
        self.setup_method()
        invalid_csv = """This is not a valid CSV file
Just some random text"""
        
        response = self.client.post(
            "/ingest/mylaps-sections?session_id=invalid-test",
            files={"file": ("invalid.csv", invalid_csv, "text/csv")}
        )
        
        assert response.status_code == 400  # Bad request
        data = response.json()
        assert "Import failed" in data["error"]["message"]