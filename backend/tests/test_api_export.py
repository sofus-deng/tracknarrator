"""Tests for the session export API endpoint."""

import json
import pytest
import zipfile
import tempfile
from pathlib import Path

from tracknarrator.schema import SessionBundle
from tracknarrator.api import app
from fastapi.testclient import TestClient

# Load the sample bundle
BUNDLE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "bundle_sample_barber.json"


class TestSessionExportAPI:
    """Test cases for the session export API endpoint."""
    
    def setup_method(self):
        """Set up test data before each test."""
        self.client = TestClient(app)
        
        # Load and seed the sample bundle
        with open(BUNDLE_PATH, 'r') as f:
            bundle_data = json.load(f)
        
        bundle = SessionBundle(**bundle_data)
        session_id = bundle.session.id
        
        # Seed the bundle
        response = self.client.post("/dev/seed", json=bundle_data)
        assert response.status_code == 200
        
        self.session_id = session_id
    
    def test_export_endpoint_basic(self):
        """Test basic export endpoint functionality."""
        response = self.client.get(f"/session/{self.session_id}/export")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Check content disposition header
        content_disposition = response.headers["content-disposition"]
        assert f"{self.session_id}_export.zip" in content_disposition
        assert "attachment" in content_disposition
    
    def test_export_endpoint_with_language(self):
        """Test export endpoint with language parameter."""
        # Test Chinese
        response_zh = self.client.get(f"/session/{self.session_id}/export?lang=zh-Hant")
        assert response_zh.status_code == 200
        
        # Test English
        response_en = self.client.get(f"/session/{self.session_id}/export?lang=en")
        assert response_en.status_code == 200
        
        # Both should be ZIP files
        assert response_zh.headers["content-type"] == "application/zip"
        assert response_en.headers["content-type"] == "application/zip"
    
    def test_export_endpoint_nonexistent_session(self):
        """Test export endpoint with non-existent session."""
        response = self.client.get("/session/nonexistent-session/export")
        
        assert response.status_code == 404
        error_data = response.json()
        # Check the actual error structure
        assert "error" in error_data
        assert "message" in error_data["error"]
        assert "not found" in error_data["error"]["message"].lower()
    
    def test_export_zip_contents(self):
        """Test that export ZIP contains all expected files with valid JSON."""
        response = self.client.get(f"/session/{self.session_id}/export")
        assert response.status_code == 200
        
        # Parse ZIP content
        zip_content = response.content
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(zip_content)
            temp_file.flush()
            
            with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                file_list = zip_file.namelist()
                
                # Check expected files are present
                expected_files = [
                    "summary.json",
                    "coach_tips.json", 
                    "events.json",
                    "cards.json",
                    "sparklines.json",
                    "kpis.json"
                ]
                
                for expected_file in expected_files:
                    assert expected_file in file_list, f"Missing file: {expected_file}"
                
                # Validate JSON content of each file
                for expected_file in expected_files:
                    with zip_file.open(expected_file) as f:
                        content = f.read().decode('utf-8')
                        
                        # Should be valid JSON
                        try:
                            json_data = json.loads(content)
                            assert isinstance(json_data, (dict, list)), f"Invalid JSON structure in {expected_file}"
                        except json.JSONDecodeError as e:
                            pytest.fail(f"Invalid JSON in {expected_file}: {e}")
    
    def test_export_json_structures(self):
        """Test that exported JSON files have correct structure."""
        response = self.client.get(f"/session/{self.session_id}/export")
        assert response.status_code == 200
        
        # Parse ZIP content
        zip_content = response.content
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(zip_content)
            temp_file.flush()
            
            with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                # Test summary.json structure
                with zip_file.open("summary.json") as f:
                    summary = json.loads(f.read().decode('utf-8'))
                    assert "events" in summary
                    assert "cards" in summary
                    assert "sparklines" in summary
                    assert isinstance(summary["events"], list)
                    assert isinstance(summary["cards"], list)
                    assert isinstance(summary["sparklines"], dict)
                
                # Test events.json structure
                with zip_file.open("events.json") as f:
                    events = json.loads(f.read().decode('utf-8'))
                    assert isinstance(events, list)
                    for event in events:
                        assert "type" in event
                        assert "severity" in event
                        assert "lap_no" in event
                
                # Test cards.json structure
                with zip_file.open("cards.json") as f:
                    cards = json.loads(f.read().decode('utf-8'))
                    assert isinstance(cards, list)
                    for card in cards:
                        assert "event_id" in card
                        assert "type" in card
                        assert "title" in card
                        assert "severity" in card
                
                # Test coach_tips.json structure
                with zip_file.open("coach_tips.json") as f:
                    tips = json.loads(f.read().decode('utf-8'))
                    assert isinstance(tips, list)
                    for tip in tips:
                        assert "tip_id" in tip
                        assert "title" in tip
                        assert "body" in tip
                        assert "severity" in tip
                        assert "event_ref" in tip
                
                # Test kpis.json structure
                with zip_file.open("kpis.json") as f:
                    kpis = json.loads(f.read().decode('utf-8'))
                    assert isinstance(kpis, dict)
                    assert "total_laps" in kpis
                    assert "best_lap_ms" in kpis
                    assert "median_lap_ms" in kpis
                    assert "session_duration_ms" in kpis
                    assert isinstance(kpis["total_laps"], int)
                    assert isinstance(kpis["best_lap_ms"], int)
                    assert isinstance(kpis["median_lap_ms"], (int, float))
                    assert isinstance(kpis["session_duration_ms"], int)
    
    def test_export_language_content(self):
        """Test that language parameter affects coach_tips content."""
        # Get Chinese export
        response_zh = self.client.get(f"/session/{self.session_id}/export?lang=zh-Hant")
        assert response_zh.status_code == 200
        
        # Get English export
        response_en = self.client.get(f"/session/{self.session_id}/export?lang=en")
        assert response_en.status_code == 200
        
        # Extract coach_tips from both
        def get_coach_tips(response_content):
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(response_content)
                temp_file.flush()
                
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    with zip_file.open("coach_tips.json") as f:
                        return json.loads(f.read().decode('utf-8'))
        
        tips_zh = get_coach_tips(response_zh.content)
        tips_en = get_coach_tips(response_en.content)
        
        # Both should be lists
        assert isinstance(tips_zh, list)
        assert isinstance(tips_en, list)
        
        # If there are tips, they should be in different languages
        if tips_zh and tips_en:
            # Chinese tips should contain Chinese characters
            zh_content = json.dumps(tips_zh, ensure_ascii=False)
            # English tips should not contain the same Chinese characters
            en_content = json.dumps(tips_en, ensure_ascii=False)
            
            # Basic check - Chinese should have Chinese characters if there are tips
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in zh_content)
            if has_chinese:
                # English version should be different
                assert zh_content != en_content