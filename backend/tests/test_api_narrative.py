"""Tests for narrative API endpoint with multilingual support and determinism."""

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


class TestAPINarrative:
    """Test cases for narrative API endpoint."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create a test session
        self.session = Session(
            id="api-narrative-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create test laps with outliers
        self.laps = [
            Lap(
                session_id="api-narrative-test",
                lap_no=1,
                driver="Driver1",
                laptime_ms=100000,  # Normal lap
            ),
            Lap(
                session_id="api-narrative-test",
                lap_no=2,
                driver="Driver1",
                laptime_ms=130000,  # Outlier lap
            ),
            Lap(
                session_id="api-narrative-test",
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
                    session_id="api-narrative-test",
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
    
    def test_narrative_endpoint_shape(self):
        """Test that narrative endpoint returns correct shape."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative
        response = client.get("/session/api-narrative-test/narrative")
        assert response.status_code == 200
        
        narrative = response.json()
        
        # Check response shape
        assert "lines" in narrative
        assert "lang" in narrative
        assert "ai_native" in narrative
        
        # Check types
        assert isinstance(narrative["lines"], list)
        assert isinstance(narrative["lang"], str)
        assert isinstance(narrative["ai_native"], bool)
        
        # Check values
        assert len(narrative["lines"]) <= 3
        assert narrative["lang"] == "zh-Hant"  # Default language
        assert narrative["ai_native"] is True  # Default is now True
    
    def test_narrative_endpoint_lang_zh_hant(self):
        """Test narrative endpoint with zh-Hant language."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative with zh-Hant
        response = client.get("/session/api-narrative-test/narrative?lang=zh-Hant")
        assert response.status_code == 200
        
        narrative = response.json()
        assert narrative["lang"] == "zh-Hant"
        
        # Should contain Chinese keywords
        all_text = " ".join(narrative["lines"])
        assert any(keyword in all_text for keyword in ["圈", "節奏", "路段", "位置"])
    
    def test_narrative_endpoint_lang_en(self):
        """Test narrative endpoint with en language."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative with en
        response = client.get("/session/api-narrative-test/narrative?lang=en")
        assert response.status_code == 200
        
        narrative = response.json()
        assert narrative["lang"] == "en"
        
        # Should contain English keywords
        all_text = " ".join(narrative["lines"]).lower()
        assert any(keyword in all_text for keyword in ["lap", "section", "position", "rhythm"])
    
    def test_narrative_endpoint_ai_native_on(self):
        """Test narrative endpoint with ai_native=on."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative with ai_native=on
        response = client.get("/session/api-narrative-test/narrative?ai_native=on")
        assert response.status_code == 200
        
        narrative = response.json()
        assert narrative["ai_native"] is True
        
        # Should use AI-native templates
        all_text = " ".join(narrative["lines"])
        assert len(all_text) > 0
    
    def test_narrative_endpoint_ai_native_off(self):
        """Test narrative endpoint with ai_native=off."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative with ai_native=off
        response = client.get("/session/api-narrative-test/narrative?ai_native=off")
        assert response.status_code == 200
        
        narrative = response.json()
        assert narrative["ai_native"] is False
        
        # Should use rule-based fallback
        all_text = " ".join(narrative["lines"])
        assert any(keyword in all_text for keyword in ["賽道", "分析", "最佳", "配速"])  # zh-Hant fallback
    
    def test_narrative_endpoint_ai_native_auto(self):
        """Test narrative endpoint with ai_native=auto (uses global setting)."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative with ai_native=auto
        response = client.get("/session/api-narrative-test/narrative?ai_native=auto")
        assert response.status_code == 200
        
        narrative = response.json()
        # Should use global setting (now defaults to True)
        assert narrative["ai_native"] is True
    
    def test_narrative_endpoint_determinism(self):
        """Test that narrative endpoint is deterministic."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative twice
        response1 = client.get("/session/api-narrative-test/narrative?lang=zh-Hant&ai_native=on")
        response2 = client.get("/session/api-narrative-test/narrative?lang=zh-Hant&ai_native=on")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        narrative1 = response1.json()
        narrative2 = response2.json()
        
        # Should be identical (deterministic)
        assert narrative1["lines"] == narrative2["lines"]
        assert narrative1["lang"] == narrative2["lang"]
        assert narrative1["ai_native"] == narrative2["ai_native"]
    
    def test_narrative_endpoint_nonexistent_session(self):
        """Test narrative endpoint with nonexistent session."""
        response = client.get("/session/nonexistent-session/narrative")
        assert response.status_code == 404
        
        error = response.json()
        assert "error" in error
        assert "Session nonexistent-session not found" in str(error)
    
    def test_narrative_endpoint_max_lines(self):
        """Test that narrative endpoint respects max_lines internally."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get narrative
        response = client.get("/session/api-narrative-test/narrative")
        assert response.status_code == 200
        
        narrative = response.json()
        
        # Should never return more than 3 lines
        assert len(narrative["lines"]) <= 3
        
        # All lines should be non-empty strings
        for line in narrative["lines"]:
            assert isinstance(line, str)
            assert len(line) > 0
    
    def test_narrative_endpoint_hash_stability(self):
        """Test that narrative output is stable across requests."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Make multiple requests and check hash stability
        responses = []
        for i in range(3):
            response = client.get("/session/api-narrative-test/narrative?lang=en&ai_native=on")
            assert response.status_code == 200
            responses.append(response.json())
        
        # All responses should be identical
        for i in range(1, len(responses)):
            assert responses[i]["lines"] == responses[0]["lines"]
            assert responses[i]["lang"] == responses[0]["lang"]
            assert responses[i]["ai_native"] == responses[0]["ai_native"]