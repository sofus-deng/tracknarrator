"""Tests for export pack narrative.json inclusion."""

import json
import zipfile
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tracknarrator.api import app
from tracknarrator.schema import SessionBundle, Session, Lap, Section
from tracknarrator.events import top5_events


client = TestClient(app)


class TestExportPackNarrative:
    """Test cases for narrative.json inclusion in export pack."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Create a test session
        self.session = Session(
            id="export-narrative-test",
            source="mylaps_csv",
            track="Test Track",
            track_id="test-track",
            schema_version="0.1.2"
        )
        
        # Create test laps with outliers
        self.laps = [
            Lap(
                session_id="export-narrative-test",
                lap_no=1,
                driver="Driver1",
                laptime_ms=100000,  # Normal lap
            ),
            Lap(
                session_id="export-narrative-test",
                lap_no=2,
                driver="Driver1",
                laptime_ms=130000,  # Outlier lap
            ),
            Lap(
                session_id="export-narrative-test",
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
                    session_id="export-narrative-test",
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
    
    def test_export_pack_includes_narrative_json(self):
        """Test that export pack includes narrative.json."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get export pack
        response = client.get("/session/export-narrative-test/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Extract and check ZIP contents
        zip_content = response.content
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Should include narrative.json
            assert "narrative.json" in file_list
            
            # Should also include all other expected files
            expected_files = {
                "summary.json",
                "coach_tips.json", 
                "events.json",
                "cards.json",
                "sparklines.json",
                "narrative.json",
                "kpis.json"
            }
            
            for expected_file in expected_files:
                assert expected_file in file_list, f"Missing {expected_file} in export"
    
    def test_export_narrative_json_structure(self):
        """Test that narrative.json has correct structure."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get export pack
        response = client.get("/session/export-narrative-test/export")
        assert response.status_code == 200
        
        # Extract narrative.json
        zip_content = response.content
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            narrative_content = zip_file.read("narrative.json").decode("utf-8")
            narrative_data = json.loads(narrative_content)
            
            # Check structure
            assert "lines" in narrative_data
            assert "lang" in narrative_data
            assert "ai_native" in narrative_data
            
            # Check types
            assert isinstance(narrative_data["lines"], list)
            assert isinstance(narrative_data["lang"], str)
            assert isinstance(narrative_data["ai_native"], bool)
            
            # Check values
            assert len(narrative_data["lines"]) <= 3
            assert len(narrative_data["lines"]) >= 1  # Should have some content
            assert narrative_data["lang"] == "zh-Hant"  # Default
            assert narrative_data["ai_native"] is True  # Default is now True
    
    def test_export_narrative_json_content_valid(self):
        """Test that narrative.json content is valid."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get export pack
        response = client.get("/session/export-narrative-test/export")
        assert response.status_code == 200
        
        # Extract narrative.json
        zip_content = response.content
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            narrative_content = zip_file.read("narrative.json").decode("utf-8")
            narrative_data = json.loads(narrative_content)
            
            # Check that lines are valid
            for line in narrative_data["lines"]:
                assert isinstance(line, str)
                assert len(line) > 0
                
                # Should contain relevant content based on our test data
                all_text = " ".join(narrative_data["lines"])
                assert len(all_text) > 0
    
    def test_export_narrative_lang_zh_hant(self):
        """Test export with zh-Hant language."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get export pack with zh-Hant
        response = client.get("/session/export-narrative-test/export?lang=zh-Hant")
        assert response.status_code == 200
        
        # Extract narrative.json
        zip_content = response.content
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            narrative_content = zip_file.read("narrative.json").decode("utf-8")
            narrative_data = json.loads(narrative_content)
            
            # Should have zh-Hant language
            assert narrative_data["lang"] == "zh-Hant"
            
            # Should contain Chinese keywords
            all_text = " ".join(narrative_data["lines"])
            assert any(keyword in all_text for keyword in ["圈", "節奏", "路段", "位置"])
    
    def test_export_narrative_lang_en(self):
        """Test export with en language."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get export pack with en
        response = client.get("/session/export-narrative-test/export?lang=en")
        assert response.status_code == 200
        
        # Extract narrative.json
        zip_content = response.content
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            narrative_content = zip_file.read("narrative.json").decode("utf-8")
            narrative_data = json.loads(narrative_content)
            
            # Should have en language
            assert narrative_data["lang"] == "en"
            
            # Should contain English keywords
            all_text = " ".join(narrative_data["lines"]).lower()
            assert any(keyword in all_text for keyword in ["lap", "section", "position", "rhythm"])
    
    def test_export_narrative_json_parsable(self):
        """Test that narrative.json is valid JSON."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get export pack
        response = client.get("/session/export-narrative-test/export")
        assert response.status_code == 200
        
        # Extract narrative.json
        zip_content = response.content
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            narrative_content = zip_file.read("narrative.json").decode("utf-8")
            
            # Should be valid JSON (no exception should be raised)
            narrative_data = json.loads(narrative_content)
            assert isinstance(narrative_data, dict)
    
    def test_export_narrative_nonexistent_session(self):
        """Test export with nonexistent session."""
        response = client.get("/session/nonexistent-session/export")
        assert response.status_code == 404
        
        error = response.json()
        assert "error" in error
        assert "Session nonexistent-session not found" in str(error)
    
    def test_export_narrative_with_fixture_data(self):
        """Test export with fixture bundle data."""
        # Load the sample bundle
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
        with open(fixtures_dir / "bundle_sample_barber.json", "r") as f:
            bundle_data = json.load(f)
        
        bundle = SessionBundle.model_validate(bundle_data)
        
        # Seed the fixture data
        response = client.post("/dev/seed", json=bundle.model_dump())
        assert response.status_code == 200

        # Derive session_id (prefer API response, then fixture, then default)
        try:
            session_id = (response.json() or {}).get("session_id")
        except Exception:
            session_id = None
        if not session_id:
            session_id = (
                locals().get("bundle", None).session_id
                if locals().get("bundle", None) is not None else
                locals().get("bundle_data", {}).get("session_id", "barber")
            )
       
        # Get export pack
        response = client.get(f"/session/{session_id}/export")
        assert response.status_code == 200
        
        # Extract and check ZIP contents
        zip_content = response.content
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Should include narrative.json
            assert "narrative.json" in file_list
            
            # Should be valid JSON
            narrative_content = zip_file.read("narrative.json").decode("utf-8")
            narrative_data = json.loads(narrative_content)
            
            # Should have correct structure
            assert "lines" in narrative_data
            assert "lang" in narrative_data
            assert "ai_native" in narrative_data
            assert isinstance(narrative_data["lines"], list)
    
    def test_export_narrative_deterministic_content(self):
        """Test that narrative content is deterministic across exports."""
        # Seed the test data
        bundle_data = self.bundle.model_dump()
        response = client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        # Get export pack twice
        response1 = client.get("/session/export-narrative-test/export?lang=zh-Hant")
        response2 = client.get("/session/export-narrative-test/export?lang=zh-Hant")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Extract narrative.json from both
        zip_content1 = response1.content
        zip_content2 = response2.content
        
        zip_buffer1 = io.BytesIO(zip_content1)
        zip_buffer2 = io.BytesIO(zip_content2)
        
        with zipfile.ZipFile(zip_buffer1, 'r') as zip_file1:
            narrative_content1 = zip_file1.read("narrative.json").decode("utf-8")
            narrative_data1 = json.loads(narrative_content1)
        
        with zipfile.ZipFile(zip_buffer2, 'r') as zip_file2:
            narrative_content2 = zip_file2.read("narrative.json").decode("utf-8")
            narrative_data2 = json.loads(narrative_content2)
        
        # Should be identical (deterministic)
        assert narrative_data1["lines"] == narrative_data2["lines"]
        assert narrative_data1["lang"] == narrative_data2["lang"]
        assert narrative_data1["ai_native"] == narrative_data2["ai_native"]