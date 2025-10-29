"""Tests for /dev/seed endpoint."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tracknarrator.api import app
from tracknarrator.schema import SessionBundle

# Get the path to the fixtures directory
fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

client = TestClient(app)


def test_seed_json():
    """Test seeding with JSON body."""
    # Load the sample bundle
    with open(fixtures_dir / "bundle_sample_barber.json", "r") as f:
        bundle_data = json.load(f)
    
    # Post the bundle
    response = client.post("/dev/seed", json=bundle_data)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == "json"
    assert data["session_id"] == "barber-demo-r1"
    
    # Check that data was added
    counts = data["counts"]
    assert counts.get("sessions_added", 0) == 1
    assert counts.get("laps_added", 0) == 2
    assert counts.get("sections_added", 0) == 8
    assert counts.get("telemetry_added", 0) == 8
    assert counts.get("weather_added", 0) == 2


def test_seed_file():
    """Test seeding with multipart file upload."""
    # Load the sample bundle
    with open(fixtures_dir / "bundle_sample_barber.json", "rb") as f:
        # Post the bundle as a file
        response = client.post(
            "/dev/seed",
            files={"file": ("bundle.json", f, "application/json")}
        )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == "file"
    assert data["session_id"] == "barber-demo-r1"


def test_seed_idempotent():
    """Test that seeding the same data twice is idempotent."""
    # Load the sample bundle
    with open(fixtures_dir / "bundle_sample_barber.json", "r") as f:
        bundle_data = json.load(f)
    
    # First seeding
    response1 = client.post("/dev/seed", json=bundle_data)
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Second seeding (should be idempotent)
    response2 = client.post("/dev/seed", json=bundle_data)
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Check idempotency
    assert data2["ok"] is True
    assert data2["session_id"] == data1["session_id"]
    
    # Second call should not add new sessions, but might update
    counts2 = data2["counts"]
    assert counts2.get("sessions_added", 0) == 0
    # laps/sections/telemetry/weather might be updated if data differs
    # but they shouldn't be added again if identical


def test_seed_oversize():
    """Test that oversized files are rejected."""
    # Create a large JSON payload (over 2MB)
    large_bundle = {
        "session": {
            "id": "test-oversize",
            "source": "mylaps_csv",
            "track": "Test Track",
            "track_id": "test-track",
            "schema_version": "0.1.2"
        },
        "telemetry": [
            {
                "session_id": "test-oversize",
                "ts_ms": i,
                "speed_kph": 100.0,
                "throttle_pct": 50.0,
                "brake_bar": 0.0,
                "gear": 3,
                "acc_long_g": 0.0,
                "acc_lat_g": 0.0,
                "steer_deg": 0.0,
                "lat_deg": 0.0,
                "lon_deg": 0.0
            }
            for i in range(100000)  # This will create a large payload
        ]
    }
    
    # Try to post the oversized bundle as a file
    large_json = json.dumps(large_bundle).encode("utf-8")
    response = client.post(
        "/dev/seed",
        files={"file": ("large.json", large_json, "application/json")}
    )
    
    # Should be rejected
    assert response.status_code == 413
    assert "too large" in response.json()["error"]["message"]


def test_seed_invalid():
    """Test that invalid JSON is rejected."""
    # Create invalid JSON
    invalid_json = b'{"invalid": json}'
    
    # Try to post the invalid JSON as a file
    response = client.post(
        "/dev/seed",
        files={"file": ("invalid.json", invalid_json, "application/json")}
    )
    
    # Should be rejected
    assert response.status_code == 400
    assert "Invalid seed JSON" in response.json()["error"]["message"]


def test_seed_empty_json():
    """Test that empty JSON body is rejected."""
    response = client.post("/dev/seed", json={})
    
    # Should be rejected due to validation error
    assert response.status_code == 400
    assert "validation error" in response.json()["error"]["message"]


def test_seed_no_input():
    """Test that request with no input is rejected."""
    response = client.post("/dev/seed")
    
    # Should be rejected
    assert response.status_code == 400
    assert "Provide either JSON body or multipart file" in response.json()["error"]["message"]