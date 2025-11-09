"""Tests for sparklines data contract stability."""

import json
import pytest
from pathlib import Path

from tracknarrator.schema import SessionBundle
from tracknarrator.events import build_sparklines
from tracknarrator.api import app
from fastapi.testclient import TestClient

# Load the sample bundle
BUNDLE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "bundle_sample_barber.json"


class TestSparklinesContract:
    """Test cases for sparklines data contract stability."""
    
    def setup_method(self):
        """Set up test data before each test."""
        self.client = TestClient(app)
        
        # Load and seed the sample bundle
        with open(BUNDLE_PATH, 'r') as f:
            bundle_data = json.load(f)
        
        bundle = SessionBundle(**bundle_data)
        session_id = bundle.session.id
        
        # Seed the bundle
        response = self.client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        self.session_id = session_id
    
    def test_sparklines_api_contract(self):
        """Test that sparklines API endpoint has stable contract."""
        response = self.client.get(f"/session/{self.session_id}/sparklines")
        
        assert response.status_code == 200
        sparklines = response.json()
        
        # Check required top-level keys
        required_keys = ["laps_ms", "sections_ms", "speed_series"]
        for key in required_keys:
            assert key in sparklines, f"Missing required key: {key}"
        
        # Check laps_ms structure
        assert isinstance(sparklines["laps_ms"], list), "laps_ms should be a list"
        for lap_time in sparklines["laps_ms"]:
            assert isinstance(lap_time, (int, float)), f"lap_time should be numeric: {lap_time}"
        
        # Check sections_ms structure
        assert isinstance(sparklines["sections_ms"], dict), "sections_ms should be a dict"
        
        # Check expected section names from config
        from tracknarrator.config import DEFAULT_SECTION_LABELS
        for section_name in DEFAULT_SECTION_LABELS:
            assert section_name in sparklines["sections_ms"], f"Missing section: {section_name}"
            assert isinstance(sparklines["sections_ms"][section_name], list), f"Section {section_name} should be a list"
            
            # Check section values
            for section_time in sparklines["sections_ms"][section_name]:
                if section_time is not None:
                    assert isinstance(section_time, (int, float)), f"Section time should be numeric: {section_time}"
        
        # Check speed_series structure
        assert isinstance(sparklines["speed_series"], list), "speed_series should be a list"
        for speed_point in sparklines["speed_series"]:
            assert "ts_ms" in speed_point, "Missing ts_ms in speed_point"
            assert "speed_kph" in speed_point, "Missing speed_kph in speed_point"
            assert isinstance(speed_point["ts_ms"], int), f"ts_ms should be int: {speed_point['ts_ms']}"
            assert isinstance(speed_point["speed_kph"], (int, float)), f"speed_kph should be numeric: {speed_point['speed_kph']}"
    
    def test_sparklines_function_contract(self):
        """Test that build_sparklines function has stable contract."""
        # Load bundle directly
        with open(BUNDLE_PATH, 'r') as f:
            bundle_data = json.load(f)
        
        bundle = SessionBundle(**bundle_data)
        sparklines = build_sparklines(bundle)
        
        # Check required top-level keys
        required_keys = ["laps_ms", "sections_ms", "speed_series"]
        for key in required_keys:
            assert key in sparklines, f"Missing required key: {key}"
        
        # Check laps_ms structure
        assert isinstance(sparklines["laps_ms"], list), "laps_ms should be a list"
        for lap_time in sparklines["laps_ms"]:
            assert isinstance(lap_time, (int, float)), f"lap_time should be numeric: {lap_time}"
        
        # Check sections_ms structure
        assert isinstance(sparklines["sections_ms"], dict), "sections_ms should be a dict"
        
        # Check expected section names from config
        from tracknarrator.config import DEFAULT_SECTION_LABELS
        for section_name in DEFAULT_SECTION_LABELS:
            assert section_name in sparklines["sections_ms"], f"Missing section: {section_name}"
            assert isinstance(sparklines["sections_ms"][section_name], list), f"Section {section_name} should be a list"
            
            # Check section values
            for section_time in sparklines["sections_ms"][section_name]:
                if section_time is not None:
                    assert isinstance(section_time, (int, float)), f"Section time should be numeric: {section_time}"
        
        # Check speed_series structure
        assert isinstance(sparklines["speed_series"], list), "speed_series should be a list"
        for speed_point in sparklines["speed_series"]:
            assert "ts_ms" in speed_point, "Missing ts_ms in speed_point"
            assert "speed_kph" in speed_point, "Missing speed_kph in speed_point"
            assert isinstance(speed_point["ts_ms"], int), f"ts_ms should be int: {speed_point['ts_ms']}"
            assert isinstance(speed_point["speed_kph"], (int, float)), f"speed_kph should be numeric: {speed_point['speed_kph']}"
    
    def test_sparklines_empty_data(self):
        """Test sparklines with empty/minimal data."""
        # Create empty bundle
        empty_bundle_data = {
            "session": {
                "id": "empty-test",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [],
            "sections": [],
            "telemetry": [],
            "weather": []
        }
        
        empty_bundle = SessionBundle(**empty_bundle_data)
        sparklines = build_sparklines(empty_bundle)
        
        # Should still have correct structure even with empty data
        required_keys = ["laps_ms", "sections_ms", "speed_series"]
        for key in required_keys:
            assert key in sparklines, f"Missing required key: {key}"
        
        # Empty data should have empty lists
        assert sparklines["laps_ms"] == []
        assert sparklines["speed_series"] == []
        
        # Sections should have all expected labels but empty lists
        from tracknarrator.config import DEFAULT_SECTION_LABELS
        for section_name in DEFAULT_SECTION_LABELS:
            assert section_name in sparklines["sections_ms"]
            assert sparklines["sections_ms"][section_name] == []
    
    def test_sparklines_data_types_consistency(self):
        """Test that sparklines data types are consistent."""
        # Load bundle directly
        with open(BUNDLE_PATH, 'r') as f:
            bundle_data = json.load(f)
        
        bundle = SessionBundle(**bundle_data)
        sparklines = build_sparklines(bundle)
        
        # All numeric values should be consistent types
        if sparklines["laps_ms"]:
            lap_types = set(type(lap) for lap in sparklines["laps_ms"])
            # Should all be the same type (all int or all float)
            assert len(lap_types) <= 1, f"lap_ms has mixed types: {lap_types}"
        
        # Check section data types
        from tracknarrator.config import DEFAULT_SECTION_LABELS
        for section_name in DEFAULT_SECTION_LABELS:
            section_data = sparklines["sections_ms"][section_name]
            non_null_values = [v for v in section_data if v is not None]
            if non_null_values:
                section_types = set(type(v) for v in non_null_values)
                # Should all be the same type
                assert len(section_types) <= 1, f"Section {section_name} has mixed types: {section_types}"