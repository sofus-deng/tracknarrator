"""Tests for summary API endpoint extension with narrative field."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tracknarrator.api import app
from tracknarrator.schema import SessionBundle, Session, Lap, Section
from tracknarrator.events import top5_events


# Get the path to the fixtures directory
fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

client = TestClient(app)


class TestAPISummaryExt:
    """Test cases for summary API endpoint extension with narrative field."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create a test session
        self.session = Session(
            id="barber-demo-r1",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create test laps with outliers
        self.laps = [
            Lap(
                session_id="summary-ext-test",
                lap_no=1,
                driver="Driver1",
                laptime_ms=100000,  # Normal lap
            ),
            Lap(
                session_id="summary-ext-test",
                lap_no=2,
                driver="Driver1",
                laptime_ms=130000,  # Outlier lap
            ),
            Lap(
                session_id="summary-ext-test",
                lap_no=3,
                driver="Driver1",
                laptime_ms=99000,  # Fast lap
            )
        ]
        
        # Create test sections
        self.sections = []
        for lap_no in [1, 2, 3]:
            for section_name in ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]:
                # Normal durations
                durations = {
                    "IM1a": 15000,
                    "IM1": 20000,
                    "IM2a": 25000,
                    "IM2": 18000,
                    "IM3a": 12000,
                    "FL": 10000
                }
                
                # Make lap 2 IM2a section abnormal
                if lap_no == 2 and section_name == "IM2a":
                    duration = 45000  # Much longer than normal
                else:
                    duration = durations[section_name]
                
                self.sections.append(Section(
                    session_id="summary-ext-test",
                    lap_no=lap_no,
                    name=section_name,
                    t_start_ms=0,
                    t_end_ms=duration,
                    meta={"source": "map"}
                ))
        
        # Create the bundle
        self.bundle = SessionBundle(
            session=self.session,
            laps=self.laps,
            sections=self.sections,
            telemetry=[],
            weather=[]
        )
        
        # Get top 5 events for narrative
        self.top5_events = top5_events(self.bundle)
    
    def test_summary_without_narrative_default(self):
        """Test summary endpoint without ai_native parameter (no narrative field)."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get summary without ai_native parameter
        response = client.get(f"/session/{self.session.id}/summary")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should have legacy shape (no narrative field)
        assert "events" in summary
        assert "cards" in summary
        assert "sparklines" in summary
        assert "narrative" not in summary
        
        # Check types
        assert isinstance(summary["events"], list)
        assert isinstance(summary["cards"], list)
        assert isinstance(summary["sparklines"], dict)
    
    def test_summary_with_ai_native_off(self):
        """Test summary endpoint with ai_native=off (no narrative field)."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get summary with ai_native=off
        response = client.get(f"/session/{self.session.id}/summary?ai_native=off")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should not have narrative field when ai_native=off
        assert "events" in summary
        assert "cards" in summary
        assert "sparklines" in summary
        assert "narrative" not in summary
    
    def test_summary_with_ai_native_on(self):
        """Test summary endpoint with ai_native=on (includes narrative field)."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get summary with ai_native=on
        response = client.get(f"/session/{self.session.id}/summary?ai_native=on")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should have narrative field when ai_native=on
        assert "events" in summary
        assert "cards" in summary
        assert "sparklines" in summary
        assert "narrative" in summary
        
        # Check narrative field structure
        narrative = summary["narrative"]
        assert "lines" in narrative
        assert "lang" in narrative
        assert "ai_native" in narrative
        
        # Check types
        assert isinstance(narrative["lines"], list)
        assert isinstance(narrative["lang"], str)
        assert isinstance(narrative["ai_native"], bool)
        
        # Check values
        assert len(narrative["lines"]) <= 3
        assert narrative["lang"] == "zh-Hant"  # Default
        assert narrative["ai_native"] is True
    
    def test_summary_with_ai_native_true(self):
        """Test summary endpoint with ai_native=true (includes narrative field)."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get summary with ai_native=true
        response = client.get(f"/session/{self.session.id}/summary?ai_native=true")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should have narrative field when ai_native=true
        assert "narrative" in summary
        
        narrative = summary["narrative"]
        assert narrative["ai_native"] is True
    
    def test_summary_with_ai_native_invalid(self):
        """Test summary endpoint with invalid ai_native value (no narrative field)."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get summary with invalid ai_native value
        response = client.get(f"/session/{self.session.id}/summary?ai_native=invalid")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should not have narrative field for invalid ai_native value
        assert "events" in summary
        assert "cards" in summary
        assert "sparklines" in summary
        assert "narrative" not in summary
    
    def test_summary_legacy_shape_preserved(self):
        """Test that legacy summary shape is preserved when narrative not requested."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get summary without ai_native parameter
        response = client.get(f"/session/{self.session.id}/summary")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should exactly match legacy shape
        expected_keys = {"events", "cards", "sparklines"}
        actual_keys = set(summary.keys())
        
        assert actual_keys == expected_keys
        
        # All legacy fields should be present and valid
        assert isinstance(summary["events"], list)
        assert isinstance(summary["cards"], list)
        assert isinstance(summary["sparklines"], dict)
    
    def test_summary_superset_keys_when_narrative_requested(self):
        """Test that summary has superset keys when narrative is requested."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get summary with ai_native=on
        response = client.get(f"/session/{self.session.id}/summary?ai_native=on")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should have all legacy keys plus narrative
        expected_keys = {"events", "cards", "sparklines", "narrative"}
        actual_keys = set(summary.keys())
        
        assert actual_keys == expected_keys
        
        # All legacy fields should still be present and valid
        assert isinstance(summary["events"], list)
        assert isinstance(summary["cards"], list)
        assert isinstance(summary["sparklines"], dict)
        
        # Narrative field should be valid
        assert isinstance(summary["narrative"], dict)
        assert "lines" in summary["narrative"]
        assert "lang" in summary["narrative"]
        assert "ai_native" in summary["narrative"]
    
    def test_summary_narrative_content_valid(self):
        """Test that narrative content in summary is valid."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        # Derive session_id for seeded bundle
        try:
            session_id = (response.json() or {}).get("session_id")
        except Exception:
            session_id = None
        if not session_id:
            session_id = bundle_data.get("session_id") or "summary-ext-test"
        
        # Get summary with ai_native=on
        response = client.get(f"/session/{session_id}/summary?ai_native=on")
        assert response.status_code == 200
        
        summary = response.json()
        narrative = summary["narrative"]
        
        # Narrative content should be valid
        assert isinstance(narrative["lines"], list)
        assert len(narrative["lines"]) <= 3
        assert len(narrative["lines"]) >= 1  # Should have some content
        
        # All lines should be non-empty strings
        for line in narrative["lines"]:
            assert isinstance(line, str)
            assert len(line) > 0
    
    def test_summary_nonexistent_session(self):
        """Test summary endpoint with nonexistent session."""
        response = client.get("/session/nonexistent-session/summary")
        assert response.status_code == 404
        
        error = response.json()
        assert "error" in error
        assert "Session nonexistent-session not found" in str(error)
    
    def test_summary_with_fixture_data(self):
        """Test summary endpoint with fixture bundle data."""
        # Load the sample bundle
        with open(fixtures_dir / "bundle_sample_barber.json", "r") as f:
            bundle_data = json.load(f)
        
        bundle = SessionBundle.model_validate(bundle_data)
        
        # Seed the fixture data
        response = client.post("/dev/seed", json=bundle.model_dump())
        assert response.status_code == 200
        # Derive session_id (prefer API response, fallback to bundle/fixture, default "barber")
        try:
            session_id = (response.json() or {}).get("session_id")
        except Exception:
            session_id = None
        if not session_id:
            session_id = getattr(bundle, "session_id", None) or bundle_data.get("session_id") or "barber"
        
        # Test summary without narrative
        response = client.get(f"/session/{session_id}/summary")
        assert response.status_code == 200
        
        summary = response.json()
        assert "events" in summary
        assert "cards" in summary
        assert "sparklines" in summary
        assert "narrative" not in summary
        
        # Test summary with narrative
        response = client.get(f"/session/{session_id}/summary?ai_native=on")
        assert response.status_code == 200
        
        summary = response.json()
        assert "narrative" in summary
        assert isinstance(summary["narrative"]["lines"], list)