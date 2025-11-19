# Multi-Driver Comparison Design for TrackNarrator

## Overview
This document outlines the design for implementing multi-driver comparison features in TrackNarrator, enabling team analysis and driver performance comparisons.

## Current State Analysis

### Existing Multi-Driver Support
- **Schema**: `Lap` model already includes `driver` field
- **Event Detection**: Already groups events by driver
- **Limitations**: Visualizations, coach scoring, and narratives are single-driver focused

### Data Structure
```python
# Current Lap model supports multiple drivers
Lap(
  session_id: str,
  lap_no: int,
  driver: str,        # Driver identifier (e.g., "No.1", "Driver A")
  laptime_ms: int,
  start_ts: Optional[datetime],
  end_ts: Optional[datetime],
  position: Optional[int]
)
```

## Multi-Driver Comparison Features

### 1. API Endpoints

#### 1.1 Driver Comparison Endpoint
```
GET /session/{session_id}/compare
```
**Parameters:**
- `drivers`: List of driver identifiers to compare (optional, defaults to all)
- `metrics`: List of metrics to include (optional, defaults to all)
- `lang`: Language for responses (zh-Hant/en)

**Response:**
```json
{
  "session_id": "barber-demo-r1",
  "drivers": ["No.1", "No.2", "No.3"],
  "comparison": {
    "lap_times": {
      "summary": {...},
      "by_driver": {...},
      "head_to_head": {...}
    },
    "section_analysis": {
      "by_section": {...},
      "driver_strengths": {...}
    },
    "telemetry_comparison": {
      "speed_profiles": {...},
      "braking_points": {...},
      "driving_styles": {...}
    },
    "events_comparison": {
      "by_driver": {...},
      "shared_events": {...}
    }
  }
}
```

#### 1.2 Team Summary Endpoint
```
GET /session/{session_id}/team
```
**Response:**
```json
{
  "session_id": "barber-demo-r1",
  "team_summary": {
    "driver_count": 3,
    "best_lap": {"driver": "No.1", "laptime_ms": 95000},
    "most_consistent": {"driver": "No.2", "consistency_score": 0.85},
    "best_per_section": {
      "IM1a": {"driver": "No.1", "time_ms": 15000},
      "IM1": {"driver": "No.3", "time_ms": 20000}
    },
    "team_metrics": {...}
  }
}
```

#### 1.3 Driver Ranking Endpoint
```
GET /session/{session_id}/ranking
```
**Parameters:**
- `metric`: Ranking metric (laptime, consistency, sections)
- `lap_range`: Lap range to consider (optional)

**Response:**
```json
{
  "session_id": "barber-demo-r1",
  "ranking_metric": "laptime",
  "rankings": [
    {"rank": 1, "driver": "No.1", "value": 95000, "details": {...}},
    {"rank": 2, "driver": "No.2", "value": 96000, "details": {...}},
    {"rank": 3, "driver": "No.3", "value": 97000, "details": {...}}
  ]
}
```

### 2. Analytics Module

#### 2.1 Driver Comparison Analytics
```python
class DriverComparison:
    def compare_lap_times(self, bundle: SessionBundle, drivers: List[str]) -> Dict
    def analyze_section_performance(self, bundle: SessionBundle, drivers: List[str]) -> Dict
    def compare_telemetry_profiles(self, bundle: SessionBundle, drivers: List[str]) -> Dict
    def detect_driver_strengths(self, bundle: SessionBundle, drivers: List[str]) -> Dict
    def generate_team_summary(self, bundle: SessionBundle) -> Dict
```

#### 2.2 Comparison Metrics
- **Lap Time Analysis**: Best lap, average lap, consistency, improvement trend
- **Section Performance**: Per-section strengths, time gains/losses
- **Telemetry Profiles**: Speed traces, braking points, steering patterns
- **Driving Style**: Aggressiveness, smoothness, efficiency
- **Event Comparison**: Types of events per driver, shared challenges

### 3. Visualization Components

#### 3.1 Comparison Charts
- **Lap Time Comparison**: Overlapping lap time charts with statistical bands
- **Section Radar Charts**: Multi-dimensional section performance comparison
- **Telemetry Overlays**: Speed/brake/steering traces for multiple drivers
- **Head-to-Head Matrix**: Direct driver comparison grid
- **Team Performance Heatmap**: Performance across different metrics

#### 3.2 Interactive Features
- Driver selection/deselection
- Metric filtering
- Lap range selection
- Detailed drill-downs

### 4. Multi-Driver Narrative Generation

#### 4.1 Comparison Narratives
```python
def build_comparison_narrative(
    bundle: SessionBundle, 
    drivers: List[str], 
    comparison_data: Dict,
    lang: str = "zh-Hant"
) -> List[str]
```

#### 4.2 Narrative Types
- **Team Summary**: Overall team performance overview
- **Driver Spotlight**: Individual driver highlights
- **Head-to-Head**: Direct driver comparisons
- **Section Analysis**: Track section performance insights
- **Coaching Recommendations**: Team-specific improvement areas

### 5. Frontend Integration

#### 5.1 Comparison Dashboard
- Multi-driver session viewer
- Interactive comparison tools
- Team performance overview
- Export capabilities

#### 5.2 UI Components
- Driver selector component
- Comparison metric selector
- Chart components for multi-driver data
- Narrative display for team insights

### 6. Export Functionality

#### 6.1 Comparison Export
```
GET /session/{session_id}/export/comparison
```
**Parameters:**
- `drivers`: Drivers to include
- `format`: Export format (json, csv, pdf)
- `lang`: Language for narratives

**Response:**
- ZIP file with comparison data, charts, and narratives

#### 6.2 Export Contents
- Comparison data (JSON)
- Charts (PNG/SVG)
- Narratives (TXT/MD)
- Summary tables (CSV)

## Implementation Plan

### Phase 1: Core Analytics
1. Implement `DriverComparison` class
2. Add comparison API endpoints
3. Create basic visualization data structures

### Phase 2: Visualization
1. Extend frontend chart components
2. Implement comparison dashboard
3. Add interactive features

### Phase 3: Narratives & Export
1. Multi-driver narrative generation
2. Export functionality
3. Documentation updates

### Phase 4: Advanced Features
1. Trend analysis across sessions
2. Historical comparisons
3. Predictive insights

## Schema Extensions

### New Models
```python
class DriverComparison(TypedDict):
    driver: str
    metrics: Dict[str, float]
    strengths: List[str]
    improvements: List[str]

class TeamSummary(TypedDict):
    driver_count: int
    best_lap: Dict[str, Any]
    most_consistent: Dict[str, Any]
    best_per_section: Dict[str, Dict[str, Any]]
    team_metrics: Dict[str, float]
```

## Testing Strategy

### Unit Tests
- Driver comparison analytics
- API endpoint responses
- Data structure validation

### Integration Tests
- Multi-driver session processing
- End-to-end comparison flows
- Export functionality

### Performance Tests
- Large multi-driver sessions
- Complex comparison queries
- Visualization rendering

## Backward Compatibility

- Existing single-driver endpoints remain unchanged
- New multi-driver features are additive
- Current visualizations continue to work
- Gradual migration path for users