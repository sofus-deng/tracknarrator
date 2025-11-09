"""Tests for the coaching tips engine."""

import json
import pytest
from pathlib import Path

from tracknarrator.schema import SessionBundle
from tracknarrator.coach import coach_tips
from tracknarrator.events import top5_events

# Load the sample bundle
BUNDLE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "bundle_sample_barber.json"


class TestCoachTips:
    """Test cases for the coaching tips engine."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Load the sample bundle
        with open(BUNDLE_PATH, 'r') as f:
            bundle_data = json.load(f)
        
        self.bundle = SessionBundle(**bundle_data)
        self.top_events = top5_events(self.bundle)
    
    def test_coach_tips_empty_events(self):
        """Test coach_tips with empty events list."""
        tips = coach_tips(self.bundle, [])
        
        assert tips == []
    
    def test_coach_tips_max_length(self):
        """Test that coach_tips returns at most 3 tips."""
        # Create a bundle with many events
        bundle_data = {
            "session": {
                "id": "test-many-events",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [
                {"session_id": "test-many-events", "lap_no": i, "driver": "Driver1", 
                 "laptime_ms": 100000 + i * 1000, "position": i}
                for i in range(1, 10)
            ],
            "sections": [],
            "telemetry": [],
            "weather": []
        }
        
        bundle = SessionBundle(**bundle_data)
        top_events = top5_events(bundle)
        
        # Even with many events, should return max 3 tips
        tips = coach_tips(bundle, top_events)
        assert len(tips) <= 3
    
    def test_coach_tips_field_completeness(self):
        """Test that tips have all required fields."""
        # Create a bundle that will generate events
        bundle_data = {
            "session": {
                "id": "test-field-completeness",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [
                {"session_id": "test-field-completeness", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000, "position": 5},
                {"session_id": "test-field-completeness", "lap_no": 2, "driver": "Driver1", "laptime_ms": 200000, "position": 3},  # Outlier
                {"session_id": "test-field-completeness", "lap_no": 3, "driver": "Driver1", "laptime_ms": 101000, "position": 1},
                {"session_id": "test-field-completeness", "lap_no": 4, "driver": "Driver1", "laptime_ms": 102000, "position": 2},
                {"session_id": "test-field-completeness", "lap_no": 5, "driver": "Driver1", "laptime_ms": 99000, "position": 1},
            ],
            "sections": [],
            "telemetry": [],
            "weather": []
        }
        
        bundle = SessionBundle(**bundle_data)
        top_events = top5_events(bundle)
        tips = coach_tips(bundle, top_events)
        
        for tip in tips:
            # Check all required fields exist
            assert "tip_id" in tip
            assert "title" in tip
            assert "body" in tip
            assert "severity" in tip
            assert "event_ref" in tip
            
            # Check field types
            assert isinstance(tip["tip_id"], str)
            assert isinstance(tip["title"], str)
            assert isinstance(tip["body"], str)
            assert isinstance(tip["severity"], (int, float))
            assert isinstance(tip["event_ref"], str)
            
            # Check severity range
            assert 0 <= tip["severity"] <= 1
            
            # Check tip_id and event_ref are the same
            assert tip["tip_id"] == tip["event_ref"]
    
    def test_coach_tips_type_distribution(self):
        """Test that tips avoid type repetition and follow rules."""
        # Create a bundle with multiple event types
        bundle_data = {
            "session": {
                "id": "test-type-distribution",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [
                {"session_id": "test-type-distribution", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000, "position": 5},
                {"session_id": "test-type-distribution", "lap_no": 2, "driver": "Driver1", "laptime_ms": 200000, "position": 3},  # Outlier
                {"session_id": "test-type-distribution", "lap_no": 3, "driver": "Driver1", "laptime_ms": 101000, "position": 1},
                {"session_id": "test-type-distribution", "lap_no": 4, "driver": "Driver1", "laptime_ms": 102000, "position": 2},
                {"session_id": "test-type-distribution", "lap_no": 5, "driver": "Driver1", "laptime_ms": 99000, "position": 1},
            ],
            "sections": [
                {"session_id": "test-type-distribution", "lap_no": 1, "name": "IM1a", "t_start_ms": 0, "t_end_ms": 20000, "delta_ms": None, "meta": {}},
                {"session_id": "test-type-distribution", "lap_no": 2, "name": "IM1a", "t_start_ms": 0, "t_end_ms": 40000, "delta_ms": None, "meta": {}},  # Outlier
            ],
            "telemetry": [],
            "weather": []
        }
        
        bundle = SessionBundle(**bundle_data)
        top_events = top5_events(bundle)
        tips = coach_tips(bundle, top_events)
        
        # Check that we don't have duplicate tip types
        tip_types = []
        for tip in tips:
            # Extract event type from tip_id (format: "event_type-lap_no")
            event_type = tip["tip_id"].split("-")[0]
            tip_types.append(event_type)
        
        # Should not have duplicate types
        assert len(tip_types) == len(set(tip_types))
        
        # Position change tips should be at most 1
        position_change_count = tip_types.count("position_change")
        assert position_change_count <= 1
    
    def test_coach_tips_english_language(self):
        """Test that lang='en' produces English output."""
        # Create a bundle that will generate events
        bundle_data = {
            "session": {
                "id": "test-english-lang",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [
                {"session_id": "test-english-lang", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000, "position": 5},
                {"session_id": "test-english-lang", "lap_no": 2, "driver": "Driver1", "laptime_ms": 200000, "position": 3},  # Outlier
                {"session_id": "test-english-lang", "lap_no": 3, "driver": "Driver1", "laptime_ms": 101000, "position": 1},
            ],
            "sections": [
                {"session_id": "test-english-lang", "lap_no": 1, "name": "IM1a", "t_start_ms": 0, "t_end_ms": 20000, "delta_ms": None, "meta": {}},
                {"session_id": "test-english-lang", "lap_no": 2, "name": "IM1a", "t_start_ms": 0, "t_end_ms": 40000, "delta_ms": None, "meta": {}},  # Outlier
            ],
            "telemetry": [],
            "weather": []
        }
        
        bundle = SessionBundle(**bundle_data)
        top_events = top5_events(bundle)
        
        # Test English language
        tips_en = coach_tips(bundle, top_events, lang="en")
        
        # Test Chinese language (default)
        tips_zh = coach_tips(bundle, top_events, lang="zh-Hant")
        
        # Should have tips in both languages
        assert len(tips_en) > 0
        assert len(tips_zh) > 0
        
        # English tips should contain English text
        for tip in tips_en:
            assert "focus on" in tip["body"].lower() or "focus" in tip["body"].lower()
            assert "pace imbalance" in tip["title"].lower() or "section slow" in tip["title"].lower() or "position fluctuation" in tip["title"].lower()
        
        # Chinese tips should contain Chinese text
        for tip in tips_zh:
            assert "建議" in tip["body"]
            assert "配速失衡" in tip["title"] or "分段偏慢" in tip["title"] or "名次波動" in tip["title"]
    
    def test_coach_tips_deterministic(self):
        """Test that coach_tips produces deterministic output."""
        # Create a bundle with events
        bundle_data = {
            "session": {
                "id": "test-deterministic",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [
                {"session_id": "test-deterministic", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000, "position": 5},
                {"session_id": "test-deterministic", "lap_no": 2, "driver": "Driver1", "laptime_ms": 200000, "position": 3},  # Outlier
                {"session_id": "test-deterministic", "lap_no": 3, "driver": "Driver1", "laptime_ms": 101000, "position": 1},
            ],
            "sections": [],
            "telemetry": [],
            "weather": []
        }
        
        bundle = SessionBundle(**bundle_data)
        top_events = top5_events(bundle)
        
        # Call coach_tips multiple times
        tips1 = coach_tips(bundle, top_events)
        tips2 = coach_tips(bundle, top_events)
        
        # Should produce identical results
        assert len(tips1) == len(tips2)
        for tip1, tip2 in zip(tips1, tips2):
            assert tip1["tip_id"] == tip2["tip_id"]
            assert tip1["title"] == tip2["title"]
            assert tip1["body"] == tip2["body"]
            assert tip1["severity"] == tip2["severity"]
            assert tip1["event_ref"] == tip2["event_ref"]
    
    def test_coach_tips_with_barber_fixture(self):
        """Test coach_tips with the actual barber fixture."""
        # This uses the real fixture data
        tips = coach_tips(self.bundle, self.top_events)
        
        # Should return a list (possibly empty for this fixture)
        assert isinstance(tips, list)
        
        # If there are tips, they should have correct structure
        for tip in tips:
            assert "tip_id" in tip
            assert "title" in tip
            assert "body" in tip
            assert "severity" in tip
            assert "event_ref" in tip
            assert 0 <= tip["severity"] <= 1
    
    def test_coach_tips_unknown_language_fallback(self):
        """Test that unknown language falls back to zh-Hant."""
        bundle_data = {
            "session": {
                "id": "test-unknown-lang",
                "source": "mylaps_csv",
                "track": "Test Track",
                "track_id": "test-track",
                "schema_version": "0.1.2"
            },
            "laps": [
                {"session_id": "test-unknown-lang", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000, "position": 5},
                {"session_id": "test-unknown-lang", "lap_no": 2, "driver": "Driver1", "laptime_ms": 200000, "position": 3},  # Outlier
                {"session_id": "test-unknown-lang", "lap_no": 3, "driver": "Driver1", "laptime_ms": 101000, "position": 1},
            ],
            "sections": [],
            "telemetry": [],
            "weather": []
        }
        
        bundle = SessionBundle(**bundle_data)
        top_events = top5_events(bundle)
        
        # Test with unknown language
        tips_unknown = coach_tips(bundle, top_events, lang="unknown")
        tips_zh = coach_tips(bundle, top_events, lang="zh-Hant")
        
        # Should fallback to Chinese
        assert len(tips_unknown) > 0
        assert len(tips_zh) > 0
        
        # Should have same content
        assert tips_unknown[0]["title"] == tips_zh[0]["title"]
        assert tips_unknown[0]["body"] == tips_zh[0]["body"]