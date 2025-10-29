"""Tests for AI-native narrative toggle functionality."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tracknarrator.api import app
from tracknarrator.schema import SessionBundle, Session, Lap, Section
from tracknarrator.narrative import build_narrative
from tracknarrator.events import top5_events


# Get the path to the fixtures directory
fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

client = TestClient(app)


class TestNarrativeToggle:
    """Test cases for AI-native narrative toggle."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create a test session
        self.session = Session(
            id="test-narrative",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create test laps with one outlier
        self.laps = [
            Lap(
                session_id="test-narrative",
                lap_no=1,
                driver="Driver1",
                laptime_ms=100000,  # Normal lap
            ),
            Lap(
                session_id="test-narrative",
                lap_no=2,
                driver="Driver1",
                laptime_ms=102000,  # Normal lap
            ),
            Lap(
                session_id="test-narrative",
                lap_no=3,
                driver="Driver1",
                laptime_ms=130000,  # Outlier lap
            ),
            Lap(
                session_id="test-narrative",
                lap_no=4,
                driver="Driver1",
                laptime_ms=101000,  # Normal lap
            ),
            Lap(
                session_id="test-narrative",
                lap_no=5,
                driver="Driver1",
                laptime_ms=99000,  # Fast lap
            )
        ]
        
        # Create test sections
        self.sections = []
        for lap_no in [1, 2, 3, 4, 5]:
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
                
                # Make lap 3 IM2a section abnormal
                if lap_no == 3 and section_name == "IM2a":
                    duration = 45000  # Much longer than normal
                else:
                    duration = durations[section_name]
                
                self.sections.append(Section(
                    session_id="test-narrative",
                    lap_no=lap_no,
                    name=section_name,
                    t_start_ms=0,  # Simplified for test
                    t_end_ms=duration,
                    meta={"source": "map"}
                ))
        
        # Create the bundle
        self.bundle = SessionBundle(
            session=self.session,
            laps=self.laps,
            sections=self.sections,
            telemetry=[],  # Not needed for narrative tests
            weather=[]
        )
        
        # Get top 5 events for narrative
        self.top5_events = top5_events(self.bundle)
    
    def test_narrative_disabled(self):
        """Test narrative when AI_NATIVE is off."""
        # Test with AI_NATIVE off
        result = build_narrative(self.bundle, self.top5_events, on=False)
        
        # Check structure
        assert "enabled" in result
        assert "lines" in result
        
        # Check values when disabled
        assert result["enabled"] is False
        assert result["lines"] == []
    
    def test_narrative_enabled(self):
        """Test narrative when AI_NATIVE is on."""
        # Test with AI_NATIVE on
        result = build_narrative(self.bundle, self.top5_events, on=True)
        
        # Check structure
        assert "enabled" in result
        assert "lines" in result
        
        # Check values when enabled
        assert result["enabled"] is True
        assert isinstance(result["lines"], list)
        assert len(result["lines"]) == 3  # Should always return exactly 3 lines
        
        # Check that lines are non-empty strings
        for line in result["lines"]:
            assert isinstance(line, str)
            assert len(line) > 0
    
    def test_narrative_deterministic_order(self):
        """Test that narrative lines are in deterministic order."""
        # Generate narrative twice
        result1 = build_narrative(self.bundle, self.top5_events, on=True)
        result2 = build_narrative(self.bundle, self.top5_events, on=True)
        
        # Should be identical
        assert result1["enabled"] == result2["enabled"]
        assert result1["lines"] == result2["lines"]
    
    def test_narrative_with_no_events(self):
        """Test narrative with no events."""
        # Create bundle with no significant events
        normal_laps = [
            Lap(
                session_id="test-narrative",
                lap_no=i,
                driver="Driver1",
                laptime_ms=100000 + (i * 100),  # Very consistent lap times
            )
            for i in range(1, 6)
        ]
        
        normal_bundle = SessionBundle(
            session=self.session,
            laps=normal_laps,
            sections=[],  # No sections
            telemetry=[],
            weather=[]
        )
        
        # Get top 5 events (should be empty or very few)
        normal_top5 = top5_events(normal_bundle)
        
        # Generate narrative
        result = build_narrative(normal_bundle, normal_top5, on=True)
        
        # Should still return exactly 3 lines
        assert result["enabled"] is True
        assert len(result["lines"]) == 3
        
        # Lines should contain session statistics
        lines_text = " ".join(result["lines"])
        assert "best" in lines_text.lower() or "median" in lines_text.lower()
    
    def test_narrative_api_endpoint_with_ai_native_off(self):
        """Test narrative API endpoint with AI_NATIVE=off."""
        # Set AI_NATIVE to off
        original_ai_native = os.environ.get("AI_NATIVE")
        os.environ["AI_NATIVE"] = "off"
        
        # Clear config cache to ensure new setting is picked up
        from tracknarrator.config import get_settings
        get_settings.cache_clear()
        
        try:
            # Seed the test data
            bundle_data = self.bundle.model_dump()
            response = client.post("/dev/seed", json=bundle_data)
            assert response.status_code == 200
            
            # Get narrative
            response = client.get("/session/test-narrative/narrative")
            assert response.status_code == 200
            
            narrative = response.json()
            assert narrative["enabled"] is False
            assert narrative["lines"] == []
            
        finally:
            # Restore original AI_NATIVE setting
            if original_ai_native is not None:
                os.environ["AI_NATIVE"] = original_ai_native
            elif "AI_NATIVE" in os.environ:
                del os.environ["AI_NATIVE"]
            # Clear config cache again
            get_settings.cache_clear()
    
    def test_narrative_api_endpoint_with_ai_native_on(self):
        """Test narrative API endpoint with AI_NATIVE=on."""
        # Set AI_NATIVE to on
        original_ai_native = os.environ.get("AI_NATIVE")
        os.environ["AI_NATIVE"] = "on"
        
        # Clear the config cache to ensure the new setting is picked up
        from tracknarrator.config import get_settings
        get_settings.cache_clear()
        
        try:
            # Seed the test data
            bundle_data = self.bundle.model_dump()
            response = client.post("/dev/seed", json=bundle_data)
            assert response.status_code == 200
            
            # Get narrative
            response = client.get("/session/test-narrative/narrative")
            assert response.status_code == 200
            
            narrative = response.json()
            assert narrative["enabled"] is True
            assert len(narrative["lines"]) == 3
            
            # Check that lines are non-empty strings
            for line in narrative["lines"]:
                assert isinstance(line, str)
                assert len(line) > 0
            
        finally:
            # Restore original AI_NATIVE setting
            if original_ai_native is not None:
                os.environ["AI_NATIVE"] = original_ai_native
            elif "AI_NATIVE" in os.environ:
                del os.environ["AI_NATIVE"]
            # Clear config cache again
            get_settings.cache_clear()
            # Clear the config cache again
            get_settings.cache_clear()
    
    def test_narrative_with_fixture_data(self):
        """Test narrative with the fixture bundle."""
        # Load the sample bundle
        with open(fixtures_dir / "bundle_sample_barber.json", "r") as f:
            bundle_data = json.load(f)
        
        bundle = SessionBundle.model_validate(bundle_data)
        top5 = top5_events(bundle)
        
        # Test with AI_NATIVE on
        result_on = build_narrative(bundle, top5, on=True)
        assert result_on["enabled"] is True
        assert len(result_on["lines"]) == 3
        
        # Test with AI_NATIVE off
        result_off = build_narrative(bundle, top5, on=False)
        assert result_off["enabled"] is False
        assert result_off["lines"] == []
    
    def test_narrative_line_templates(self):
        """Test that narrative line templates are correctly applied."""
        # Generate narrative
        result = build_narrative(self.bundle, self.top5_events, on=True)
        
        lines = result["lines"]
        
        # Should have exactly 3 lines
        assert len(lines) == 3
        
        # Check that lines contain expected content based on our test data
        # (lap 3 outlier, section IM2a outlier, etc.)
        all_text = " ".join(lines).lower()
        
        # Should mention lap outlier
        assert "lap 3" in all_text or "stood out" in all_text
        
        # Should mention section outlier or position change
        assert ("section" in all_text or "position" in all_text or 
                "best" in all_text or "median" in all_text)