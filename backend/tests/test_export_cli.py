"""Tests for the export CLI script."""

import json
import pytest
import tempfile
import subprocess
import zipfile
import threading
import time
from pathlib import Path

from tracknarrator.schema import SessionBundle
from tracknarrator.api import app
from fastapi.testclient import TestClient
import uvicorn

# Load the sample bundle
BUNDLE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "bundle_sample_barber.json"


class TestExportCLI:
    """Test cases for the export CLI script."""
    
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
    
    def test_export_cli_basic(self):
        """Test basic CLI export functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_export.zip"
            
            # Start server in background for CLI tests
            def run_server():
                uvicorn.run(app, host="localhost", port=8000, log_level="error")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            time.sleep(1)  # Give server time to start
            
            try:
                # Run CLI script
                result = subprocess.run([
                    "uv", "run", "python", "../scripts/export_session.py",
                    "--session", self.session_id,
                    "--out", str(output_file)
                ], capture_output=True, text=True, cwd=Path.cwd())
            finally:
                # Server will be cleaned up when thread exits
                pass
            
            # Check command succeeded
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            
            # Check output file was created
            assert output_file.exists(), "Export file was not created"
            
            # Check output is a valid ZIP file
            try:
                with zipfile.ZipFile(output_file, 'r') as zip_file:
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
                        
            except zipfile.BadZipFile:
                pytest.fail("Output file is not a valid ZIP file")
    
    def test_export_cli_with_language(self):
        """Test CLI export with language parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file_zh = Path(temp_dir) / "test_export_zh.zip"
            output_file_en = Path(temp_dir) / "test_export_en.zip"
            
            # Start server in background for CLI tests
            def run_server():
                uvicorn.run(app, host="localhost", port=8000, log_level="error")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            time.sleep(1)  # Give server time to start
            
            try:
                # Run CLI script for Chinese
                result_zh = subprocess.run([
                    "uv", "run", "python", "../scripts/export_session.py",
                    "--session", self.session_id,
                    "--out", str(output_file_zh),
                    "--lang", "zh-Hant"
                ], capture_output=True, text=True, cwd=Path.cwd())
                
                # Run CLI script for English
                result_en = subprocess.run([
                    "uv", "run", "python", "../scripts/export_session.py",
                    "--session", self.session_id,
                    "--out", str(output_file_en),
                    "--lang", "en"
                ], capture_output=True, text=True, cwd=Path.cwd())
            finally:
                # Server will be cleaned up when thread exits
                pass
            
            # Both should succeed
            assert result_zh.returncode == 0, f"Chinese CLI failed: {result_zh.stderr}"
            assert result_en.returncode == 0, f"English CLI failed: {result_en.stderr}"
            
            # Both files should exist
            assert output_file_zh.exists(), "Chinese export file was not created"
            assert output_file_en.exists(), "English export file was not created"
            
            # Both should be valid ZIP files
            with zipfile.ZipFile(output_file_zh, 'r') as zip_zh, \
                 zipfile.ZipFile(output_file_en, 'r') as zip_en:
                
                # Both should have same file structure
                assert zip_zh.namelist() == zip_en.namelist()
                
                # Extract coach_tips and compare
                with zip_zh.open("coach_tips.json") as f_zh, \
                     zip_en.open("coach_tips.json") as f_en:
                    
                    tips_zh = json.loads(f_zh.read().decode('utf-8'))
                    tips_en = json.loads(f_en.read().decode('utf-8'))
                    
                    # Both should be lists
                    assert isinstance(tips_zh, list)
                    assert isinstance(tips_en, list)
                    
                    # If there are tips, content should be different
                    if tips_zh and tips_en:
                        zh_content = json.dumps(tips_zh, ensure_ascii=False)
                        en_content = json.dumps(tips_en, ensure_ascii=False)
                        # Chinese should have Chinese characters
                        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in zh_content)
                        if has_chinese:
                            assert zh_content != en_content
    
    def test_export_cli_json_validation(self):
        """Test that CLI export produces valid JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_export.zip"
            
            # Start server in background for CLI tests
            def run_server():
                uvicorn.run(app, host="localhost", port=8000, log_level="error")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            time.sleep(1)  # Give server time to start
            
            try:
                # Run CLI script
                result = subprocess.run([
                    "uv", "run", "python", "../scripts/export_session.py",
                    "--session", self.session_id,
                    "--out", str(output_file)
                ], capture_output=True, text=True, cwd=Path.cwd())
            finally:
                # Server will be cleaned up when thread exits
                pass
            
            assert result.returncode == 0
            
            # Validate JSON content
            with zipfile.ZipFile(output_file, 'r') as zip_file:
                # Test each JSON file
                json_files = [
                    "summary.json",
                    "coach_tips.json", 
                    "events.json",
                    "cards.json",
                    "sparklines.json",
                    "kpis.json"
                ]
                
                for json_file in json_files:
                    with zip_file.open(json_file) as f:
                        content = f.read().decode('utf-8')
                        
                        # Should be valid JSON
                        try:
                            json_data = json.loads(content)
                            assert isinstance(json_data, (dict, list)), f"Invalid JSON structure in {json_file}"
                        except json.JSONDecodeError as e:
                            pytest.fail(f"Invalid JSON in {json_file}: {e}")
    
    def test_export_cli_nonexistent_session(self):
        """Test CLI export with non-existent session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_export.zip"
            
            # Start server in background for CLI tests
            def run_server():
                uvicorn.run(app, host="localhost", port=8000, log_level="error")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            time.sleep(1)  # Give server time to start
            
            try:
                # Run CLI script with non-existent session
                result = subprocess.run([
                    "uv", "run", "python", "../scripts/export_session.py",
                    "--session", "nonexistent-session",
                    "--out", str(output_file)
                ], capture_output=True, text=True, cwd=Path.cwd())
            finally:
                # Server will be cleaned up when thread exits
                pass
            
            # Should fail
            assert result.returncode != 0
            
            # Should have error message
            assert "404" in result.stderr or "not found" in result.stderr.lower()
            
            # Output file should not exist
            assert not output_file.exists()
    
    def test_export_cli_help(self):
        """Test CLI help functionality."""
        result = subprocess.run([
            "uv", "run", "python", "../scripts/export_session.py",
            "--help"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        # Should succeed and show help
        assert result.returncode == 0
        assert "--session" in result.stdout
        assert "--out" in result.stdout
        assert "--lang" in result.stdout
        assert "zh-Hant" in result.stdout
        assert "en" in result.stdout
    
    def test_export_cli_missing_args(self):
        """Test CLI with missing required arguments."""
        # Test missing --session
        result = subprocess.run([
            "uv", "run", "python", "../scripts/export_session.py",
            "--out", "/tmp/test.zip"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        assert result.returncode != 0
        
        # Test missing --out
        result = subprocess.run([
            "uv", "run", "python", "../scripts/export_session.py",
            "--session", "test-session"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        assert result.returncode != 0