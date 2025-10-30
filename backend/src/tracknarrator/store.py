"""In-memory session store with deterministic merge strategy."""

import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from .schema import Lap, Section, Session, SessionBundle, Telemetry, WeatherPoint


class SessionStore:
    """In-memory store for session data with merge capabilities."""
    
    def __init__(self):
        """Initialize the session store."""
        self.sessions: Dict[str, SessionBundle] = {}
        
        # Source precedence for conflict resolution
        self.source_precedence = {
            "laps": ["mylaps_sections_csv", "trd_csv", "racechrono_csv", "gpx", "weather_csv"],
            "sections": ["mylaps_sections_csv", "trd_csv", "racechrono_csv", "gpx", "weather_csv"],
            "telemetry": ["trd_long_csv", "racechrono_csv", "gpx", "mylaps_sections_csv", "weather_csv"],
            "weather": ["weather_csv", "trd_long_csv", "racechrono_csv", "gpx", "mylaps_sections_csv"]
        }
        
        # Numeric tolerances for conflict detection
        self.tolerances = {
            "speed_kph": 0.5,
            "throttle_pct": 0.5,
            "brake_bar": 0.5,
            "steer_deg": 0.5,
            "acc_long_g": 0.05,
            "acc_lat_g": 0.05,
            "lat_deg": 1e-6,
            "lon_deg": 1e-6,
        }
    
    def merge_bundle(self, session_id: str, partial_bundle: SessionBundle, src: str) -> Tuple[Dict[str, int], List[str]]:
        """
        Merge a partial bundle into the store.
        
        Args:
            session_id: Session ID to merge into
            partial_bundle: Partial bundle with new data
            src: Source identifier for precedence
            
        Returns:
            tuple: (counts, warnings)
            counts contains added/updated counts per data type
        """
        counts = defaultdict(int)
        warnings = []
        
        # Get or create session bundle
        if session_id not in self.sessions:
            # New session - use provided session info but update source
            session = partial_bundle.session.model_copy(update={"id": session_id})
            self.sessions[session_id] = SessionBundle(
                session=session,
                laps=[],
                sections=[],
                telemetry=[],
                weather=[]
            )
            counts["sessions_added"] = 1
        else:
            counts["sessions_updated"] = 1
        
        existing_bundle = self.sessions[session_id]
        
        # Merge laps
        lap_counts, lap_warnings = self._merge_laps(existing_bundle, partial_bundle.laps, src)
        counts.update(lap_counts)
        warnings.extend(lap_warnings)
        
        # Merge sections
        section_counts, section_warnings = self._merge_sections(existing_bundle, partial_bundle.sections, src)
        counts.update(section_counts)
        warnings.extend(section_warnings)
        
        # Merge telemetry
        telemetry_counts, telemetry_warnings = self._merge_telemetry(existing_bundle, partial_bundle.telemetry, src)
        counts.update(telemetry_counts)
        warnings.extend(telemetry_warnings)
        
        # Merge weather
        weather_counts, weather_warnings = self._merge_weather(existing_bundle, partial_bundle.weather, src)
        counts.update(weather_counts)
        warnings.extend(weather_warnings)
        
        return dict(counts), warnings
    
    def _merge_laps(self, existing_bundle: SessionBundle, new_laps: List[Lap], src: str) -> Tuple[Dict[str, int], List[str]]:
        """Merge laps with conflict resolution."""
        counts = {"laps_added": 0, "laps_updated": 0}
        warnings = []
        
        # Create index for existing laps
        laps_index = {(lap.lap_no, lap.driver): lap for lap in existing_bundle.laps}
        
        for new_lap in new_laps:
            key = (new_lap.lap_no, new_lap.driver)
            
            # Add provenance metadata
            self._add_provenance(new_lap, src)
            
            if key not in laps_index:
                # New lap - add it
                existing_bundle.laps.append(new_lap)
                laps_index[key] = new_lap
                counts["laps_added"] += 1
            else:
                # Existing lap - merge with conflict resolution
                existing_lap = laps_index[key]
                precedence_list = self.source_precedence["laps"]
                
                if self._has_higher_precedence(src, existing_lap, precedence_list):
                    # Higher precedence source - replace
                    self._merge_lap_fields(existing_lap, new_lap)
                    counts["laps_updated"] += 1
                elif self._has_higher_precedence(self._get_source(existing_lap), new_lap, precedence_list):
                    # Existing has higher precedence - keep existing
                    warnings.append(
                        f"Lap {new_lap.lap_no} driver {new_lap.driver}: "
                        f"keeping data from higher precedence source {self._get_source(existing_lap)}"
                    )
                else:
                    # Same precedence - merge field by field
                    self._merge_lap_fields(existing_lap, new_lap)
                    counts["laps_updated"] += 1
        
        return counts, warnings
    
    def _merge_sections(self, existing_bundle: SessionBundle, new_sections: List[Section], src: str) -> Tuple[Dict[str, int], List[str]]:
        """Merge sections with conflict resolution."""
        counts = {"sections_added": 0, "sections_updated": 0}
        warnings = []
        
        # Create index for existing sections with tolerance
        sections_index = {}
        for section in existing_bundle.sections:
            key = (section.lap_no, section.name, round(section.t_start_ms))
            sections_index[key] = section
        
        for new_section in new_sections:
            # Add provenance metadata
            self._add_provenance(new_section, src)
            
            # Find matching section with tolerance
            matching_key = None
            for key, existing_section in sections_index.items():
                if (key[0] == new_section.lap_no and 
                    key[1] == new_section.name and
                    abs(key[2] - new_section.t_start_ms) <= 10):
                    matching_key = key
                    break
            
            if matching_key is None:
                # New section - add it
                key = (new_section.lap_no, new_section.name, round(new_section.t_start_ms))
                existing_bundle.sections.append(new_section)
                sections_index[key] = new_section
                counts["sections_added"] += 1
            else:
                # Existing section - merge
                existing_section = sections_index[matching_key]
                precedence_list = self.source_precedence["sections"]
                
                # Prefer meta.source == "map" over "fallback"
                if (new_section.meta.get("source") == "map" and 
                    existing_section.meta.get("source") != "map"):
                    self._merge_section_fields(existing_section, new_section)
                    counts["sections_updated"] += 1
                elif self._has_higher_precedence(src, existing_section, precedence_list):
                    self._merge_section_fields(existing_section, new_section)
                    counts["sections_updated"] += 1
                else:
                    warnings.append(
                        f"Section {new_section.name} lap {new_section.lap_no}: "
                        f"keeping data from higher precedence source {self._get_source(existing_section)}"
                    )
        
        return counts, warnings
    
    def _merge_telemetry(self, existing_bundle: SessionBundle, new_telemetry: List[Telemetry], src: str) -> Tuple[Dict[str, int], List[str]]:
        """Merge telemetry with conflict resolution using ±1ms buckets."""
        counts = {"telemetry_added": 0, "telemetry_updated": 0}
        warnings = []
        
        # Create index for existing telemetry with ±1ms buckets
        telemetry_buckets = self._create_telemetry_buckets(existing_bundle.telemetry)
        
        for new_telemetry in new_telemetry:
            # Add provenance metadata
            self._add_provenance(new_telemetry, src)
            
            # Find matching telemetry bucket within ±1ms
            matching_bucket_ts = None
            for bucket_ts in telemetry_buckets:
                if abs(bucket_ts - new_telemetry.ts_ms) <= 1:
                    matching_bucket_ts = bucket_ts
                    break
            
            if matching_bucket_ts is None:
                # New telemetry - add it
                existing_bundle.telemetry.append(new_telemetry)
                telemetry_buckets[new_telemetry.ts_ms] = [new_telemetry]
                counts["telemetry_added"] += 1
            else:
                # Existing telemetry bucket - merge with best match
                existing_telemetry_list = telemetry_buckets[matching_bucket_ts]
                best_existing = self._find_best_telemetry_match(existing_telemetry_list, new_telemetry)
                
                precedence_list = self.source_precedence["telemetry"]
                
                if self._has_higher_precedence(src, best_existing, precedence_list):
                    # Higher precedence - replace existing
                    existing_bundle.telemetry.remove(best_existing)
                    existing_telemetry_list.remove(best_existing)
                    existing_bundle.telemetry.append(new_telemetry)
                    existing_telemetry_list.append(new_telemetry)
                    counts["telemetry_updated"] += 1
                else:
                    # Check for conflicts and warn
                    conflicts = self._detect_telemetry_conflicts(best_existing, new_telemetry)
                    if conflicts:
                        warnings.append(
                            f"Telemetry at {new_telemetry.ts_ms}ms: "
                            f"conflicts in {', '.join(conflicts)} - keeping {self._get_source(best_existing)}"
                        )
        
        return counts, warnings
    
    def _merge_weather(self, existing_bundle: SessionBundle, new_weather: List[WeatherPoint], src: str) -> Tuple[Dict[str, int], List[str]]:
        """Merge weather with conflict resolution."""
        counts = {"weather_added": 0, "weather_updated": 0}
        warnings = []
        
        # Create index for existing weather
        weather_index = {weather.ts_ms: weather for weather in existing_bundle.weather}
        
        for new_weather_point in new_weather:
            # Add provenance metadata
            self._add_provenance(new_weather_point, src)
            
            if new_weather_point.ts_ms not in weather_index:
                # New weather point - add it
                existing_bundle.weather.append(new_weather_point)
                weather_index[new_weather_point.ts_ms] = new_weather_point
                counts["weather_added"] += 1
            else:
                # Existing weather point - merge
                existing_weather = weather_index[new_weather_point.ts_ms]
                precedence_list = self.source_precedence["weather"]
                
                if self._has_higher_precedence(src, existing_weather, precedence_list):
                    self._merge_weather_fields(existing_weather, new_weather_point)
                    counts["weather_updated"] += 1
                else:
                    warnings.append(
                        f"Weather at {new_weather_point.ts_ms}ms: "
                        f"keeping data from higher precedence source {self._get_source(existing_weather)}"
                    )
        
        return counts, warnings
    
    def _add_provenance(self, obj, src: str):
        """Add provenance metadata to an object."""
        obj.__src = src
        obj.__ingested_at = int(time.time() * 1000)
    
    def _get_source(self, obj) -> str:
        """Get source from provenance metadata."""
        return getattr(obj, '__src', 'unknown')
    
    def _has_higher_precedence(self, src: str, obj, precedence_list: List[str]) -> bool:
        """Check if source has higher precedence than object's source."""
        obj_src = self._get_source(obj)
        try:
            return precedence_list.index(src) < precedence_list.index(obj_src)
        except ValueError:
            return True  # Unknown sources get lower precedence
    
    def _merge_lap_fields(self, existing: Lap, new: Lap):
        """Merge lap fields with non-None wins logic."""
        if new.start_ts and not existing.start_ts:
            existing.start_ts = new.start_ts
        if new.end_ts and not existing.end_ts:
            existing.end_ts = new.end_ts
        if new.position is not None and existing.position is None:
            existing.position = new.position
        if new.laptime_ms:  # Always take new laptime if provided
            existing.laptime_ms = new.laptime_ms
    
    def _merge_section_fields(self, existing: Section, new: Section):
        """Merge section fields with source preference."""
        if new.meta.get("source") == "map":
            existing.t_start_ms = new.t_start_ms
            existing.t_end_ms = new.t_end_ms
        if new.delta_ms is not None:
            existing.delta_ms = new.delta_ms
        if new.meta:
            existing.meta.update(new.meta)
    
    def _merge_telemetry_fields(self, existing: Telemetry, new: Telemetry):
        """Merge telemetry fields with non-None wins logic."""
        fields = ['speed_kph', 'throttle_pct', 'brake_bar', 'gear', 
                 'acc_long_g', 'acc_lat_g', 'steer_deg', 'lat_deg', 'lon_deg']
        
        for field in fields:
            new_value = getattr(new, field)
            existing_value = getattr(existing, field)
            if new_value is not None and existing_value is None:
                setattr(existing, field, new_value)
    
    def _merge_weather_fields(self, existing: WeatherPoint, new: WeatherPoint):
        """Merge weather fields with non-None wins logic."""
        fields = ['air_temp_c', 'track_temp_c', 'humidity_pct', 'pressure_hpa',
                 'wind_speed', 'wind_dir_deg', 'rain_flag']
        
        for field in fields:
            new_value = getattr(new, field)
            existing_value = getattr(existing, field)
            if new_value is not None and existing_value is None:
                setattr(existing, field, new_value)
    
    def _detect_telemetry_conflicts(self, existing: Telemetry, new: Telemetry) -> List[str]:
        """Detect conflicts between telemetry points beyond tolerance."""
        conflicts = []
        
        for field, tolerance in self.tolerances.items():
            existing_value = getattr(existing, field)
            new_value = getattr(new, field)
            
            if (existing_value is not None and new_value is not None and
                abs(existing_value - new_value) > tolerance):
                conflicts.append(field)
        
        return conflicts
    
    def _create_telemetry_buckets(self, telemetry_list: List[Telemetry]) -> Dict[int, List[Telemetry]]:
        """
        Create buckets for telemetry timestamps within ±1ms range.
        
        Args:
            telemetry_list: List of existing telemetry points
            
        Returns:
            Dictionary mapping bucket_timestamp -> list of telemetry points
        """
        if not telemetry_list:
            return {}
        
        buckets = {}
        
        # Sort telemetry by timestamp
        sorted_telemetry = sorted(telemetry_list, key=lambda t: t.ts_ms)
        
        for telemetry in sorted_telemetry:
            ts_ms = telemetry.ts_ms
            
            # Find existing bucket within ±1ms
            bucket_found = False
            for bucket_ts in buckets:
                if abs(bucket_ts - ts_ms) <= 1:
                    buckets[bucket_ts].append(telemetry)
                    bucket_found = True
                    break
            
            if not bucket_found:
                # Create new bucket
                buckets[ts_ms] = [telemetry]
        
        return buckets
    
    def _find_best_telemetry_match(self, telemetry_list: List[Telemetry], new_telemetry: Telemetry) -> Telemetry:
        """
        Find the best matching telemetry from a list.
        
        Args:
            telemetry_list: List of existing telemetry points in same bucket
            new_telemetry: New telemetry point to match
            
        Returns:
            Best matching telemetry point
        """
        if len(telemetry_list) == 1:
            return telemetry_list[0]
        
        # Find telemetry with most non-None fields and closest timestamp
        best_match = telemetry_list[0]
        best_score = -1
        
        for telemetry in telemetry_list:
            # Count non-None fields (excluding session_id and ts_ms)
            non_none_count = sum(1 for k, v in telemetry.model_dump().items()
                               if k not in ['session_id', 'ts_ms'] and v is not None)
            
            # Calculate score: prioritize non-None fields, then timestamp proximity
            timestamp_diff = abs(telemetry.ts_ms - new_telemetry.ts_ms)
            score = non_none_count * 1000 - timestamp_diff
            
            if score > best_score:
                best_score = score
                best_match = telemetry
        
        return best_match
    
    def get_bundle(self, session_id: str) -> Optional[SessionBundle]:
        """Get session bundle by ID."""
        return self.sessions.get(session_id)
    
    def make_session(self, session_id: str, track: str = "Barber Motorsports Park", 
                    track_id: str = "barber-motorsports-park", 
                    track_map_version: str = "pdf:Barber_Circuit_Map",
                    source: str = "mylaps_csv") -> Session:
        """Create a new session with default values."""
        return Session(
            id=session_id,
            source=source,
            track=track,
            track_id=track_id,
            track_map_version=track_map_version
        )


# Global store instance
store = SessionStore()