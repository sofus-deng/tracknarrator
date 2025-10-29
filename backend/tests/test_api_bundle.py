"""Tests for API bundle endpoint integration."""

import io

import pytest
from fastapi.testclient import TestClient

from src.tracknarrator.api import app
from src.tracknarrator.store import store


class TestAPIBundle:
    """Test cases for API bundle endpoint integration."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear the store
        store.sessions.clear()
        
        # Create test client
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
    
    def test_config_endpoint(self):
        """Test config endpoint."""
        response = self.client.get("/config")
        assert response.status_code == 200
        assert "ai_native" in response.json()
        assert isinstance(response.json()["ai_native"], bool)
    
    def test_full_ingest_and_bundle_workflow(self):
        """Test complete workflow: ingest all data types and retrieve bundle."""
        session_id = "test-session-full"
        
        # 1. Ingest MYLAPS sections
        mylaps_csv = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456
2;1;1:22.123;0:11.234;0:24.567;0:37.890;0:51.123;1:04.456;1:22.123"""
        
        response = self.client.post(
            f"/ingest/mylaps-sections?session_id={session_id}",
            files={"file": ("mylaps.csv", mylaps_csv, "text/csv")}
        )
        assert response.status_code == 200
        mylaps_result = response.json()
        assert mylaps_result["status"] == "success"
        assert mylaps_result["counts"]["laps_added"] == 2
        assert mylaps_result["counts"]["sections_added"] == 12
        
        # 2. Ingest TRD telemetry
        trd_csv = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Lat_Min,33.123456,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Long_Minutes,-87.654321,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,speed,122.1,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,aps,78.5,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,pbrake_f,14.2,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,gear,3,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,accx_can,0.9,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,accy_can,-0.4,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,Steering_Angle,13.1,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,VBOX_Lat_Min,33.123457,2025-04-04T18:10:24.456Z,1,1
2025-04-04T18:10:24.456Z,1,session1,session1,trd,2025-04-04T18:10:24.456Z,123,1,VBOX_Long_Minutes,-87.654322,2025-04-04T18:10:24.456Z,1,1"""
        
        response = self.client.post(
            f"/ingest/trd-long?session_id={session_id}",
            files={"file": ("trd.csv", trd_csv, "text/csv")}
        )
        assert response.status_code == 200
        trd_result = response.json()
        assert trd_result["status"] == "success"
        assert trd_result["counts"]["telemetry_added"] == 2
        
        # 3. Ingest weather data
        weather_csv = """TIME_UTC_SECONDS;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;WIND_SPEED;WIND_DIRECTION;RAIN
