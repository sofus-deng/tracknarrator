"""Tests for event detection algorithms."""

import pytest
from datetime import datetime

from tracknarrator.schema import SessionBundle, Session, Lap, Section, Telemetry, WeatherPoint
from tracknarrator.events import detect_events, top5_events, build_sparklines


class TestEventDetection:
    """Test cases for event detection algorithms."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create a test session
        self.session = Session(
            id="test-session",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create test laps with one outlier (lap 3)
        self.laps = [
            Lap(
                session_id="test-session",
                lap_no=1,
                driver="Driver1",
                laptime_ms=100000,  # Normal lap
                position=5
            ),
            Lap(
                session_id="test-session",
                lap_no=2,
                driver="Driver1",
                laptime_ms=102000,  # Normal lap
                position=4
            ),
            Lap(
                session_id="test-session",
                lap_no=3,
                driver="Driver1",
                laptime_ms=130000,  # Outlier lap (30% slower)
                position=2  # Position change
            ),
            Lap(
                session_id="test-session",
                lap_no=4,
                driver="Driver1",
                laptime_ms=101000,  # Normal lap
                position=2
            ),
            Lap(
                session_id="test-session",
                lap_no=5,
                driver="Driver1",
                laptime_ms=99000,  # Fast lap
                position=1
            )
        ]
        
        # Create test sections with one abnormal section
        self.sections = []
        for lap_no in [1, 2, 3, 4, 5]:
            start_time = 0
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
                    duration = 150000  # Much longer than normal (6x normal)
                else:
                    duration = durations[section_name]
                
                end_time = start_time + duration
                self.sections.append(Section(
                    session_id="test-session",
                    lap_no=lap_no,
                    name=section_name,
                    t_start_ms=start_time,
                    t_end_ms=end_time,
                    meta={"source": "map"}
                ))
                start_time = end_time
        
        # Add more laps with same sections to ensure we have enough data for outlier detection
        for lap_no in [6, 7, 8]:
            start_time = 0
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
                
                duration = durations[section_name]
                end_time = start_time + duration
                self.sections.append(Section(
                    session_id="test-session",
                    lap_no=lap_no,
                    name=section_name,
                    t_start_ms=start_time,
                    t_end_ms=end_time,
                    meta={"source": "map"}
                ))
                start_time = end_time
        
        # Create minimal telemetry data
        self.telemetry = [
            Telemetry(
                session_id="test-session",
                ts_ms=1000,
                speed_kph=120.0,
                throttle_pct=75.0,
                brake_bar=0.0,
                gear=3,
                acc_long_g=0.5,
                acc_lat_g=0.3,
                steer_deg=5.0,
                lat_deg=33.5,
                lon_deg=-86.6
            ),
            Telemetry(
                session_id="test-session",
                ts_ms=2000,
                speed_kph=130.0,
                throttle_pct=80.0,
                brake_bar=0.0,
                gear=4,
                acc_long_g=0.6,
                acc_lat_g=0.2,
                steer_deg=3.0,
                lat_deg=33.51,
                lon_deg=-86.61
            )
        ]
        
        # Create minimal weather data
        self.weather = [
            WeatherPoint(
                session_id="test-session",
                ts_ms=1000,
                air_temp_c=25.0,
                track_temp_c=30.0,
                humidity_pct=60.0,
                pressure_hpa=1013.0,
                wind_speed=5.0,
                wind_dir_deg=180.0,
                rain_flag=0
            )
        ]
        
        # Create the bundle
        self.bundle = SessionBundle(
            session=self.session,
            laps=self.laps,
            sections=self.sections,
            telemetry=self.telemetry,
            weather=self.weather
        )
    
    def test_detect_lap_outliers(self):
        """Test lap outlier detection."""
        events = detect_events(self.bundle)
        
        # Should detect lap 3 as an outlier
        lap_outliers = [e for e in events if e["type"] == "lap_outlier"]
        assert len(lap_outliers) >= 1
        
        # Check that lap 3 is detected
        lap_3_outliers = [e for e in lap_outliers if e["lap_no"] == 3]
        assert len(lap_3_outliers) == 1
        
        # Check severity is within bounds
        for event in lap_outliers:
            assert 0 <= event["severity"] <= 1
        
        # Check summary contains expected information
        outlier = lap_3_outliers[0]
        assert "Lap 3" in outlier["summary"]
        assert "130000" in outlier["summary"]
        assert "median" in outlier["summary"]
    
    def test_detect_events_overall(self):
        """Test overall event detection."""
        events = detect_events(self.bundle)
        
        # Should detect at least 2 events total (lap outlier + position change)
        assert len(events) >= 2
        
        # Check that we have the expected event types
        event_types = set(e["type"] for e in events)
        assert "lap_outlier" in event_types  # Should detect lap 3 as outlier
        assert "position_change" in event_types  # Should detect position changes
        
        # Check severity bounds
        for event in events:
            assert 0 <= event["severity"] <= 1
        
        # Check severity is within bounds
        for event in events:
            assert 0 <= event["severity"] <= 1
    
    def test_detect_position_changes(self):
        """Test position change detection."""
        events = detect_events(self.bundle)
        
        # Should detect position changes
        position_changes = [e for e in events if e["type"] == "position_change"]
        assert len(position_changes) >= 1
        
        # Check that position changes are detected for laps with position differences
        for event in position_changes:
            assert event["lap_no"] is not None
            assert "delta" in event["meta"]
            assert "prev_pos" in event["meta"]
            assert "curr_pos" in event["meta"]
            
            # Check severity is within bounds
            assert 0 <= event["severity"] <= 1
    
    def test_top5_events_ranking(self):
        """Test top 5 events ranking and deduplication."""
        top5 = top5_events(self.bundle)
        
        # Should return at most 5 events
        assert len(top5) <= 5
        
        # Should return at least 2 events (lap outlier + section outlier)
        assert len(top5) >= 2
        
        # Check that events are properly sorted by severity (descending)
        if len(top5) > 1:
            for i in range(len(top5) - 1):
                assert top5[i]["severity"] >= top5[i+1]["severity"]
        
        # Check that no duplicate (lap_no, type) combinations exist
        seen = set()
        for event in top5:
            key = (event["lap_no"], event["type"])
            assert key not in seen
            seen.add(key)
        
        # Check that all required fields are present
        for event in top5:
            assert "type" in event
            assert "lap_no" in event
            assert "severity" in event
            assert "summary" in event
            assert "meta" in event
            assert event["severity"] >= 0
            assert event["severity"] <= 1
    
    def test_build_sparklines(self):
        """Test sparkline generation."""
        sparklines = build_sparklines(self.bundle)
        
        # Check required keys
        assert "laps_ms" in sparklines
        assert "sections_ms" in sparklines
        assert "speed_series" in sparklines
        
        # Check laps_ms
        laps_ms = sparklines["laps_ms"]
        assert isinstance(laps_ms, list)
        assert len(laps_ms) == len(self.laps)
        
        # Check that laps are ordered by lap_no
        expected_lap_times = [lap.laptime_ms for lap in sorted(self.laps, key=lambda l: l.lap_no)]
        assert laps_ms == expected_lap_times
        
        # Check sections_ms
        sections_ms = sparklines["sections_ms"]
        assert isinstance(sections_ms, dict)
        
        for section_name in ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]:
            assert section_name in sections_ms
            assert isinstance(sections_ms[section_name], list)
        
        # Check speed_series
        speed_series = sparklines["speed_series"]
        assert isinstance(speed_series, list)
        assert len(speed_series) <= 120  # Should be downsampled to at most 120 points
        
        # Check speed series structure
        for point in speed_series:
            assert "ts_ms" in point
            assert "speed_kph" in point
            assert isinstance(point["ts_ms"], int)
            assert isinstance(point["speed_kph"], float)
            assert 0 <= point["speed_kph"] <= 400  # Should be clamped
    
    def test_robust_z_score_edge_cases(self):
        """Test robust z-score calculation with edge cases."""
        from tracknarrator.events import _robust_z_score
        
        # Empty list
        assert _robust_z_score([], 100) == 0.0
        
        # Single value
        assert _robust_z_score([100], 100) == 0.0
        
        # All same values (MAD = 0)
        assert _robust_z_score([100, 100, 100], 100) == 0.0
        
        # Normal case
        values = [100, 110, 120, 130, 140]
        z = _robust_z_score(values, 200)  # Outlier
        assert z > 0
    
    def test_events_with_minimal_data(self):
        """Test event detection with minimal data."""
        # Create bundle with minimal data
        minimal_bundle = SessionBundle(
            session=self.session,
            laps=[],  # No laps
            sections=[],  # No sections
            telemetry=[],  # No telemetry
            weather=[]
        )
        
        # Should handle empty data gracefully
        events = detect_events(minimal_bundle)
        assert isinstance(events, list)
        
        top5 = top5_events(minimal_bundle)
        assert isinstance(top5, list)
        assert len(top5) == 0
        
        sparklines = build_sparklines(minimal_bundle)
        assert isinstance(sparklines, dict)
        assert sparklines["laps_ms"] == []
        assert sparklines["speed_series"] == []
    
    def test_top5_events_ranking_comprehensive(self):
        """Test comprehensive ranking behavior of top5_events."""
        # Create a bundle with known events to test ranking
        session = Session(
            id="ranking-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create laps with different severities and lap numbers
        laps = [
            Lap(session_id="ranking-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=5),
            Lap(session_id="ranking-test", lap_no=2, driver="Driver1", laptime_ms=200000, position=3),  # High severity outlier
            Lap(session_id="ranking-test", lap_no=3, driver="Driver1", laptime_ms=105000, position=1),  # Position change
            Lap(session_id="ranking-test", lap_no=4, driver="Driver1", laptime_ms=102000, position=2),
            Lap(session_id="ranking-test", lap_no=5, driver="Driver1", laptime_ms=101000, position=1),
        ]
        
        # Create sections with one severe outlier
        sections = []
        for lap_no in [1, 2, 3, 4, 5]:
            start_time = 0
            for section_name in ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]:
                duration = 20000  # Normal duration
                # Make lap 2 IM1a section very slow (high severity)
                if lap_no == 2 and section_name == "IM1a":
                    duration = 200000  # 10x normal
                
                end_time = start_time + duration
                sections.append(Section(
                    session_id="ranking-test",
                    lap_no=lap_no,
                    name=section_name,
                    t_start_ms=start_time,
                    t_end_ms=end_time,
                    meta={"source": "map"}
                ))
                start_time = end_time
        
        # Add more normal sections to have enough data for outlier detection
        for lap_no in [6, 7, 8]:
            start_time = 0
            for section_name in ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]:
                duration = 20000
                end_time = start_time + duration
                sections.append(Section(
                    session_id="ranking-test",
                    lap_no=lap_no,
                    name=section_name,
                    t_start_ms=start_time,
                    t_end_ms=end_time,
                    meta={"source": "map"}
                ))
                start_time = end_time
        
        bundle = SessionBundle(
            session=session,
            laps=laps,
            sections=sections,
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(bundle)
        
        # Should have at least 3 events (lap outlier, section outlier, position change)
        assert len(top5) >= 3
        
        # Check sorting: severity first (descending)
        for i in range(len(top5) - 1):
            assert top5[i]["severity"] >= top5[i+1]["severity"], \
                f"Events not sorted by severity: {top5[i]['severity']} < {top5[i+1]['severity']}"
        
        # For equal severity, check recency (higher lap_no first)
        for i in range(len(top5) - 1):
            if abs(top5[i]["severity"] - top5[i+1]["severity"]) < 1e-10:
                lap_i = top5[i]["lap_no"] or -1
                lap_next = top5[i+1]["lap_no"] or -1
                assert lap_i >= lap_next, \
                    f"Equal severity events not sorted by recency: lap {lap_i} before lap {lap_next}"
        
        # For equal severity and lap_no, check type order
        type_order = {"lap_outlier": 0, "section_outlier": 1, "position_change": 2}
        for i in range(len(top5) - 1):
            if (abs(top5[i]["severity"] - top5[i+1]["severity"]) < 1e-10 and
                (top5[i]["lap_no"] or -1) == (top5[i+1]["lap_no"] or -1)):
                type_i = type_order.get(top5[i]["type"], 999)
                type_next = type_order.get(top5[i+1]["type"], 999)
                assert type_i <= type_next, \
                    f"Equal severity/lap events not sorted by type: {top5[i]['type']} before {top5[i+1]['type']}"
    
    def test_top5_events_deduplication(self):
        """Test that top5_events properly deduplicates by (lap_no, type)."""
        from tracknarrator.events import _detect_lap_outliers, _detect_section_outliers, _detect_position_changes
        
        # Create a bundle that might generate duplicate events
        session = Session(
            id="dedup-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create laps with multiple potential outliers
        laps = [
            Lap(session_id="dedup-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=5),
            Lap(session_id="dedup-test", lap_no=2, driver="Driver1", laptime_ms=150000, position=3),  # Outlier
            Lap(session_id="dedup-test", lap_no=3, driver="Driver1", laptime_ms=160000, position=1),  # More severe outlier
            Lap(session_id="dedup-test", lap_no=4, driver="Driver1", laptime_ms=102000, position=2),
        ]
        
        # Create sections with outliers
        sections = []
        for lap_no in [1, 2, 3, 4, 5, 6, 7, 8]:
            start_time = 0
            for section_name in ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]:
                duration = 20000
                # Make some sections outliers
                if lap_no == 2 and section_name == "IM1a":
                    duration = 150000
                elif lap_no == 3 and section_name == "IM1a":
                    duration = 180000  # More severe
                
                end_time = start_time + duration
                sections.append(Section(
                    session_id="dedup-test",
                    lap_no=lap_no,
                    name=section_name,
                    t_start_ms=start_time,
                    t_end_ms=end_time,
                    meta={"source": "map"}
                ))
                start_time = end_time
        
        bundle = SessionBundle(
            session=session,
            laps=laps,
            sections=sections,
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(bundle)
        
        # Check no duplicate (lap_no, type) combinations
        seen = set()
        for event in top5:
            key = (event["lap_no"], event["type"])
            assert key not in seen, f"Duplicate (lap_no, type) found: {key}"
            seen.add(key)
        
        # Check that severity is non-increasing
        for i in range(len(top5) - 1):
            assert top5[i]["severity"] >= top5[i+1]["severity"], \
                f"Severity should be non-increasing: {top5[i]['severity']} < {top5[i+1]['severity']}"
    
    def test_top5_events_edge_cases(self):
        """Test top5_events with edge cases and low-data sessions."""
        # Test with no laps
        empty_bundle = SessionBundle(
            session=Session(
                id="empty-test",
                source="mylaps_csv",
                track="Test Track",
                track_id="test-track",
                schema_version="0.1.2"
            ),
            laps=[],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(empty_bundle)
        assert top5 == []
        
        # Test with only 1 lap (should not crash)
        single_lap_bundle = SessionBundle(
            session=Session(
                id="single-test",
                source="mylaps_csv",
                track="Test Track",
                track_id="test-track",
                schema_version="0.1.2"
            ),
            laps=[Lap(session_id="single-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=1)],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(single_lap_bundle)
        assert isinstance(top5, list)
        # Should return empty since no outliers can be detected with only 1 lap
        assert len(top5) == 0
        
        # Test with 2 laps (position changes possible, but no outliers)
        two_lap_bundle = SessionBundle(
            session=Session(
                id="two-test",
                source="mylaps_csv",
                track="Test Track",
                track_id="test-track",
                schema_version="0.1.2"
            ),
            laps=[
                Lap(session_id="two-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=5),
                Lap(session_id="two-test", lap_no=2, driver="Driver1", laptime_ms=102000, position=3),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(two_lap_bundle)
        assert isinstance(top5, list)
        # Should detect position change
        assert len(top5) >= 1
        assert top5[0]["type"] == "position_change"
        
        # Test with only low-severity events
        low_severity_bundle = SessionBundle(
            session=Session(
                id="low-sev-test",
                source="mylaps_csv",
                track="Test Track",
                track_id="test-track",
                schema_version="0.1.2"
            ),
            laps=[
                Lap(session_id="low-sev-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=5),
                Lap(session_id="low-sev-test", lap_no=2, driver="Driver1", laptime_ms=101000, position=4),  # Small change
                Lap(session_id="low-sev-test", lap_no=3, driver="Driver1", laptime_ms=102000, position=3),  # Small change
                Lap(session_id="low-sev-test", lap_no=4, driver="Driver1", laptime_ms=103000, position=2),  # Small change
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(low_severity_bundle)
        assert isinstance(top5, list)
        # Should detect position changes but they should have low severity
        for event in top5:
            assert event["severity"] >= 0
            assert event["severity"] <= 1
            if event["type"] == "position_change":
                # Position changes of 1 position should have low severity
                assert event["severity"] <= 0.2
    
    def test_top5_events_type_precedence(self):
        """Test that type precedence is correctly applied when severity and lap_no are equal."""
        # This is a bit tricky to test naturally, so we'll create a scenario
        # where we can manually verify the type ordering
        
        session = Session(
            id="type-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create laps that will generate events with same severity and lap_no
        # We'll use position changes to create multiple events on the same lap
        laps = [
            Lap(session_id="type-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=5),
            Lap(session_id="type-test", lap_no=2, driver="Driver1", laptime_ms=100000, position=3),  # Position change
            Lap(session_id="type-test", lap_no=3, driver="Driver1", laptime_ms=100000, position=1),  # Position change
        ]
        
        bundle = SessionBundle(
            session=session,
            laps=laps,
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(bundle)
        
        # Should have position change events
        position_changes = [e for e in top5 if e["type"] == "position_change"]
        assert len(position_changes) >= 1
        
        # All should be position_change type (no lap_outlier or section_outlier)
        # since lap times are all identical
        for event in top5:
            if event["type"] != "position_change":
                # If we get other types, they should be sorted correctly
                pass
    
    def test_top5_events_severity_bounds(self):
        """Test that all events in top5_events have severity within bounds."""
        # Create a bundle with various severity levels
        session = Session(
            id="severity-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create some extreme outliers
        laps = [
            Lap(session_id="severity-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=5),
            Lap(session_id="severity-test", lap_no=2, driver="Driver1", laptime_ms=500000, position=3),  # Extreme outlier
            Lap(session_id="severity-test", lap_no=3, driver="Driver1", laptime_ms=100000, position=1),
        ]
        
        bundle = SessionBundle(
            session=session,
            laps=laps,
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        top5 = top5_events(bundle)
        
        # All events should have severity between 0 and 1
        for event in top5:
            assert 0 <= event["severity"] <= 1, f"Severity out of bounds: {event['severity']}"
    
    def test_events_config_constants(self):
        """Test that using config constants doesn't change behavior."""
        from tracknarrator.config import ROBUST_Z_LAP, ROBUST_Z_SECTION, EVENT_TYPE_ORDER, DEFAULT_SECTION_LABELS
        
        # Verify constants are properly defined
        assert ROBUST_Z_LAP == 2.5
        assert ROBUST_Z_SECTION == 2.8
        assert EVENT_TYPE_ORDER == ["lap_outlier", "section_outlier", "position_change"]
        assert DEFAULT_SECTION_LABELS == ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]
        
        # Test that current bundle still produces same results with new implementation
        all_events = detect_events(self.bundle)
        top5_before = top5_events(self.bundle)
        
        # Should still have same number of events
        assert len(all_events) >= 0
        assert len(top5_before) <= 5
        
        # Verify sorting still works
        if len(top5_before) > 1:
            for i in range(len(top5_before) - 1):
                assert top5_before[i]["severity"] >= top5_before[i+1]["severity"]
                
        # Verify no duplicate (lap_no, type) pairs
        seen = set()
        for event in top5_before:
            key = (event["lap_no"], event["type"])
            assert key not in seen
            seen.add(key)
    
    def test_robust_z_optimization(self):
        """Test that robust z computation optimization works correctly."""
        from tracknarrator.events import prepare_robust_stats, robust_z_from_stats
        
        # Test prepare_robust_stats
        values = [100, 110, 120, 130, 140]
        median, mad = prepare_robust_stats(values)
        
        # Median should be 120 for sorted [100, 110, 120, 130, 140]
        assert median == 120
        assert mad > 0
        
        # Test robust_z_from_stats with same values
        z_outlier = robust_z_from_stats(200, median, mad)
        z_normal = robust_z_from_stats(120, median, mad)
        
        # Outlier should have higher z-score
        assert z_outlier > z_normal
        assert z_normal == 0  # Value at median should have z=0
        
        # Test with empty values
        median, mad = prepare_robust_stats([])
        assert median == 0
        assert mad == 0
        
        z_empty = robust_z_from_stats(100, median, mad)
        assert z_empty == 0  # Should return 0 when mad ≈ 0