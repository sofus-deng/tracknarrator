"""Tests for TRD long CSV importer."""

import io
from datetime import datetime

import pytest

from src.tracknarrator.importers.trd_long_csv import TRDLongCSVImporter
from src.tracknarrator.schema import Telemetry


class TestTRDLongCSVImporter:
    """Test cases for TRD long CSV importer."""
    
    def test_import_basic_telemetry(self):
        """Test importing basic telemetry data with all required fields."""
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
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.warnings) == 0
        assert len(result.bundle.telemetry) == 1
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.session_id == "test-session"
        assert telemetry.ts_ms == 1743790223456  # 2025-04-04T18:10:23.456Z in ms
        assert telemetry.speed_kph == 120.5
        assert telemetry.throttle_pct == 75.2
        assert telemetry.brake_bar == 15.8
        assert telemetry.gear == 3
        assert telemetry.acc_long_g == 0.8
        assert telemetry.acc_lat_g == -0.5
        assert telemetry.steer_deg == 12.3
        assert telemetry.lat_deg == 33.123456
        assert telemetry.lon_deg == -87.654321
    
    def test_pbrake_fallback(self):
        """Test pbrake_r fallback when pbrake_f is missing."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_r,18.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.brake_bar == 18.2  # Should use pbrake_r fallback
    
    def test_throttle_clamping(self):
        """Test throttle percentage clamping to [0, 100]."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,150.0,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        telemetry = result.bundle.telemetry[0]
        assert telemetry.throttle_pct == 100.0  # Should be clamped to 100
    
    def test_outlier_rejection(self):
        """Test that outliers are set to None instead of clamped."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,500.0,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,15.0,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Lat_Min,33.123456,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Long_Minutes,-87.654321,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-15.0,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        telemetry = result.bundle.telemetry[0]
        assert telemetry.speed_kph is None  # 500 km/h is outside 0-350 range
        assert telemetry.acc_long_g is None  # 15g is outside ±10g range
        assert telemetry.acc_lat_g is None  # -15g is outside ±10g range
    
    def test_insufficient_fields_rejection(self):
        """Test that rows with <5 fields are rejected."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None  # Should fail due to insufficient fields
        assert len(result.warnings) > 0
    
    def test_unknown_telemetry_names_warning(self):
        """Test warning for unknown telemetry names."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,unknown_field,42.0,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert any("unknown_field" in warning for warning in result.warnings)
    
    def test_multiple_timestamps(self):
        """Test importing data with multiple timestamps."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,Steering_Angle,12.3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.460Z,1,session1,session1,trd,2025-04-04T18:10:23.460Z,123,1,speed,122.1,2025-04-04T18:10:23.460Z,1,1
