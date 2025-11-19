# Multi-Driver Comparison Usage Guide

## Overview
This guide provides comprehensive examples and instructions for using TrackNarrator's multi-driver comparison features to analyze team performance and generate coaching insights.

## Getting Started

### 1. Accessing Multi-Driver Features

#### Web Interface
```
https://your-domain.com/team-dashboard.html?session=your-session-id
```

#### API Access
```
Base URL: https://your-domain.com/api
Authentication: Cookie-based or API key (if configured)
```

### 2. Prerequisites

- Session must contain data from multiple drivers
- Drivers should be properly identified in the `driver` field of lap data
- Minimum 2 drivers required for meaningful comparisons
- Recommended 3+ drivers for comprehensive team analysis

## API Usage Examples

### 1. Basic Driver Comparison

#### Compare All Drivers
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/compare" \
  -H "Accept: application/json"
```

**Response:**
```json
{
  "session_id": "barber-demo-r1",
  "drivers": ["Driver A", "Driver B", "Driver C"],
  "comparison": {
    "lap_times": {
      "by_driver": {
        "Driver A": {
          "best_lap_ms": 94500,
          "avg_lap_ms": 95167,
          "consistency_score": 0.78,
          "lap_count": 3
        }
      },
      "summary": {
        "fastest_driver": "Driver A",
        "most_consistent": "Driver A",
        "pace_spread_ms": 3500
      }
    },
    "section_analysis": {
      "by_section": {
        "IM1a": {
          "by_driver": {
            "Driver A": {
              "best_ms": 14500,
              "avg_ms": 14833,
              "consistency": 0.82
            }
          },
          "summary": {
            "fastest_driver": "Driver A",
            "fastest_time_ms": 14500
          }
        }
      },
      "driver_strengths": {
        "Driver A": {
          "strengths": ["IM1a", "IM2a"],
          "weaknesses": ["IM1", "IM2"]
        }
      }
    }
  }
}
```

#### Compare Specific Drivers
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/compare?drivers=Driver%20A,Driver%20B" \
  -H "Accept: application/json"
```

#### Filter Metrics
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/compare?metrics=lap_times,section_analysis" \
  -H "Accept: application/json"
```

### 2. Team Summary

#### Get Team Overview
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/team" \
  -H "Accept: application/json"
```

**Response:**
```json
{
  "session_id": "barber-demo-r1",
  "team_summary": {
    "driver_count": 3,
    "best_lap": {
      "driver": "Driver A",
      "laptime_ms": 94500
    },
    "most_consistent": {
      "driver": "Driver A",
      "consistency_score": 0.78
    },
    "best_per_section": {
      "IM1a": {
        "driver": "Driver A",
        "time_ms": 14500
      },
      "IM1": {
        "driver": "Driver B",
        "time_ms": 15500
      }
    },
    "team_metrics": {
      "pace_spread_ms": 3500,
      "avg_consistency": 0.72,
      "competitive_balance": 0.65
    }
  }
}
```

### 3. Driver Rankings

#### Rank by Lap Time
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/ranking?metric=laptime" \
  -H "Accept: application/json"
```

#### Rank by Consistency
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/ranking?metric=consistency" \
  -H "Accept: application/json"
```

#### Rank with Lap Range
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/ranking?metric=laptime&lap_range=1-5" \
  -H "Accept: application/json"
```

### 4. Narrative Generation

#### Team Summary Narrative (English)
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/compare/narrative?narrative_type=team&lang=en" \
  -H "Accept: application/json"
```

**Response:**
```json
{
  "session_id": "barber-demo-r1",
  "narrative_type": "team",
  "lines": [
    "Team analysis shows Driver A leading the pace with a best lap of 94.5s, while Driver B demonstrates the most consistency at 85%.",
    "The team shows a competitive spread of 3.5s across all drivers, indicating balanced performance levels.",
    "Driver A excels in 2 sections, showing particular strength in high-speed track areas."
  ],
  "lang": "en",
  "generated_at": 1703020800000
}
```

#### Head-to-Head Comparison (Chinese)
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/compare/narrative?narrative_type=head_to_head&driver1=Driver%20A&driver2=Driver%20B&lang=zh-Hant" \
  -H "Accept: application/json"
```

#### Driver Spotlight
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/compare/narrative?narrative_type=spotlight&spotlight_driver=Driver%20A&lang=en" \
  -H "Accept: application/json"
```

### 5. Export Functionality

#### Export JSON Comparison
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/export/comparison?format=json&drivers=Driver%20A,Driver%20B" \
  -H "Accept: application/json" \
  -o "team_comparison.json"
```

#### Export CSV Comparison
```bash
curl -X GET "https://your-domain.com/api/session/barber-demo-r1/export/comparison?format=csv" \
  -H "Accept: text/csv" \
  -o "team_comparison.csv"
