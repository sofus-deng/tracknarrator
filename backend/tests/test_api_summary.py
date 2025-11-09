"""Tests for the session summary API endpoint."""

import json
import pytest
from pathlib import Path

from tracknarrator.schema import SessionBundle
from tracknarrator.api import app
from fastapi.testclient import TestClient

# Load the sample bundle
BUNDLE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "bundle_sample_barber.json"


class TestSessionSummaryAPI:
    """Test cases for the session summary API endpoint."""
    
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
    
    def test_get_session_summary_basic(self):
        """Test basic session summary endpoint functionality."""
        response = self.client.get(f"/session/{self.session_id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "events" in data
        assert "cards" in data
        assert "sparklines" in data
        
        # Check data types
        assert isinstance(data["events"], list)
        assert isinstance(data["cards"], list)
        assert isinstance(data["sparklines"], dict)
    
    def test_get_session_summary_events_structure(self):
        """Test that events have the expected structure."""
        response = self.client.get(f"/session/{self.session_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        events = data["events"]
        
        # Events should be empty for the sample bundle (insufficient data)
        assert isinstance(events, list)
        
        # If there were events, they should have the correct structure
        for event in events:
            assert "type" in event
            assert "lap_no" in event
            assert "severity" in event
            assert "summary" in event
            assert "meta" in event
            assert event["type"] in ["lap_outlier", "section_outlier", "position_change"]
            assert 0 <= event["severity"] <= 1
    
    def test_get_session_summary_cards_structure(self):
        """Test that cards have the expected v0 schema structure."""
        response = self.client.get(f"/session/{self.session_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        cards = data["cards"]
        
        # Cards should be empty for the sample bundle (insufficient data)
        assert isinstance(cards, list)
        
        # If there were cards, they should have the correct v0 schema
        for card in cards:
            # Check required v0 schema fields
            required_fields = ["event_id", "type", "lap_no", "title", "metric", "delta_ms", "icon", "severity", "ts_ms", "meta"]
            for field in required_fields:
                assert field in card, f"Missing required field: {field}"
            
            # Check field types
            assert isinstance(card["event_id"], str)
            assert isinstance(card["type"], str)
            assert card["lap_no"] is None or isinstance(card["lap_no"], int)
            assert isinstance(card["title"], str)
            assert isinstance(card["metric"], str)
            assert card["delta_ms"] is None or isinstance(card["delta_ms"], int)
            assert isinstance(card["icon"], str)
            assert isinstance(card["severity"], (int, float))
            assert 0 <= card["severity"] <= 1
            assert card["ts_ms"] is None or isinstance(card["ts_ms"], int)
            assert isinstance(card["meta"], dict)
            
            # Check event type validity
            assert card["type"] in ["lap_outlier", "section_outlier", "position_change"]
            # Check icon mapping
            icon_map = {"lap_outlier": "⏱️", "section_outlier": "📍", "position_change": "🏁"}
            assert card["icon"] in icon_map.values()
    
    def test_get_session_summary_sparklines_structure(self):
        """Test that sparklines have the expected structure."""
        response = self.client.get(f"/session/{self.session_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        sparklines = data["sparklines"]
        
        # Check required sparkline keys
        assert "laps_ms" in sparklines
        assert "sections_ms" in sparklines
        assert "speed_series" in sparklines
        
        # Check data types
        assert isinstance(sparklines["laps_ms"], list)
        assert isinstance(sparklines["sections_ms"], dict)
        assert isinstance(sparklines["speed_series"], list)
        
        # Check speed series structure if present
        for point in sparklines["speed_series"]:
            assert "ts_ms" in point
            assert "speed_kph" in point
            assert isinstance(point["ts_ms"], int)
            assert isinstance(point["speed_kph"], float)
    
    def test_get_session_summary_nonexistent_session(self):
        """Test summary endpoint with non-existent session."""
        response = self.client.get("/session/nonexistent-session")
        
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"] or "Not Found" in error_data["detail"]
    
    def test_get_session_summary_consistency(self):
        """Test that summary endpoint is consistent with individual endpoints."""
        # Get summary
        summary_response = self.client.get(f"/session/{self.session_id}/summary")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        
        # Get individual endpoints
        events_response = self.client.get(f"/session/{self.session_id}/events")
        assert events_response.status_code == 200
        events_data = events_response.json()
        
        sparklines_response = self.client.get(f"/session/{self.session_id}/sparklines")
        assert sparklines_response.status_code == 200
        sparklines_data = sparklines_response.json()
        
        # Compare data
        assert summary_data["events"] == events_data["top5"]
        assert summary_data["sparklines"] == sparklines_data
    
    def test_get_session_summary_with_enriched_data(self):
        """Test summary endpoint behavior with data that would generate events."""
        # Create a bundle that would generate events
        session_data = {
            "session": {
                "id": "enriched-test",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [
                {"session_id": "enriched-test", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000, "position": 5},
                {"session_id": "enriched-test", "lap_no": 2, "driver": "Driver1", "laptime_ms": 200000, "position": 3},  # Outlier
                {"session_id": "enriched-test", "lap_no": 3, "driver": "Driver1", "laptime_ms": 101000, "position": 1},
                {"session_id": "enriched-test", "lap_no": 4, "driver": "Driver1", "laptime_ms": 102000, "position": 2},
                {"session_id": "enriched-test", "lap_no": 5, "driver": "Driver1", "laptime_ms": 99000, "position": 1},
            ],
            "sections": [],
            "telemetry": [],
            "weather": []
        }
        
        # Add more laps for section analysis
        for lap_no in [6, 7, 8]:
            session_data["laps"].append({
                "session_id": "enriched-test", "lap_no": lap_no, "driver": "Driver1", 
                "laptime_ms": 100000 + lap_no * 1000, "position": 1
            })
        
        # Seed the data
        response = self.client.post("/dev/seed", json=session_data)
        assert response.status_code == 200
        
        # Get summary
        response = self.client.get("/session/enriched-test/summary")
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have data structure
        assert "events" in data
        assert "cards" in data
        assert "sparklines" in data
        
        # For this enriched data, we should have some events
        # (at least position changes if not lap outliers due to thresholds)
        assert isinstance(data["events"], list)
        assert isinstance(data["cards"], list)
        assert isinstance(data["sparklines"], dict)
        
        # Sparklines should have lap times
        assert len(data["sparklines"]["laps_ms"]) > 0
    
    def test_get_session_summary_response_format(self):
        """Test that the response format is stable and JSON-serializable."""
        response = self.client.get(f"/session/{self.session_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        
        # Ensure the response is JSON-serializable
        try:
            json.dumps(data)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Response is not JSON-serializable: {e}")
        
        # Check that we have the expected top-level keys
        expected_keys = {"events", "cards", "sparklines"}
        actual_keys = set(data.keys())
        assert expected_keys.issubset(actual_keys), f"Missing keys: {expected_keys - actual_keys}"
    
    def test_get_session_summary_empty_session(self):
        """Test summary endpoint with a session that has no data."""
        empty_session_data = {
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
        
        # Seed empty session
        response = self.client.post("/dev/seed", json=empty_session_data)
        assert response.status_code == 200
        
        # Get summary
        response = self.client.get("/session/empty-test/summary")
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty structures
        assert data["events"] == []
        assert data["cards"] == []
        assert isinstance(data["sparklines"], dict)
        assert data["sparklines"]["laps_ms"] == []
        assert data["sparklines"]["speed_series"] == []