2025-04-04T18:10:23.460Z,1,session1,session1,trd,2025-04-04T18:10:23.460Z,123,1,aps,78.5,2025-04-04T18:10:23.460Z,1,1
2025-04-04T18:10:23.460Z,1,session1,session1,trd,2025-04-04T18:10:23.460Z,123,1,pbrake_f,14.2,2025-04-04T18:10:23.460Z,1,1
2025-04-04T18:10:23.460Z,1,session1,session1,trd,2025-04-04T18:10:23.460Z,123,1,gear,3,2025-04-04T18:10:23.460Z,1,1
2025-04-04T18:10:23.460Z,1,session1,session1,trd,2025-04-04T18:10:23.460Z,123,1,accx_can,0.9,2025-04-04T18:10:23.460Z,1,1
2025-04-04T18:10:23.460Z,1,session1,session1,trd,2025-04-04T18:10:23.460Z,123,1,accy_can,-0.4,2025-04-04T18:10:23.460Z,1,1
2025-04-04T18:10:23.460Z,1,session1,session1,trd,2025-04-04T18:10:23.460Z,123,1,Steering_Angle,13.1,2025-04-04T18:10:23.460Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 2  # Should have 2 telemetry points
        
        # Check first timestamp
        telemetry1 = result.bundle.telemetry[0]
        assert telemetry1.ts_ms == 1743790223456
        assert telemetry1.speed_kph == 120.5
        
        # Check second timestamp
        telemetry2 = result.bundle.telemetry[1]
        assert telemetry2.ts_ms == 1743790223460  # 2025-04-04T18:10:23.460Z in ms
        assert telemetry2.speed_kph == 122.1
    
    def test_min_fields_gate_with_valid_fields(self):
        """Test that rows with ≥5 mapped numeric fields are kept."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.telemetry) == 1  # Should keep the row with 6 valid fields
    
    def test_min_fields_gate_with_outliers(self):
        """Test that outliers don't count toward the ≥5 mapped numeric fields requirement."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,500.0,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-15.0,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None  # Should fail due to only 4 valid fields (2 outliers)
        assert len(result.warnings) > 0
    
    def test_telemetry_deduplication_within_1ms(self):
        """Test telemetry de-duplication within ±1 ms buckets."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,speed,122.1,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,aps,78.5,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,pbrake_f,14.2,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,gear,3,2025-04-04T18:10:23.457Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should have 1 telemetry point (second timestamp has fewer fields)
        assert len(result.bundle.telemetry) == 1
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 1743790223456  # Should use the timestamp with more fields
        assert telemetry.speed_kph == 120.5
        assert telemetry.throttle_pct == 75.2
        assert telemetry.brake_bar == 15.8
        assert telemetry.gear == 3
        assert telemetry.acc_long_g == 0.8
        assert telemetry.acc_lat_g == -0.5
    
    def test_telemetry_deduplication_keeps_more_fields(self):
        """Test that de-duplication keeps the row with more non-None fields."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,speed,122.1,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,aps,78.5,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,pbrake_f,14.2,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,gear,3,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,accx_can,0.9,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,accy_can,-0.4,2025-04-04T18:10:23.457Z,1,1
2025-04-04T18:10:23.457Z,1,session1,session1,trd,2025-04-04T18:10:23.457Z,123,1,Steering_Angle,13.1,2025-04-04T18:10:23.457Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should have 1 telemetry point (second timestamp has more fields)
        assert len(result.bundle.telemetry) == 1
        
        telemetry = result.bundle.telemetry[0]
        assert telemetry.ts_ms == 1743790223457  # Should use the timestamp with more fields
        assert telemetry.speed_kph == 122.1
        assert telemetry.throttle_pct == 78.5
        assert telemetry.brake_bar == 14.2
        assert telemetry.gear == 3
        assert telemetry.acc_long_g == 0.9
        assert telemetry.acc_lat_g == -0.4
        assert telemetry.steer_deg == 13.1
    
    def test_vbox_coordinate_bounds_validation(self):
        """Test VBOX coordinate bounds validation."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Lat_Min,91.0,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Long_Minutes,181.0,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        telemetry = result.bundle.telemetry[0]
        # Out-of-bounds coordinates should be set to None
        assert telemetry.lat_deg is None  # 91.0 is outside [-90, 90]
        assert telemetry.lon_deg is None  # 181.0 is outside [-180, 180]
    
    def test_vbox_coordinate_valid_bounds(self):
        """Test VBOX coordinates within valid bounds."""
        csv_content = """expire_at,lap,meta_event,meta_session,meta_source,meta_time,original_vehicle_id,outing,telemetry_name,telemetry_value,timestamp,vehicle_id,vehicle_number
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,speed,120.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,aps,75.2,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,pbrake_f,15.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,gear,3,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accx_can,0.8,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,accy_can,-0.5,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Lat_Min,33.123456,2025-04-04T18:10:23.456Z,1,1
2025-04-04T18:10:23.456Z,1,session1,session1,trd,2025-04-04T18:10:23.456Z,123,1,VBOX_Long_Minutes,-87.654321,2025-04-04T18:10:23.456Z,1,1"""
        
        file_obj = io.StringIO(csv_content)
        result = TRDLongCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        telemetry = result.bundle.telemetry[0]
        # Valid coordinates should be preserved
        assert telemetry.lat_deg == 33.123456  # Within [-90, 90]
        assert telemetry.lon_deg == -87.654321  # Within [-180, 180]