"""End-to-end pipeline tests for TrackNarrator."""

import json
import random
import string
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.tracknarrator.api import app
from src.tracknarrator.store import store


class TestE2EPipeline:
    """End-to-end pipeline tests."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.client = TestClient(app)
        # Clear store before each test
        store.sessions.clear()
        # Generate random session ID
        self.session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    def test_complete_pipeline(self):
        """Test complete pipeline: health, ingest all data types, verify bundle, test seed."""
        # 1. Health check
        response = self.client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["ok"] is True
        
        # 2. Ingest TRD long telemetry
        trd_path = Path(__file__).parent.parent.parent / "samples" / "trd_long_sample.csv"
        with open(trd_path, "rb") as f:
            response = self.client.post(
                f"/ingest/trd-long?session_id={self.session_id}",
                files={"file": ("trd_long.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        trd_data = response.json()
        assert trd_data["status"] == "success"
        assert trd_data["counts"]["telemetry_added"] > 0
        
        # 3. Ingest MYLAPS sections
        mylaps_path = Path(__file__).parent.parent.parent / "samples" / "mylaps_sections_sample.csv"
        with open(mylaps_path, "rb") as f:
            response = self.client.post(
                f"/ingest/mylaps-sections?session_id={self.session_id}",
                files={"file": ("mylaps_sections.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        mylaps_data = response.json()
        assert mylaps_data["status"] == "success"
        assert mylaps_data["counts"]["laps_added"] > 0
        assert mylaps_data["counts"]["sections_added"] > 0
        
        # 4. Ingest weather data
        weather_path = Path(__file__).parent.parent.parent / "samples" / "weather_ok.csv"
        with open(weather_path, "rb") as f:
            response = self.client.post(
                f"/ingest/weather?session_id={self.session_id}",
                files={"file": ("weather.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        weather_data = response.json()
        assert weather_data["status"] == "success"
        assert weather_data["counts"]["weather_added"] > 0
        
        # 5. Verify session bundle contains all data types
        response = self.client.get(f"/session/{self.session_id}/bundle")
        assert response.status_code == 200
        bundle_data = response.json()
        
        # Check telemetry data
        assert len(bundle_data["telemetry"]) > 0
        assert any(t["session_id"] == self.session_id for t in bundle_data["telemetry"])
        
        # Check laps data
        assert len(bundle_data["laps"]) > 0
        assert all(lap["session_id"] == self.session_id for lap in bundle_data["laps"])
        
        # Check sections data
        assert len(bundle_data["sections"]) > 0
        assert all(section["session_id"] == self.session_id for section in bundle_data["sections"])
        
        # Check weather data
        assert len(bundle_data["weather"]) > 0
        assert all(weather["session_id"] == self.session_id for weather in bundle_data["weather"])
        
        # 6. Test /dev/seed with weather items missing session_id
        # Create a session bundle with weather items that have no session_id
        seed_bundle = {
            "session": {
                "id": f"{self.session_id}_seeded",
                "source": "weather_csv",
                "track_id": "test-track"
            },
            "weather": [
                {
                    "ts_ms": 0,
                    "air_temp_c": 25.0,
                    "wind_kph": 5.0,
                    "humidity_pct": 55.0
                    # Note: no session_id field
                },
                {
                    "ts_ms": 3600000,
                    "air_temp_c": 26.0,
                    "wind_kph": 6.0,
                    "humidity_pct": 60.0
                    # Note: no session_id field
                }
            ]
        }
        
        response = self.client.post(
            "/dev/seed",
            json=seed_bundle
        )
        assert response.status_code == 200
        seed_data = response.json()
        assert seed_data["ok"] is True
        assert seed_data["session_id"] == f"{self.session_id}_seeded"
        assert seed_data["counts"]["weather_added"] == 2
        
        # Verify seeded weather data has session_id filled
        response = self.client.get(f"/session/{self.session_id}_seeded/bundle")
        assert response.status_code == 200
        seeded_bundle = response.json()
        assert len(seeded_bundle["weather"]) == 2
        assert all(weather["session_id"] == f"{self.session_id}_seeded" for weather in seeded_bundle["weather"])
    
    def test_weather_inspect_with_samples(self):
        """Test weather inspect endpoint with all sample files."""
        # Test weather_ok.csv
        weather_ok_path = Path(__file__).parent.parent.parent / "samples" / "weather_ok.csv"
        with open(weather_ok_path, "rb") as f:
            response = self.client.post(
                "/dev/inspect/weather",
                files={"file": ("weather.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        inspect_data = response.json()
        assert inspect_data["status"] == "ok"
        inspect = inspect_data["inspect"]
        assert inspect["rows_total"] == 3
        assert inspect["rows_accepted"] == 3
        assert "ts_ms" in inspect["recognized_headers"]
        assert "temp_c" in inspect["recognized_headers"]
        assert "wind_kph" in inspect["recognized_headers"]
        assert "humidity_pct" in inspect["recognized_headers"]
        
        # Test weather_utc.csv
        weather_utc_path = Path(__file__).parent.parent.parent / "samples" / "weather_utc.csv"
        with open(weather_utc_path, "rb") as f:
            response = self.client.post(
                "/dev/inspect/weather",
                files={"file": ("weather.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        inspect_data = response.json()
        assert inspect_data["status"] == "ok"
        inspect = inspect_data["inspect"]
        assert inspect["rows_total"] == 3
        assert inspect["rows_accepted"] == 3
        assert "utc" in inspect["recognized_headers"]
        
        # Test weather_semicolon.csv
        weather_semicolon_path = Path(__file__).parent.parent.parent / "samples" / "weather_semicolon.csv"
        with open(weather_semicolon_path, "rb") as f:
            response = self.client.post(
                "/dev/inspect/weather",
                files={"file": ("weather.csv", f, "text/csv")}
            )
        assert response.status_code == 200
        inspect_data = response.json()
        assert inspect_data["status"] == "ok"
        inspect = inspect_data["inspect"]
        assert inspect["rows_total"] == 2
        assert inspect["rows_accepted"] == 2
        assert "ts_ms" in inspect["recognized_headers"]
        assert "temp_c" in inspect["recognized_headers"]
        assert "wind_kph" in inspect["recognized_headers"]