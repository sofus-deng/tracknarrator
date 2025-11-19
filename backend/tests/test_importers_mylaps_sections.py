"""Tests for MYLAPS sections CSV importer."""

import io

import pytest

from src.tracknarrator.importers.mylaps_sections_csv import MYLAPSSectionsCSVImporter
from src.tracknarrator.schema import Lap, Section


class TestMYLAPSSectionsCSVImporter:
    """Test cases for MYLAPS sections CSV importer."""
    
    def test_import_basic_sections(self):
        """Test importing basic sections data with standard headers."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456
2;1;1:22.123;0:11.234;0:24.567;0:37.890;0:51.123;1:04.456;1:22.123"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.warnings) == 0
        assert len(result.bundle.laps) == 2
        assert len(result.bundle.sections) == 12  # 2 laps * 6 sections each
        
        # Check laps
        lap1 = result.bundle.laps[0]
        assert lap1.session_id == "test-session"
        assert lap1.lap_no == 1
        assert lap1.driver == "No.1"
        assert lap1.laptime_ms == 83456  # 1:23.456 in ms
        
        lap2 = result.bundle.laps[1]
        assert lap2.lap_no == 2
        assert lap2.laptime_ms == 82123  # 1:22.123 in ms
        
        # Check sections for lap 1
        lap1_sections = [s for s in result.bundle.sections if s.lap_no == 1]
        assert len(lap1_sections) == 6
        
        # Check section names and timing
        section_names = [s.name for s in lap1_sections]
        assert section_names == ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]
        
        # IM1a: 0:12.345 = 12345ms
        im1a = next(s for s in lap1_sections if s.name == "IM1a")
        assert im1a.t_start_ms == 0
        assert im1a.t_end_ms == 12345
        
        # IM1: 0:25.678 = 25678ms, duration = 25678 - 12345 = 13333ms
        im1 = next(s for s in lap1_sections if s.name == "IM1")
        assert im1.t_start_ms == 12345
        assert im1.t_end_ms == 25678
        
        # FL: 1:23.456 = 83456ms
        fl = next(s for s in lap1_sections if s.name == "FL")
        assert fl.t_start_ms == 65567  # 1:05.567 = 65567ms
        assert fl.t_end_ms == 83456
    
    def test_header_variants(self):
        """Test importing with header variants."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1A_TIME;IM1;IM2a_sec;IM2;S3a;FINAL_LAP
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
        
        # Check section names resolved correctly
        section_names = [s.name for s in result.bundle.sections]
        assert section_names == ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]
    
    def test_comma_delimiter(self):
        """Test importing with comma delimiter."""
        csv_content = """LAP_NUMBER,DRIVER_NUMBER,LAP_TIME,IM1a,IM1,IM2a,IM2,IM3a,FL
1,1,1:23.456,0:12.345,0:25.678,0:38.901,0:52.234,1:05.567,1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        assert len(result.bundle.sections) == 6
    
    def test_im10_no_match(self):
        """Test that IM10 doesn't match IM1 pattern."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL;IM10
1;1;1:23.456;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456;0:15.000"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should still have 6 sections, IM10 should be ignored
        assert len(result.bundle.sections) == 6
        
        section_names = [s.name for s in result.bundle.sections]
        assert section_names == ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]
    
    def test_im10_explicit_negative_test(self):
        """Explicit negative test that IM10 does NOT match IM1 pattern using (?!\d)."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM10;IM1
1;1;1:23.456;0:15.000;0:25.678"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should only have 1 section (IM1), IM10 should be ignored
        assert len(result.bundle.sections) == 1
        
        section_names = [s.name for s in result.bundle.sections]
        assert section_names == ["IM1"]
        
        # Verify IM10 was not mapped to IM1 by checking the section times
        im1_section = result.bundle.sections[0]
        assert im1_section.name == "IM1"
        assert im1_section.t_end_ms == 25678  # Should be IM1 time, not IM10 time
    
    def test_missing_sections_warning(self):
        """Test warning for missing section headers."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a
1;1;1:23.456;0:12.345;0:25.678;0:38.901"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.sections) == 3  # Only IM1a, IM1, IM2a
        
        # Should have warning about missing sections
        missing_warnings = [w for w in result.warnings if "Missing section headers" in w]
        assert len(missing_warnings) == 1
        assert "IM2" in missing_warnings[0]
        assert "IM3a" in missing_warnings[0]
        assert "FL" in missing_warnings[0]
    
    def test_duplicate_headers_warning(self):
        """Test warning for duplicate headers matching same canonical."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1A;IM2a;IM2;IM3a;FL
1;1;1:23.456;0:12.345;0:13.000;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        
        # Should have warning about duplicate headers
        duplicate_warnings = [w for w in result.warnings if "Multiple headers match" in w and "IM1a" in w]
        assert len(duplicate_warnings) == 1
    
    def test_invalid_laptime(self):
        """Test handling of invalid laptime format."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;invalid;0:12.345;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        # Should have warning about invalid laptime
        print(f"DEBUG: result.warnings = {result.warnings}")
        laptime_warnings = [w for w in result.warnings if "Invalid LAP_TIME" in w]
        assert len(laptime_warnings) == 1
    
    def test_invalid_section_time(self):
        """Test handling of invalid section time format."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;1:23.456;invalid;0:25.678;0:38.901;0:52.234;1:05.567;1:23.456"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        # Should have 5 sections (IM1a skipped)
        assert len(result.bundle.sections) == 5
        
        # Should have warning about invalid section time
        section_warnings = [w for w in result.warnings if "Invalid IM1a time" in w]
        assert len(section_warnings) == 1
    
    def test_empty_csv(self):
        """Test handling of empty CSV."""
        csv_content = ""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert len(result.warnings) == 1
        assert "Empty CSV file" in result.warnings[0]
    
    def test_missing_required_columns(self):
        """Test handling of missing required columns."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER
1;1"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is None
        assert any("missing required columns: LAP_TIME" in w for w in result.warnings)
    
    def test_ss_mmm_format(self):
        """Test laptime in ss.mmm format."""
        csv_content = """LAP_NUMBER;DRIVER_NUMBER;LAP_TIME;IM1a;IM1;IM2a;IM2;IM3a;FL
1;1;59.123;12.345;25.678;38.901;52.234;65.567;59.123"""
        
        file_obj = io.StringIO(csv_content)
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, "test-session")
        
        assert result.bundle is not None
        assert len(result.bundle.laps) == 1
        
        lap = result.bundle.laps[0]
        assert lap.laptime_ms == 59123  # 59.123 in ms
        
        # Check section timing
        im1a = next(s for s in result.bundle.sections if s.name == "IM1a")
        assert im1a.t_end_ms == 12345  # 12.345 in ms