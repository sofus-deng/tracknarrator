"""MYLAPS sections CSV importer with regex-based header resolver."""

import csv
import io
import re
from typing import BinaryIO, Dict, List, TextIO, Tuple

from .base import ImportResult, coerce_float, coerce_int, clean_string
from ..schema import Lap, Section, Session, SessionBundle
from ..utils_time import parse_laptime_to_ms


class MYLAPSSectionsCSVImporter:
    """Importer for MYLAPS analysis-with-sections CSV files."""
    
    # Canonical section names and their regex patterns
    SECTION_PATTERNS = {
        "IM1a": [
            r"\bIM\s*1A\b",
            r"\bIM1A(_TIME|_ELAPSED|_SEC|_S|_MS)?\b",
            r"\bS1\.?a\b", 
            r"\bS1A\b"
        ],
        "IM1": [
            r"\bIM\s*1\b(?!\d)",  # boundary to avoid IM10
            r"\bIM1(_TIME|_ELAPSED|_SEC|_S|_MS)?\b",
            r"\bS1\b"
        ],
        "IM2a": [
            r"\bIM\s*2A\b",
            r"\bIM2A(_TIME|_ELAPSED|_SEC|_S|_MS)?\b",
            r"\bS2\.?a\b", 
            r"\bS2A\b"
        ],
        "IM2": [
            r"\bIM\s*2\b(?!\d)",
            r"\bIM2(_TIME|_ELAPSED|_SEC|_S|_MS)?\b",
            r"\bS2\b"
        ],
        "IM3a": [
            r"\bIM\s*3A\b",
            r"\bIM3A(_TIME|_ELAPSED|_SEC|_S|_MS)?\b",
            r"\bS3\.?a\b", 
            r"\bS3A\b"
        ],
        "FL": [
            r"\bFL\b",
            r"\bFINISH(_TIME|_ELAPSED|_SEC|_S|_MS)?\b",
            r"\bFINAL\s*LAP(_TIME|_ELAPSED|_SEC)?\b",
            r"\bFINAL_LAP\b"
        ]
    }
    
    # Required canonical section order
    SECTION_ORDER = ["IM1a", "IM1", "IM2a", "IM2", "IM3a", "FL"]
    
    @classmethod
    def import_file(cls, file: BinaryIO | TextIO, session_id: str) -> ImportResult:
        """
        Import MYLAPS sections CSV file.
        
        Args:
            file: File-like object containing CSV data
            session_id: Session ID for the data
            
        Returns:
            ImportResult with laps and sections data and any warnings
        """
        warnings = []
        
        try:
            # Handle both binary and text files with encoding fallback
            content, encoding_used = cls._read_file_with_encoding_fallback(file)
            if content is None:
                return ImportResult.failure(["Failed to read file with any supported encoding"])
            
            # Auto-detect delimiter
            delimiter = cls._detect_delimiter(content)
            
            # Read CSV data
            text_io = io.StringIO(content)
            reader = csv.DictReader(text_io, delimiter=delimiter)
            rows = list(reader)
            
            if not rows:
                return ImportResult.failure(["Empty CSV file"])
            
            # Resolve headers to canonical section names
            header_mapping, header_warnings = cls._resolve_headers(reader.fieldnames or [])
            warnings.extend(header_warnings)
            
            if not header_mapping:
                return ImportResult.failure(["No valid section headers found"])
            
            # Process rows to create laps and sections
            laps = []
            sections = []
            
            for row_num, row in enumerate(rows, 1):
                try:
                    # Extract lap number
                    lap_no_raw = cls._get_lap_number(row)
                    if lap_no_raw is None:
                        warnings.append(f"Row {row_num}: Missing LAP_NUMBER")
                        continue
                    
                    lap_no = coerce_int(lap_no_raw)
                    if lap_no is None:
                        warnings.append(f"Row {row_num}: Invalid LAP_NUMBER '{lap_no_raw}'")
                        continue
                    
                    # Extract driver number
                    driver_no_raw = row.get('DRIVER_NUMBER', '')
                    driver_no = coerce_int(driver_no_raw)
                    if driver_no is None:
                        warnings.append(f"Row {row_num}: Invalid DRIVER_NUMBER '{driver_no_raw}'")
                        continue
                    
                    driver = f"No.{driver_no}"
                    
                    # Extract lap time
                    laptime_raw = row.get('LAP_TIME', '')
                    if not laptime_raw:
                        warnings.append(f"Row {row_num}: Missing LAP_TIME")
                        continue
                    
                    try:
                        laptime_ms = parse_laptime_to_ms(laptime_raw)
                    except ValueError as e:
                        warning_msg = f"Invalid LAP_TIME '{laptime_raw}': {e}"
                        warnings.append(warning_msg)
                        continue
                    
                    # Create lap
                    lap = Lap(
                        session_id=session_id,
                        lap_no=lap_no,
                        driver=driver,
                        laptime_ms=laptime_ms
                    )
                    laps.append(lap)
                    
                    # Process sections
                    lap_sections, section_warnings = cls._process_sections(
                        row, session_id, lap_no, header_mapping
                    )
                    warnings.extend(section_warnings)
                    sections.extend(lap_sections)
                    
                except Exception as e:
                    warnings.append(f"Row {row_num}: Error processing row: {e}")
                    continue
            
            if not laps:
                failure_warnings = ["No valid laps found"] + warnings
                return ImportResult.failure(failure_warnings)
            
            # Create session and bundle
            session = Session(
                id=session_id,
                source="mylaps_csv",
                track_id="unknown",  # Will be updated by other importers
            )
            
            bundle = SessionBundle(
                session=session,
                laps=laps,
                sections=sections
            )
            
            return ImportResult.success(bundle, warnings)
            
        except Exception as e:
            return ImportResult.failure([f"Error processing MYLAPS sections CSV: {str(e)}"])
    
    @classmethod
    def _resolve_headers(cls, fieldnames: List[str]) -> tuple[Dict[str, str], List[str]]:
        """
        Resolve CSV headers to canonical section names using regex patterns.
        
        Returns:
            tuple: (header_mapping, warnings)
            header_mapping maps original_header -> canonical_name
        """
        warnings = []
        header_mapping = {}
        used_headers = {}
        
        # Compile regex patterns
        compiled_patterns = {}
        for canonical, patterns in cls.SECTION_PATTERNS.items():
            compiled_patterns[canonical] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        # Match headers to patterns
        for header in fieldnames:
            header_clean = header.strip().strip('"\'')
            
            for canonical, patterns in compiled_patterns.items():
                for pattern in patterns:
                    if pattern.fullmatch(header_clean):
                        # Check for duplicate canonical matches
                        if canonical in used_headers:
                            warnings.append(
                                f"Multiple headers match '{canonical}': "
                                f"'{used_headers[canonical]}' and '{header}'. Using first."
                            )
                        else:
                            header_mapping[header] = canonical
                            used_headers[canonical] = header
                        break
                    elif pattern.search(header_clean):
                        # Partial match - warn but still use it
                        if canonical not in used_headers:
                            header_mapping[header] = canonical
                            used_headers[canonical] = header
                        break
        
        # Check for missing canonical sections
        missing_sections = [
            canonical for canonical in cls.SECTION_ORDER 
            if canonical not in used_headers
        ]
        
        if missing_sections:
            warnings.append(f"Missing section headers: {', '.join(missing_sections)}")
        
        return header_mapping, warnings
    
    @classmethod
    def _get_lap_number(cls, row: Dict[str, str]) -> str:
        """Extract lap number from row with various possible header names."""
        for header in ['LAP_NUMBER', 'LAP', 'LAPNO']:
            if header in row and row[header].strip():
                return row[header].strip()
        return ''
    
    @classmethod
    def _process_sections(cls, row: Dict[str, str], session_id: str, lap_no: int,
                         header_mapping: Dict[str, str]) -> tuple[List[Section], List[str]]:
        """Process sections for a single lap."""
        warnings = []
        sections = []
        previous_time_ms = 0
        
        # Process sections in canonical order
        for section_name in cls.SECTION_ORDER:
            # Find the header that maps to this section
            header = None
            for h, canonical in header_mapping.items():
                if canonical == section_name:
                    header = h
                    break
            
            if header is None:
                warnings.append(f"Lap {lap_no}: Missing {section_name} data")
                continue
            
            # Get section time (absolute time from lap start)
            section_time_raw = row.get(header, '').strip()
            if not section_time_raw:
                warnings.append(f"Lap {lap_no}: Empty {section_name} time")
                continue
            
            try:
                section_time_ms = parse_laptime_to_ms(section_time_raw)
            except ValueError as e:
                warnings.append(f"Lap {lap_no}: Invalid {section_name} time '{section_time_raw}': {e}")
                continue
            
            # Create section (using absolute times, not cumulative)
            t_start_ms = previous_time_ms
            t_end_ms = section_time_ms
            
            section = Section(
                session_id=session_id,
                lap_no=lap_no,
                name=section_name,
                t_start_ms=t_start_ms,
                t_end_ms=t_end_ms,
                meta={"source": "mylaps"}
            )
            sections.append(section)
            
            previous_time_ms = t_end_ms
        
        return sections, warnings
    
    @classmethod
    def _read_file_with_encoding_fallback(cls, file: BinaryIO | TextIO) -> Tuple[str, str]:
        """
        Read file with encoding fallback: utf-8 -> utf-8-sig -> latin1.
        
        Returns:
            tuple: (content, encoding_used) or (None, None) if all fail
        """
        encodings = ['utf-8', 'utf-8-sig', 'latin1']
        
        # Handle binary file
        if hasattr(file, 'read'):
            content = file.read()
            if isinstance(content, bytes):
                for encoding in encodings:
                    try:
                        decoded = content.decode(encoding)
                        # Remove BOM if present
                        if decoded.startswith('\ufeff'):
                            decoded = decoded[1:]
                        return decoded, encoding
                    except UnicodeDecodeError:
                        continue
                return None, None
            else:
                # Already text, remove BOM if present
                text = content
                if text.startswith('\ufeff'):
                    text = text[1:]
                return text, 'utf-8'
        else:
            # Already text, remove BOM if present
            text = str(file)
            if text.startswith('\ufeff'):
                text = text[1:]
            return text, 'utf-8'
    
    @classmethod
    def _detect_delimiter(cls, content: str) -> str:
        """
        Auto-detect CSV delimiter based on first line.
        
        Returns:
            ';' if more semicolons than commas, otherwise ','
        """
        first_line = content.split('\n')[0] if '\n' in content else content
        semicolon_count = first_line.count(';')
        comma_count = first_line.count(',')
        
        return ';' if semicolon_count > comma_count else ','