```

## Web Dashboard Usage

### 1. Accessing the Dashboard

Navigate to the team dashboard URL:
```
https://your-domain.com/team-dashboard.html?session=your-session-id
```

### 2. Driver Selection

#### Select All Drivers
1. In the Control Panel, locate "Driver Selection"
2. Check "Select All Drivers" to include everyone
3. Or individually check specific drivers

#### Head-to-Head Mode
1. Select "Head-to-Head" comparison mode
2. Choose two drivers from the dropdown menus
3. View automatically updates to show direct comparison

### 3. Metric Selection

#### Available Metrics
- **Lap Times**: Best lap, average lap, consistency analysis
- **Section Analysis**: Per-section performance, strengths/weaknesses
- **Telemetry Profiles**: Speed traces, braking patterns, driving styles
- **Event Analysis**: Detected events, mistake patterns

#### Customizing Views
1. Check/uncheck metrics in "Metrics & Analysis" section
2. View automatically updates to show selected data
3. Combine multiple metrics for comprehensive analysis

### 4. View Modes

#### Overview Tab
- Team summary cards
- Performance rankings
- Key insights
- Quick statistics

#### Lap Times Tab
- Interactive lap time chart
- Statistical bands
- Trend analysis
- Comparison table

#### Section Analysis Tab
- Radar chart for section performance
- Driver strengths matrix
- Section-by-section breakdown

#### Telemetry Tab
- Speed profile overlays
- Braking point analysis
- Steering pattern comparison
- Driving style classification

#### Events Tab
- Timeline of detected events
- Event distribution by driver
- Severity analysis
- Pattern recognition

#### Rankings Tab
- Customizable ranking metrics
- Visual ranking displays
- Historical trends
- Performance gaps

### 5. Narrative Panel

#### Team Summary
- Overall team performance overview
- Key strengths and weaknesses
- Competitive balance analysis
- Coaching recommendations

#### Driver Spotlight
- Individual driver analysis
- Performance breakdown
- Improvement suggestions
- Comparison to team average

#### Coaching Tips
- Specific actionable recommendations
- Technical focus areas
- Training suggestions
- Strategic insights

### 6. Language Support

#### Switching Languages
1. Use language selector in header
2. Choose between:
   - 中文 (繁體) - Traditional Chinese
   - English - English
3. All content updates immediately
4. Narratives regenerate in selected language

### 7. Export Options

#### Quick Export
1. Click "Export" button in header
2. Choose format (JSON/CSV)
3. Select drivers to include
4. Download automatically starts

#### Custom Export
1. Configure driver selection
2. Choose specific metrics
3. Set lap range if needed
4. Export tailored to your analysis

## Advanced Usage

### 1. Session Preparation

#### Multi-Driver Data Requirements
```python
# Example: Creating multi-driver session
from tracknarrator.schema import SessionBundle, Session, Lap

# Create laps for multiple drivers
laps = [
    # Driver A
    Lap(session_id="team-session", lap_no=1, driver="Driver A", laptime_ms=95000),
    Lap(session_id="team-session", lap_no=2, driver="Driver A", laptime_ms=94500),
    
    # Driver B
    Lap(session_id="team-session", lap_no=1, driver="Driver B", laptime_ms=97000),
    Lap(session_id="team-session", lap_no=2, driver="Driver B", laptime_ms=96500),
    
    # Driver C
    Lap(session_id="team-session", lap_no=1, driver="Driver C", laptime_ms=98000),
    Lap(session_id="team-session", lap_no=2, driver="Driver C", laptime_ms=97500)
]

# Create session bundle
session = Session(
    id="team-session",
    source="team_analysis",
    track="Team Track",
    track_id="team-track"
)

bundle = SessionBundle(session=session, laps=laps)
```

### 2. Custom Analysis

#### Driver Comparison Analytics
```python
from tracknarrator.driver_comparison import DriverComparison

# Initialize comparison
comparison = DriverComparison(bundle)

# Compare specific drivers
result = comparison.compare_lap_times(["Driver A", "Driver B"])

# Analyze sections
sections = comparison.analyze_section_performance(["Driver A", "Driver B"])

# Generate team summary
summary = comparison.generate_team_summary()
```

#### Custom Narratives
```python
from tracknarrator.multi_driver_narrative import MultiDriverNarrative

# Initialize narrative generator
narrative = MultiDriverNarrative(bundle)

# Generate team narrative
team_narrative = narrative.generate_team_narrative("en")

# Generate head-to-head comparison
head_to_head = narrative.generate_head_to_head_narrative(
    "Driver A", "Driver B", "en"
)

# Generate driver spotlight
spotlight = narrative.generate_driver_spotlight_narrative("Driver A", "en")
```

### 3. Integration Examples

#### Python Client Integration
```python
import requests
import json

