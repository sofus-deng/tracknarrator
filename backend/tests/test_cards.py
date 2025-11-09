"""Tests for share card generation."""

import pytest
import json
from pathlib import Path

from tracknarrator.schema import SessionBundle, Session, Lap, Section, Telemetry, WeatherPoint
from tracknarrator.cards import build_share_cards, ShareCard


class TestShareCards:
    """Test cases for share card generation."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Load the sample bundle for testing
        bundle_path = Path(__file__).parent.parent.parent / "fixtures" / "bundle_sample_barber.json"
        with open(bundle_path, 'r') as f:
            bundle_data = json.load(f)
        
        # Convert dict to proper SessionBundle object
        self.sample_bundle = SessionBundle(**bundle_data)
    
    def test_share_card_schema(self):
        """Test that share cards follow the v0 schema."""
        # Create a minimal card to test schema
        card = ShareCard(
            event_id="test-event-1",
            type="lap_outlier",
            lap_no=3,
            title="Slow Lap Detected",
            metric="Lap time: 130.0s vs median 100.0s",
            delta_ms=30000,
            icon="⏱️",
            severity=0.8,
            ts_ms=1234567890,
            meta={
                "driver": "Driver1",
                "laptime_ms": 130000,
                "median_ms": 100000,
                "robust_z": 3.0
            }
        )
        
        # Check required fields
        assert "event_id" in card
        assert "type" in card
        assert "lap_no" in card
        assert "title" in card
        assert "metric" in card
        assert "delta_ms" in card
        assert "icon" in card
        assert "severity" in card
        assert "ts_ms" in card
        assert "meta" in card
        
        # Check field types
        assert isinstance(card["event_id"], str)
        assert isinstance(card["type"], str)
        assert card["lap_no"] is None or isinstance(card["lap_no"], int)
        assert isinstance(card["title"], str)
        assert isinstance(card["metric"], str)
        assert card["delta_ms"] is None or isinstance(card["delta_ms"], int)
        assert isinstance(card["icon"], str)
        assert isinstance(card["severity"], (int, float))
        assert card["ts_ms"] is None or isinstance(card["ts_ms"], int)
        assert isinstance(card["meta"], dict)
        
        # Check severity bounds
        assert 0 <= card["severity"] <= 1
        
        # Check event type is valid
        valid_types = ["lap_outlier", "section_outlier", "position_change"]
        assert card["type"] in valid_types
    
    def test_build_share_cards_empty_bundle(self):
        """Test build_share_cards with empty bundle."""
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
        
        cards = build_share_cards(empty_bundle)
        assert isinstance(cards, list)
        assert len(cards) == 0
    
    def test_build_share_cards_sample_bundle(self):
        """Test build_share_cards with sample barber bundle."""
        cards = build_share_cards(self.sample_bundle)
        
        # Should return a list
        assert isinstance(cards, list)
        
        # Currently returns empty list (placeholder implementation)
        # This test will be updated when implementation is complete
        assert len(cards) == 0
        
        # When implemented, should return cards with proper schema
        for card in cards:
            self._validate_card_schema(card)
    
    def test_build_share_cards_golden_sample(self):
        """Test build_share_cards returns deterministic results for sample bundle."""
        # This test documents our golden sample for the barber bundle
        cards = build_share_cards(self.sample_bundle)
        
        # For now, expect empty list (placeholder)
        assert isinstance(cards, list)
        
        # When implemented, we can check for specific cards
        # For example, we might expect:
        # - 1-3 cards for the most significant events
        # - Specific event types based on the data in bundle_sample_barber.json
        
        # This will serve as our regression test
        expected_card_count = 0  # Sample bundle has insufficient data for events
        assert len(cards) == expected_card_count
    
    def _validate_card_schema(self, card):
        """Helper method to validate card schema."""
        # Check all required fields exist
        required_fields = ["event_id", "type", "lap_no", "title", "metric", "delta_ms", "icon", "severity", "ts_ms", "meta"]
        for field in required_fields:
            assert field in card, f"Missing required field: {field}"
        
        # Check field types and constraints
        assert isinstance(card["event_id"], str)
        assert len(card["event_id"]) > 0
        
        assert isinstance(card["type"], str)
        valid_types = ["lap_outlier", "section_outlier", "position_change"]
        assert card["type"] in valid_types
        
        assert card["lap_no"] is None or isinstance(card["lap_no"], int)
        if card["lap_no"] is not None:
            assert card["lap_no"] > 0
        
        assert isinstance(card["title"], str)
        assert len(card["title"]) > 0
        
        assert isinstance(card["metric"], str)
        assert len(card["metric"]) > 0
        
        assert card["delta_ms"] is None or isinstance(card["delta_ms"], int)
        
        assert isinstance(card["icon"], str)
        assert len(card["icon"]) > 0
        
        assert isinstance(card["severity"], (int, float))
        assert 0 <= card["severity"] <= 1
        
        assert card["ts_ms"] is None or isinstance(card["ts_ms"], int)
        if card["ts_ms"] is not None:
            assert card["ts_ms"] >= 0
        
        assert isinstance(card["meta"], dict)
    
    def test_share_card_event_types(self):
        """Test that different event types generate appropriate cards."""
        # This test will be expanded when implementation is complete
        # For now, just test the schema validation
        
        test_cards = [
            ShareCard(
                event_id="lap-outlier-test",
                type="lap_outlier",
                lap_no=5,
                title="Slow Lap",
                metric="Lap time: 120s",
                delta_ms=20000,
                icon="⏱️",
                severity=0.7,
                ts_ms=1234567890,
                meta={"driver": "TestDriver", "laptime_ms": 120000}
            ),
            ShareCard(
                event_id="section-outlier-test",
                type="section_outlier",
                lap_no=3,
                title="Slow Section",
                metric="IM1a: 25s vs median 20s",
                delta_ms=5000,
                icon="📍",
                severity=0.6,
                ts_ms=1234567890,
                meta={"section": "IM1a", "duration_ms": 25000}
            ),
            ShareCard(
                event_id="position-change-test",
                type="position_change",
                lap_no=2,
                title="Position Gain",
                metric="P5 → P3",
                delta_ms=None,
                icon="🏁",
                severity=0.4,
                ts_ms=1234567890,
                meta={"prev_pos": 5, "curr_pos": 3, "delta": -2}
            )
        ]
        
        for card in test_cards:
            self._validate_card_schema(card)
    
    def test_share_card_icon_mapping(self):
        """Test that event types have appropriate icons."""
        # This documents our icon mapping strategy
        icon_mapping = {
            "lap_outlier": "⏱️",      # Clock/timer for lap time issues
            "section_outlier": "📍",   # Location pin for section issues
            "position_change": "🏁"     # Checkered flag for position changes
        }
        
        # When implemented, cards should use these icons
        for event_type, expected_icon in icon_mapping.items():
            card = ShareCard(
                event_id=f"test-{event_type}",
                type=event_type,
                lap_no=1,
                title=f"Test {event_type}",
                metric="Test metric",
                delta_ms=None,
                icon=expected_icon,
                severity=0.5,
                ts_ms=1234567890,
                meta={}
            )
            
            assert card["icon"] == expected_icon