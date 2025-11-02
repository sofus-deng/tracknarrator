"""Tests for TRD inspector API endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.tracknarrator.api import app
from src.tracknarrator.store import store


class TestTRDInspectAPI:
    """Test cases for TRD inspector API endpoint."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.client = TestClient(app)
        # Clear store before each test
        store.sessions.clear()
    
    def test_inspect_trd_long_with_synonyms(self):
        """Test TRD inspector with variant field names using synonyms."""
        # Create a tiny CSV with VBOX_Long_Min and steering_angle (lowercase)
        csv_content = """ts_ms,name,value
0,speed,120.5
0,aps,75.2
0,pbrake_f,15.8
0,gear,3
0,accx_can,0.8
0,accy_can,-0.5
0,steering_angle,12.3
0,VBOX_Lat_Min,33.123456
0,VBOX_Long_Min,-87.654321
1000,speed,122.1
1000,aps,78.5
1000,pbrake_f,14.2
1000,gear,3
1000,accx_can,0.9
1000,accy_can,-0.4
1000,Steering_Angle,13.1
1000,VBOX_Lat_Min,33.123457
1000,vbox_long_min,-87.654322"""
        
        response = self.client.post(
            "/dev/inspect/trd-long",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        # Check that recognized channels include mapped names via synonyms
        assert "Steering_Angle" in inspect["recognized_channels"]  # via steering_angle synonym
        assert "VBOX_Long_Minutes" in inspect["recognized_channels"]  # via vbox_long_min synonym
        assert "speed" in inspect["recognized_channels"]
        assert "aps" in inspect["recognized_channels"]
        assert "gear" in inspect["recognized_channels"]
        
        # Check that min_fields_per_ts is >= 5 when channels provided
        assert inspect["min_fields_per_ts"] >= 5
        assert inspect["timestamps"] == 2  # Two distinct timestamps
        assert inspect["rows_total"] == 18  # 9 rows per timestamp
    
    def test_inspect_trd_long_with_trd_format(self):
        """Test TRD inspector with original TRD format."""
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
            "/dev/inspect/trd-long",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        # Check recognized channels
        assert "speed" in inspect["recognized_channels"]
        assert "aps" in inspect["recognized_channels"]
        assert "Steering_Angle" in inspect["recognized_channels"]
        assert "VBOX_Lat_Min" in inspect["recognized_channels"]
        assert "VBOX_Long_Minutes" in inspect["recognized_channels"]
        
        # Check statistics
        assert inspect["timestamps"] == 1  # One distinct timestamp
        assert inspect["rows_total"] == 9  # 9 rows total
        assert inspect["min_fields_per_ts"] == 9  # All 9 fields for the timestamp
    
    def test_inspect_trd_long_with_missing_channels(self):
        """Test TRD inspector with missing expected channels."""
        csv_content = """ts_ms,name,value
0,speed,120.5
0,aps,75.2
0,unknown_channel,42.0"""
        
        response = self.client.post(
            "/dev/inspect/trd-long",
            files={"file": ("trd.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        # Check recognized and missing channels
        assert "speed" in inspect["recognized_channels"]
        assert "aps" in inspect["recognized_channels"]
        assert "unknown_channel" in inspect["unrecognized_names"]
        
        # Should be missing many expected channels
        assert len(inspect["missing_expected"]) > 5
        assert "gear" in inspect["missing_expected"]
        assert "Steering_Angle" in inspect["missing_expected"]
    
    def test_inspect_trd_long_invalid_format(self):
        """Test TRD inspector with invalid CSV format."""
        csv_content = """invalid,csv,format
just,some,random,text"""
        
        response = self.client.post(
            "/dev/inspect/trd-long",
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
    
    def test_inspect_trd_long_no_file(self):
        """Test TRD inspector with no file uploaded."""
        response = self.client.post("/dev/inspect/trd-long")
        
        assert response.status_code == 422  # Validation error
    
    def test_inspect_trd_long_empty_file(self):
        """Test TRD inspector with empty file."""
        response = self.client.post(
            "/dev/inspect/trd-long",
            files={"file": ("trd.csv", "", "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        
        inspect = data["inspect"]
        assert inspect["recognized_channels"] == []
        assert inspect["rows_total"] == 0
        assert inspect["timestamps"] == 0
        assert inspect["min_fields_per_ts"] == 0