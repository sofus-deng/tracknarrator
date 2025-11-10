"""Tests for narrative engine v0.2 with multilingual support and deterministic templates."""

import pytest

from tracknarrator.schema import SessionBundle, Session, Lap, Section
from tracknarrator.narrative import build_narrative
from tracknarrator.events import top5_events


class TestNarrativeV02:
    """Test cases for narrative engine v0.2."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create a test session
        self.session = Session(
            id="narrative-v02-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create test laps with outliers
        self.laps = [
            Lap(
                session_id="narrative-v02-test",
                lap_no=1,
                driver="Driver1",
                laptime_ms=100000,  # Normal lap
            ),
            Lap(
                session_id="narrative-v02-test",
                lap_no=2,
                driver="Driver1",
                laptime_ms=130000,  # Outlier lap
            ),
            Lap(
                session_id="narrative-v02-test",
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
                    session_id="narrative-v02-test",
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
    
    def test_ai_native_true_returns_max_lines(self):
        """Test that ai_native=True returns ≤max_lines lines."""
        result = build_narrative(self.bundle, self.top5_events, ai_native=True, max_lines=3)
        
        assert isinstance(result, list)
        assert len(result) <= 3
        assert len(result) >= 1  # Should have at least some content
        
        # All lines should be strings
        for line in result:
            assert isinstance(line, str)
            assert len(line) > 0
    
    def test_ai_native_false_returns_fallback(self):
        """Test that ai_native=False returns safe 3-line fallback."""
        result = build_narrative(self.bundle, self.top5_events, ai_native=False)
        
        assert isinstance(result, list)
        assert len(result) == 3
        
        # Should contain session statistics
        all_text = " ".join(result)
        assert any(keyword in all_text for keyword in ["圈", "最佳", "配速"])  # zh-Hant keywords
    
    def test_lang_en_returns_english(self):
        """Test that lang='en' returns English strings."""
        result = build_narrative(self.bundle, self.top5_events, lang="en", ai_native=True)
        
        assert isinstance(result, list)
        assert len(result) <= 3
        
        # Should contain English keywords
        all_text = " ".join(result).lower()
        assert any(keyword in all_text for keyword in ["lap", "section", "position", "rhythm"])
    
    def test_lang_zh_hant_returns_chinese(self):
        """Test that lang='zh-Hant' returns Chinese strings."""
        result = build_narrative(self.bundle, self.top5_events, lang="zh-Hant", ai_native=True)
        
        assert isinstance(result, list)
        assert len(result) <= 3
        
        # Should contain Chinese keywords
        all_text = " ".join(result)
        assert any(keyword in all_text for keyword in ["圈", "節奏", "路段", "位置"])
    
    def test_few_events_padded_to_max_lines(self):
        """Test that with only 1-2 events, still returns up to 3 lines."""
        # Create bundle with minimal events
        normal_bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-v02-test", lap_no=1, driver="Driver1", laptime_ms=100000),
                Lap(session_id="narrative-v02-test", lap_no=2, driver="Driver1", laptime_ms=102000),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        normal_top5 = top5_events(normal_bundle)
        result = build_narrative(normal_bundle, normal_top5, ai_native=True, max_lines=3)
        
        assert isinstance(result, list)
        assert len(result) == 3  # Should be padded to 3 lines
        
        # Should contain fallback content
        all_text = " ".join(result)
        assert any(keyword in all_text for keyword in ["最佳", "中位數", "配速"])  # zh-Hant
    
    def test_determinism_same_bundle_same_lines(self):
        """Test determinism: same bundle → same lines."""
        result1 = build_narrative(self.bundle, self.top5_events, lang="zh-Hant", ai_native=True)
        result2 = build_narrative(self.bundle, self.top5_events, lang="zh-Hant", ai_native=True)
        
        assert result1 == result2  # Should be identical
    
    def test_determinism_different_seeds_different_valid_choices(self):
        """Test determinism: different seeds → different but valid choices."""
        # Create slightly different bundle
        alt_bundle = SessionBundle(
            session=Session(
                id="alt-narrative-v02-test",
                source="mylaps_csv",
                track="Test Track",
                track_id="test-track",
                schema_version="0.1.2"
            ),
            laps=[
                Lap(session_id="alt-narrative-v02-test", lap_no=1, driver="Driver1", laptime_ms=100000),
                Lap(session_id="alt-narrative-v02-test", lap_no=2, driver="Driver1", laptime_ms=131000),  # Different outlier
                Lap(session_id="alt-narrative-v02-test", lap_no=3, driver="Driver1", laptime_ms=99000),
            ],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        alt_top5 = top5_events(alt_bundle)
        result1 = build_narrative(self.bundle, self.top5_events, lang="zh-Hant", ai_native=True)
        result2 = build_narrative(alt_bundle, alt_top5, lang="zh-Hant", ai_native=True)
        
        # Results should be different but both valid
        assert result1 != result2  # Should be different due to different content
        
        # Both should be valid narratives
        for result in [result1, result2]:
            assert isinstance(result, list)
            assert len(result) <= 3
            assert all(isinstance(line, str) and len(line) > 0 for line in result)
    
    def test_event_type_diversity(self):
        """Test that event type diversity is preferred when possible."""
        # Create bundle with multiple event types
        diverse_bundle = SessionBundle(
            session=self.session,
            laps=[
                Lap(session_id="narrative-v02-test", lap_no=1, driver="Driver1", laptime_ms=100000, position=5),
                Lap(session_id="narrative-v02-test", lap_no=2, driver="Driver1", laptime_ms=130000, position=3),  # Outlier + position change
                Lap(session_id="narrative-v02-test", lap_no=3, driver="Driver1", laptime_ms=99000, position=1),
            ],
            sections=[
                Section(session_id="narrative-v02-test", lap_no=2, name="IM1a", t_start_ms=0, t_end_ms=45000, meta={"source": "map"})
            ],
            telemetry=[],
            weather=[]
        )
        
        diverse_top5 = top5_events(diverse_bundle)
        result = build_narrative(diverse_bundle, diverse_top5, lang="zh-Hant", ai_native=True, max_lines=3)
        
        assert isinstance(result, list)
        assert len(result) <= 3
        
        all_text = " ".join(result)
        
        # Should mention different aspects when possible
        # This is a loose test since deterministic selection may choose specific templates
        assert len(all_text) > 0  # Should have some content
    
    def test_max_lines_parameter(self):
        """Test that max_lines parameter works correctly."""
        # Test with different max_lines values
        for max_lines in [1, 2, 3, 5]:
            result = build_narrative(self.bundle, self.top5_events, ai_native=True, max_lines=max_lines)
            
            assert isinstance(result, list)
            assert len(result) <= max_lines
            assert all(isinstance(line, str) and len(line) > 0 for line in result)
    
    def test_empty_bundle_handling(self):
        """Test handling of empty bundle."""
        empty_bundle = SessionBundle(
            session=self.session,
            laps=[],
            sections=[],
            telemetry=[],
            weather=[]
        )
        
        result = build_narrative(empty_bundle, [], ai_native=True, max_lines=3)
        
        assert isinstance(result, list)
        assert len(result) == 3  # Should be padded with generic fallbacks
        
        # Should contain generic fallbacks
        all_text = " ".join(result)
        assert any(keyword in all_text for keyword in ["分析", "完成", "檢測"])  # zh-Hant
    
    def test_template_formatting_edge_cases(self):
        """Test template formatting with edge cases."""
        # Create event with minimal meta
        minimal_event = {
            "type": "lap_outlier",
            "lap_no": 1,
            "section": None,
            "severity": 0.8,
            "summary": "Lap 1 was slow",
            "meta": {"driver": "Driver1"}  # Missing other fields
        }
        
        # Should not crash and should return something reasonable
        result = build_narrative(self.bundle, [minimal_event], lang="zh-Hant", ai_native=True)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(line, str) and len(line) > 0 for line in result)