1722838223;25.5;35.2;65.0;1013.25;5.2;180.0;0
1722838283;26.0;36.1;63.5;1013.15;4.8;175.5;0"""
        
        response = self.client.post(
            f"/ingest/weather?session_id={session_id}",
            files={"file": ("weather.csv", weather_csv, "text/csv")}
        )
        assert response.status_code == 200
        weather_result = response.json()
        assert weather_result["status"] == "success"
        assert weather_result["counts"]["weather_added"] == 2
        
        # 4. Retrieve the complete bundle
        response = self.client.get(f"/session/{session_id}/bundle")
        assert response.status_code == 200
        bundle = response.json()
        
        # Verify bundle structure
        assert "session" in bundle
        assert "laps" in bundle
        assert "sections" in bundle
        assert "telemetry" in bundle
        assert "weather" in bundle
        
        # Verify session data
        assert bundle["session"]["id"] == session_id
        assert bundle["session"]["schema_version"] == "0.1.2"
        
        # Verify counts
        assert len(bundle["laps"]) == 2
        assert len(bundle["sections"]) == 12  # 2 laps * 6 sections
        assert len(bundle["telemetry"]) == 2
        assert len(bundle["weather"]) == 2
        
        # Verify lap data structure
        lap = bundle["laps"][0]
        assert lap["session_id"] == session_id
        assert lap["lap_no"] == 1
        assert lap["driver"] == "No.1"
        assert lap["laptime_ms"] == 83456
        
        # Verify section data structure
        section = bundle["sections"][0]
        assert section["session_id"] == session_id
        assert section["lap_no"] == 1
        assert section["name"] in ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]
        assert "t_start_ms" in section
        assert "t_end_ms" in section
        assert section["meta"]["source"] == "mylaps"
        
        # Verify telemetry data structure
        telemetry = bundle["telemetry"][0]
        assert telemetry["session_id"] == session_id
        assert telemetry["ts_ms"] == 1743790223456
        assert telemetry["speed_kph"] == 120.5
        assert telemetry["throttle_pct"] == 75.2
        assert telemetry["brake_bar"] == 15.8
        assert telemetry["gear"] == 3
        assert telemetry["acc_long_g"] == 0.8
        assert telemetry["acc_lat_g"] == -0.5
        assert telemetry["steer_deg"] == 12.3
        assert telemetry["lat_deg"] == 33.123456
        assert telemetry["lon_deg"] == -87.654321
        
        # Verify weather data structure
        weather = bundle["weather"][0]
        assert weather["session_id"] == session_id
        assert weather["ts_ms"] == 1722838223000
        assert weather["air_temp_c"] == 25.5
        assert weather["track_temp_c"] == 35.2
        assert weather["humidity_pct"] == 65.0
        assert weather["pressure_hpa"] == 1013.25
        assert weather["wind_speed"] == 5.2
        assert weather["wind_dir_deg"] == 180.0
        assert weather["rain_flag"] == 0
    
    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        response = self.client.get("/session/nonexistent/bundle")
        assert response.status_code == 404
        error = response.json()
        assert error["error"]["code"] == 404
        assert "not found" in error["error"]["message"]
    
    def test_ingest_invalid_file(self):
        """Test ingesting an invalid file."""
        invalid_csv = "LAP_NUMBER,DRIVER_NUMBER\n1,invalid"
        
        response = self.client.post(
            "/ingest/mylaps-sections?session_id=test",
            files={"file": ("invalid.csv", invalid_csv, "text/csv")}
        )
        assert response.status_code == 400
        error = response.json()
        assert error["error"]["code"] == 400
        assert "Import failed" in error["error"]["message"]
    
    def test_duplicate_ingest_idempotency(self):
        """Test that ingesting the same data twice is idempotent."""
        session_id = "test-duplicate"
        
        # First ingestion
        mylaps_csv = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        response = self.client.post(
            f"/ingest/mylaps-sections?session_id={session_id}",
            files={"file": ("mylaps.csv", mylaps_csv, "text/csv")}
        )
        assert response.status_code == 200
        first_result = response.json()
        assert first_result["counts"]["laps_added"] == 1
        assert first_result["counts"]["sections_added"] == 6
        
        # Second ingestion (same data)
        response = self.client.post(
            f"/ingest/mylaps-sections?session_id={session_id}",
            files={"file": ("mylaps.csv", mylaps_csv, "text/csv")}
        )
        assert response.status_code == 200
        second_result = response.json()
        # Should not add new data due to deduplication
        assert second_result["counts"]["laps_added"] == 0
        assert second_result["counts"]["sections_added"] == 0
        
        # Verify only one lap and 6 sections exist
        response = self.client.get(f"/session/{session_id}/bundle")
        assert response.status_code == 200
        bundle = response.json()
        assert len(bundle["laps"]) == 1
        assert len(bundle["sections"]) == 6
    
    def test_merge_conflict_resolution(self):
        """Test merge conflict resolution between different sources."""
        session_id = "test-conflict"
        
        # Ingest MYLAPS data first (lower precedence for telemetry)
        mylaps_csv = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        response = self.client.post(
            f"/ingest/mylaps-sections?session_id={session_id}",
            files={"file": ("mylaps.csv", mylaps_csv, "text/csv")}
        )
        assert response.status_code == 200
        
        # Ingest TRD data (higher precedence for telemetry)
        trd_csv = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1"""
        
        response = self.client.post(
            f"/ingest/trd-long?session_id={session_id}",
            files={"file": ("trd.csv", trd_csv, "text/csv")}
        )
        assert response.status_code == 200
        
        # Verify session source was updated to higher precedence
        response = self.client.get(f"/session/{session_id}/bundle")
        assert response.status_code == 200
        bundle = response.json()
        # Session should keep original source since it was created first
        assert bundle["session"]["source"] == "mylaps_csv"