class TrackNarratorClient:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def compare_drivers(self, session_id, drivers=None, metrics=None):
        """Compare drivers in a session."""
        params = {}
        if drivers:
            params['drivers'] = ','.join(drivers)
        if metrics:
            params['metrics'] = ','.join(metrics)
        
        response = self.session.get(
            f"{self.base_url}/session/{session_id}/compare",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_team_summary(self, session_id):
        """Get team summary for a session."""
        response = self.session.get(
            f"{self.base_url}/session/{session_id}/team"
        )
        response.raise_for_status()
        return response.json()
    
    def get_narrative(self, session_id, narrative_type, lang='en', **kwargs):
        """Get narrative for a session."""
        params = {'narrative_type': narrative_type, 'lang': lang}
        params.update(kwargs)
        
        response = self.session.get(
            f"{self.base_url}/session/{session_id}/compare/narrative",
            params=params
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = TrackNarratorClient('https://your-domain.com/api')

# Compare specific drivers
comparison = client.compare_drivers(
    'barber-demo-r1',
    drivers=['Driver A', 'Driver B'],
    metrics=['lap_times', 'section_analysis']
)

# Get team summary
summary = client.get_team_summary('barber-demo-r1')

# Get narratives in Chinese
narrative = client.get_narrative(
    'barber-demo-r1',
    'team',
    lang='zh-Hant'
)
```

#### JavaScript Integration
```javascript
class MultiDriverAnalysis {
    constructor(apiBaseUrl, sessionId) {
        this.apiBaseUrl = apiBaseUrl;
        this.sessionId = sessionId;
    }
    
    async compareDrivers(drivers = null, metrics = null) {
        const params = new URLSearchParams();
        if (drivers) {
            params.append('drivers', drivers.join(','));
        }
        if (metrics) {
            params.append('metrics', metrics.join(','));
        }
        
        const response = await fetch(
            `${this.apiBaseUrl}/session/${this.sessionId}/compare?${params}`
        );
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async getTeamSummary() {
        const response = await fetch(
            `${this.apiBaseUrl}/session/${this.sessionId}/team`
        );
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async getNarrative(type, options = {}) {
        const params = new URLSearchParams({
            narrative_type: type,
            lang: options.lang || 'en',
            ...options
        });
        
        const response = await fetch(
            `${this.apiBaseUrl}/session/${this.sessionId}/compare/narrative?${params}`
        );
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
}

// Usage example
const analysis = new MultiDriverAnalysis('/api', 'barber-demo-r1');

// Get comparison data
const comparison = await analysis.compareDrivers(
    ['Driver A', 'Driver B'],
    ['lap_times', 'section_analysis']
);

// Get team summary
const summary = await analysis.getTeamSummary();

// Get narratives
const narrative = await analysis.getNarrative('team', { lang: 'zh-Hant' });
```

## Troubleshooting

### Common Issues

#### 1. No Multi-Driver Data
**Problem**: Comparison endpoints return empty results
**Solution**: 
- Verify session contains multiple drivers
- Check driver field is populated in lap data
- Ensure lap times are valid (> 0)

#### 2. Performance Issues
**Problem**: Slow response times for large sessions
**Solution**:
- Use driver filtering to reduce data size
- Limit metrics to essential ones
- Consider lap range filtering

#### 3. Narrative Not Generated
**Problem**: Narrative endpoints return empty arrays
**Solution**:
- Check session has sufficient data (3+ laps per driver)
- Verify language parameter is valid
- Ensure narrative_type is correct

#### 4. Export Failures
**Problem**: Download doesn't start or is incomplete
**Solution**:
- Check browser popup blockers
- Verify sufficient disk space
- Try smaller data selection

### Debug Mode

#### Enable Debug Logging
```bash
# Set debug environment variable
export TN_DEBUG=true

# Run with verbose logging
python -m tracknarrator.api --log-level DEBUG
```

#### API Testing
```bash
# Test connection
curl -I https://your-domain.com/api/health

# Test session exists
curl https://your-domain.com/api/session/your-session/bundle

# Test specific endpoint
curl -v https://your-domain.com/api/session/your-session/compare
```

## Best Practices

### 1. Data Preparation
- Ensure consistent driver naming across laps
- Validate lap times are reasonable
- Include sufficient laps per driver (3+ recommended)
- Add section data for detailed analysis

### 2. Analysis Workflow
1. Start with team summary for overview
2. Use head-to-head for specific comparisons
3. Dive into section analysis for detailed insights
4. Review telemetry for technical analysis
5. Generate narratives for coaching recommendations

### 3. Performance Optimization
- Filter drivers to essential comparisons
- Use specific metrics when possible
- Limit lap ranges for focused analysis
- Cache results for repeated analysis

### 4. Integration Tips
- Use client libraries for consistent API access
- Implement error handling for network issues
- Cache session metadata locally
- Batch API calls when possible

## Support

### Documentation
- [API Reference](./API-REFERENCE.md)
- [Schema Specification](./SPEC-schema-v0.1.2.md)
- [Implementation Guide](./MULTI-DRIVER-IMPLEMENTATION-SPEC.md)

### Contact
- Technical support: support@tracknarrator.com
- Documentation issues: docs@tracknarrator.com
- Feature requests: features@tracknarrator.com

This comprehensive usage guide enables teams to effectively leverage TrackNarrator's multi-driver comparison features for performance analysis and coaching.