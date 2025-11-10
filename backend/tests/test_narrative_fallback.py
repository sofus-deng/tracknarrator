"""Tests for narrative fallback and edge cases."""

import pytest

from tracknarrator.schema import SessionBundle, Session, Lap, Section, Telemetry, WeatherPoint
from tracknarrator.narrative import build_narrative
from tracknarrator.events import Event


class TestNarrativeFallback:
    """Test cases for narrative fallback scenarios."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create a basic session for testing
        self.session = Session(
            id="narrative-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
    
    def test_empty_events_list(self):
        """Test narrative with empty events list."""
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=5),
                Lap(session_id="narrative-test", lap_no=2, driver="Driver1", 
                    laptime_ms=102000, position=4),
                Lap(session_id="narrative-test", lap_no=3, driver="Driver1", 
                    laptime_ms=101000, position=3),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        result = build_narrative(bundle, [], ai_native=True)

        # Should return session statistics since there are valid laps
        assert isinstance(result, list)
        assert len(result) == 3
        # With valid lap times, returns session stats instead of generic fallback
        assert "Best lap" in result["lines"][0]
        assert "median" in result["lines"][0]
        assert "Pace spread" in result["lines"][1]
        assert "Data analysis complete." in result["lines"][2]
    
    def test_single_event(self):
        """Test narrative with single event."""
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=5),
                Lap(session_id="narrative-test", lap_no=2, driver="Driver1", 
                    laptime_ms=130000, position=4),  # Outlier
                Lap(session_id="narrative-test", lap_no=3, driver="Driver1", 
                    laptime_ms=101000, position=3),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        single_event = Event(
            type="lap_outlier",
            lap_no=2,
            section=None,
            severity=0.8,
            summary="Lap 2 was slow",
            meta={"driver": "Driver1", "laptime_ms": 130000, "median_ms": 100500, "robust_z": 3.0}
        )
        
        result = build_narrative(bundle, [single_event], ai_native=True)

        assert isinstance(result, list)
        assert len(result) == 3
        
        # First line should be the event
        assert "Lap 2" in result["lines"][0]
        assert "stood out" in result["lines"][0]
        
        # Should have fallback lines
        # With only 1 event, adds session stats and one generic line
        assert "Best lap" in result["lines"][1]
        assert "Pace spread" in result["lines"][2]
    
    def test_two_events(self):
        """Test narrative with two events."""
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=5),
                Lap(session_id="narrative-test", lap_no=2, driver="Driver1", 
                    laptime_ms=130000, position=3),  # Position change + outlier
                Lap(session_id="narrative-test", lap_no=3, driver="Driver1", 
                    laptime_ms=99000, position=1),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        events = [
            Event(
                type="lap_outlier",
                lap_no=2,
                section=None,
                severity=0.8,
                summary="Lap 2 was slow",
                meta={"driver": "Driver1", "laptime_ms": 130000, "median_ms": 100500, "robust_z": 3.0}
            ),
            Event(
                type="position_change",
                lap_no=2,
                section=None,
                severity=0.4,
                summary="Position change",
                meta={"delta": -2, "prev_pos": 5, "curr_pos": 3}
            )
        ]
        
        result = build_narrative(bundle, events, on=True)
        
        assert result["enabled"] is True
        assert len(result["lines"]) == 3
        
        # First two lines should be the events (sorted by severity)
        assert "Lap 2" in result["lines"][0]
        assert "stood out" in result["lines"][0]
        assert "Position shift" in result["lines"][1]
        
        # Should have session stats as fallback
        assert "Best lap" in result["lines"][2]
    
    def test_three_events_exact(self):
        """Test narrative with exactly three events."""
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=5),
                Lap(session_id="narrative-test", lap_no=2, driver="Driver1", 
                    laptime_ms=130000, position=3),  # Multiple issues
                Lap(session_id="narrative-test", lap_no=3, driver="Driver1", 
                    laptime_ms=99000, position=1),
            ],
            sections=[
                Section(session_id="narrative-test", lap_no=2, name="IM1a", 
                       t_start_ms=0, t_end_ms=20000, meta={"source": "map"})
            ],
            telemetry=[],
            weather=[]
        )
        
        events = [
            Event(
                type="lap_outlier",
                lap_no=2,
                section=None,
                severity=0.8,
                summary="Lap 2 was slow",
                meta={"driver": "Driver1", "laptime_ms": 130000, "median_ms": 100500, "robust_z": 3.0}
            ),
            Event(
                type="position_change",
                lap_no=2,
                section=None,
                severity=0.4,
                summary="Position change",
                meta={"delta": -2, "prev_pos": 5, "curr_pos": 3}
            ),
            Event(
                type="section_outlier",
                lap_no=2,
                section="IM1a",
                severity=0.3,
                summary="Section was slow",
                meta={"section_name": "IM1a", "duration_ms": 20000, "median_ms": 15000, "robust_z": 2.8}
            )
        ]
        
        result = build_narrative(bundle, events, on=True)
        
        assert result["enabled"] is True
        assert len(result["lines"]) == 3
        
        # All lines should be from events
        assert "Lap 2" in result["lines"][0]
        assert "Position shift" in result["lines"][1]
        assert "Section IM1a" in result["lines"][2]
        
        # No fallback lines should be added
        assert "Session completed." not in result["lines"]
        assert "No significant anomalies detected." not in result["lines"]
        assert "Data analysis complete." not in result["lines"]
    
    def test_narrative_disabled(self):
        """Test narrative when disabled."""
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=5),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        events = [
            Event(
                type="lap_outlier",
                lap_no=1,
                section=None,
                severity=0.8,
                summary="Lap 1 was slow",
                meta={"driver": "Driver1", "laptime_ms": 130000, "median_ms": 100500, "robust_z": 3.0}
            )
        ]
        
        result = build_narrative(bundle, events, on=False)
        
        # Should return disabled state
        assert result["enabled"] is False
        assert result["lines"] == []
    
    def test_empty_bundle_with_fallback(self):
        """Test narrative with empty bundle."""
        empty_bundle = SessionBundle(
            session=self.session,
            laps=[],  # No laps
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        result = build_narrative(empty_bundle, [], on=True)
        
        # Empty bundle with no laps returns empty narrative
        assert result["enabled"] is True
        assert len(result["lines"]) == 0
    
    def test_bundle_with_laps_but_no_valid_times(self):
        """Test bundle with laps but no valid lap times."""
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=0, position=5),  # Invalid time
                Lap(session_id="narrative-test", lap_no=2, driver="Driver1", 
                    laptime_ms=0, position=4),  # Invalid time
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        result = build_narrative(bundle, [], on=True)
        
        # Bundle with invalid lap times returns empty narrative
        assert result["enabled"] is True
        assert len(result["lines"]) == 0
    
    def test_event_formatting_with_missing_meta(self):
        """Test event formatting when some meta fields are missing."""
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=5),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        # Event with minimal meta
        event = Event(
            type="lap_outlier",
            lap_no=1,
            section=None,
            severity=0.8,
            summary="Lap 1 was slow",
            meta={"driver": "Driver1"}  # Missing other fields
        )
        
        result = build_narrative(bundle, [event], on=True)
        
        assert result["enabled"] is True
        assert len(result["lines"]) == 3
        assert "Lap 1" in result["lines"][0]
        assert "stood out" in result["lines"][0]
    
    def test_session_stats_computation(self):
        """Test session statistics computation with various lap time distributions."""
        # Bundle with known lap times for predictable stats
        bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=1),  # Best lap
                Lap(session_id="narrative-test", lap_no=2, driver="Driver1", 
                    laptime_ms=110000, position=1),
                Lap(session_id="narrative-test", lap_no=3, driver="Driver1", 
                    laptime_ms=105000, position=1),
                Lap(session_id="narrative-test", lap_no=4, driver="Driver1", 
                    laptime_ms=115000, position=1),
                Lap(session_id="narrative-test", lap_no=5, driver="Driver1", 
                    laptime_ms=120000, position=1),  # Slowest lap
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        result = build_narrative(bundle, [], ai_native=True)

        # Should include session statistics in fallback
        assert isinstance(result, list)
        assert len(result) == 3
        # Should contain session stats
        stats_line = None
        for line in result["lines"]:
            if "Best lap" in line and "median" in line:
                stats_line = line
                break
        
        assert stats_line is not None
        assert "100000" in stats_line  # Best lap
        assert "110000" in stats_line  # Median (sorted: 100k, 105k, 110k, 115k, 120k)
        # Median is the middle value = 110000
    
    def test_stable_wording_format(self):
        """Test that wording format is stable for similar scenarios."""
        # Create two similar bundles
        bundle1 = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=5),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        bundle2 = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-test", lap_no=1, driver="Driver1", 
                    laptime_ms=100000, position=3),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        result1 = build_narrative(bundle1, [], ai_native=True)
        result2 = build_narrative(bundle2, [], ai_native=True)
        
        # Should have same format (even if content differs slightly)
        assert isinstance(result1, list) and isinstance(result2, list)
        assert len(result1["lines"]) == len(result2["lines"])
        
        # All lines should have similar structure
        for i, (line1, line2) in enumerate(zip(result1["lines"], result2["lines"])):
            if i == 0:
                assert line1 == line2  # Should be identical
            else:
                # Subsequent lines may differ slightly
                assert isinstance(line1, str)
                assert isinstance(line2, str)
                assert len(line1) > 0
                assert len(line2) > 0