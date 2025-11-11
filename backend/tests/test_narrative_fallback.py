"""Tests for narrative fallback and edge cases."""

import pytest

from tracknarrator.schema import SessionBundle, Session, Lap, Section, Telemetry, WeatherPoint
from tracknarrator.narrative import build_narrative
from tracknarrator.events import Event


def _as_lines(result):
    """Helper to handle both dict and list return formats."""
    return result["lines"] if isinstance(result, dict) else result


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
        # Check for either English or Chinese text based on default language
        line0 = result[0].lower()
        line1 = result[1].lower()
        line2 = result[2].lower()
        
        assert ("best lap" in line0 or "最佳單圈" in line0 or "完成" in line0)
        assert ("median" in line0 or "中位數" in line0 or "完成" in line0)
        assert ("pace spread" in line1 or "差距" in line1 or "完成" in line1 or "時間" in line1)
        assert ("data analysis complete" in line2 or "結束" in line2 or "完成" in line2 or "穩定性" in line2)
    
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
        assert "Lap 2" in result[0] or "第2圈" in result[0]
        assert ("stood out" in result[0] or "突出" in result[0] or "異常" in result[0])
        
        # Should have fallback lines
        # With only 1 event, adds session stats and one generic line
        assert "Best lap" in result[1] or "最佳單圈" in result[1] or "完成" in result[1] or "時間" in result[1]
        assert "Pace spread" in result[2] or "差距" in result[2] or "完成" in result[2] or "時間" in result[2]
    
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
        
        result = build_narrative(bundle, events, ai_native=True)
        
        assert isinstance(result, list)
        assert len(result) == 3
        
        # First two lines should be the events (sorted by severity)
        assert "Lap 2" in result[0] or "第2圈" in result[0]
        assert ("stood out" in result[0] or "突出" in result[0] or "異常" in result[0])
        assert ("Position shift" in result[1] or "位置" in result[1])
        
        # Should have session stats as fallback
        assert ("Best lap" in result[2] or "最佳單圈" in result[2] or "完成" in result[2])
    
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
        
        result = build_narrative(bundle, events, ai_native=True)
        
        assert isinstance(result, list)
        assert len(result) == 3
        
        # All lines should be from events
        assert "Lap 2" in result[0] or "第2圈" in result[0]
        assert ("Position shift" in result[1] or "位置" in result[1])
        assert ("Section IM1a" in result[2] or "IM1a" in result[2])
        
        # No fallback lines should be added
        assert "Session completed." not in result[0] and "Session completed." not in result[1] and "Session completed." not in result[2]
        assert "No significant anomalies detected." not in result[0] and "No significant anomalies detected." not in result[1] and "No significant anomalies detected." not in result[2]
        assert "Data analysis complete." not in result[0] and "Data analysis complete." not in result[1] and "Data analysis complete." not in result[2]
    
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
        
        result = build_narrative(bundle, events, ai_native=False)
        
        # Should return fallback lines when ai_native is False
        assert isinstance(result, list)
        assert len(result) == 3
    
    def test_empty_bundle_with_fallback(self):
        """Test narrative with empty bundle."""
        empty_bundle = SessionBundle(
            session=self.session,
            laps=[],  # No laps
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        result = build_narrative(empty_bundle, [], ai_native=True)
        
        # Empty bundle with no laps returns generic fallbacks
        assert isinstance(result, list)
        assert len(result) == 3
    
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
        
        result = build_narrative(bundle, [], ai_native=True)
        
        # Bundle with invalid lap times returns generic fallbacks
        assert isinstance(result, list)
        assert len(result) == 3
    
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
        
        result = build_narrative(bundle, [event], ai_native=True)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert "Lap 1" in result[0] or "第1圈" in result[0]
        assert ("stood out" in result[0] or "突出" in result[0] or "異常" in result[0] or "event" in result[0])
    
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
        for line in result:
            if "Best lap" in line and "median" in line:
                stats_line = line
                break
        
        # Check for either English or Chinese stats line
        if stats_line is not None:
            assert "100000" in stats_line  # Best lap
            assert "110000" in stats_line  # Median (sorted: 100k, 105k, 110k, 115k, 120k)
        else:
            # Check if any line contains expected elements
            found_stats = any("100000" in line and ("best" in line.lower() or "最佳" in line) for line in result)
            found_median = any("110000" in line and ("median" in line.lower() or "中位數" in line) for line in result)
            assert found_stats and found_median, f"No stats line found in {result}"
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
        assert len(result1) == len(result2)
        
        # All lines should have similar structure
        for i, (line1, line2) in enumerate(zip(result1, result2)):
            if i == 0:
                assert line1 == line2  # Should be identical
            else:
                # Subsequent lines may differ slightly
                assert isinstance(line1, str)
                assert isinstance(line2, str)
                assert len(line1) > 0
                assert len(line2) > 0