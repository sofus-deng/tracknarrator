# Multi-Driver Comparison Implementation Specification

## 1. Driver Comparison Analytics Module

### File: `backend/src/tracknarrator/driver_comparison.py`

```python
"""Multi-driver comparison analytics for TrackNarrator."""

from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import math
import statistics

from .schema import SessionBundle, Lap, Section, Telemetry
from .viz import _percentile, _robust_sigma


class DriverComparison:
    """Analytics for comparing multiple drivers in a session."""
    
    def __init__(self, bundle: SessionBundle):
        """Initialize with session bundle."""
        self.bundle = bundle
        self.drivers = self._extract_drivers()
        self.driver_laps = self._group_laps_by_driver()
        self.driver_sections = self._group_sections_by_driver()
    
    def _extract_drivers(self) -> List[str]:
        """Extract all unique drivers from the session."""
        return list({lap.driver for lap in self.bundle.laps if lap.driver})
    
    def _group_laps_by_driver(self) -> Dict[str, List[Lap]]:
        """Group laps by driver."""
        driver_laps = defaultdict(list)
        for lap in self.bundle.laps:
            if lap.driver and lap.laptime_ms > 0:
                driver_laps[lap.driver].append(lap)
        return dict(driver_laps)
    
    def _group_sections_by_driver(self) -> Dict[str, List[Section]]:
        """Group sections by driver using lap mapping."""
        # Create lap to driver mapping
        lap_driver_map = {lap.lap_no: lap.driver for lap in self.bundle.laps if lap.driver}
        
        driver_sections = defaultdict(list)
        for section in self.bundle.sections:
            driver = lap_driver_map.get(section.lap_no)
            if driver:
                driver_sections[driver].append(section)
        return dict(driver_sections)
    
    def compare_lap_times(self, drivers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compare lap times across drivers.
        
        Args:
            drivers: List of drivers to compare (None = all)
            
        Returns:
            Dictionary with lap time comparison data
        """
        if drivers is None:
            drivers = self.drivers
        
        comparison = {
            "by_driver": {},
            "summary": {},
            "head_to_head": {}
        }
        
        # Analyze each driver
        for driver in drivers:
            if driver not in self.driver_laps:
                continue
                
            laps = self.driver_laps[driver]
            lap_times = [lap.laptime_ms for lap in laps]
            
            if not lap_times:
                continue
            
            # Statistics
            best_lap = min(lap_times)
            avg_lap = sum(lap_times) / len(lap_times)
            median_lap = statistics.median(lap_times)
            consistency = 1.0 - (_robust_sigma(lap_times) / median_lap) if median_lap > 0 else 0
            
            # Lap by lap data
            lap_data = []
            for lap in sorted(laps, key=lambda l: l.lap_no):
                lap_data.append({
                    "lap_no": lap.lap_no,
                    "laptime_ms": lap.laptime_ms,
                    "position": lap.position
                })
            
            comparison["by_driver"][driver] = {
                "best_lap_ms": best_lap,
                "avg_lap_ms": avg_lap,
                "median_lap_ms": median_lap,
                "consistency_score": consistency,
                "lap_count": len(laps),
                "laps": lap_data
            }
        
        # Summary statistics
        if comparison["by_driver"]:
            all_best_laps = [data["best_lap_ms"] for data in comparison["by_driver"].values()]
            all_consistency = [data["consistency_score"] for data in comparison["by_driver"].values()]
            
            comparison["summary"] = {
                "fastest_driver": min(comparison["by_driver"].keys(), 
                                   key=lambda d: comparison["by_driver"][d]["best_lap_ms"]),
                "most_consistent": max(comparison["by_driver"].keys(), 
                                    key=lambda d: comparison["by_driver"][d]["consistency_score"]),
                "pace_spread_ms": max(all_best_laps) - min(all_best_laps),
                "avg_consistency": sum(all_consistency) / len(all_consistency)
            }
        
        # Head-to-head matrix
        comparison["head_to_head"] = self._create_head_to_head_matrix(drivers)
        
        return comparison
    
    def _create_head_to_head_matrix(self, drivers: List[str]) -> Dict[str, Any]:
        """Create head-to-head comparison matrix."""
        matrix = {}
        
        for driver1 in drivers:
            matrix[driver1] = {}
            for driver2 in drivers:
                if driver1 == driver2:
                    matrix[driver1][driver2] = {"advantage": 0.0, "status": "same"}
                    continue
                
                if (driver1 in self.driver_laps and driver2 in self.driver_laps):
                    laps1 = [l.laptime_ms for l in self.driver_laps[driver1]]
                    laps2 = [l.laptime_ms for l in self.driver_laps[driver2]]
                    
                    if laps1 and laps2:
                        avg1 = sum(laps1) / len(laps1)
                        avg2 = sum(laps2) / len(laps2)
                        advantage_ms = avg2 - avg1  # Positive = driver1 faster
                        
                        if abs(advantage_ms) < 100:  # Within 100ms
                            status = "even"
                        elif advantage_ms > 0:
                            status = "faster"
                        else:
                            status = "slower"
                        
                        matrix[driver1][driver2] = {
                            "advantage_ms": advantage_ms,
                            "status": status
                        }
        
        return matrix
    
    def analyze_section_performance(self, drivers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze section performance across drivers.
        
        Args:
            drivers: List of drivers to analyze (None = all)
            
        Returns:
            Dictionary with section performance data
        """
        if drivers is None:
            drivers = self.drivers
        
        analysis = {
            "by_section": {},
            "driver_strengths": {},
            "section_rankings": {}
        }
        
        # Group sections by name across all drivers
        all_sections = defaultdict(lambda: defaultdict(list))
        for driver in drivers:
            if driver not in self.driver_sections:
                continue
                
            for section in self.driver_sections[driver]:
                duration = section.t_end_ms - section.t_start_ms
                if duration > 0:
                    all_sections[section.name][driver].append(duration)
        
        # Analyze each section
        for section_name, driver_data in all_sections.items():
            section_analysis = {
                "by_driver": {},
                "summary": {}
            }
            
            for driver, durations in driver_data.items():
                if durations:
                    best = min(durations)
                    avg = sum(durations) / len(durations)
                    consistency = 1.0 - (_robust_sigma(durations) / avg) if avg > 0 else 0
                    
                    section_analysis["by_driver"][driver] = {
                        "best_ms": best,
                        "avg_ms": avg,
                        "consistency": consistency,
                        "sample_count": len(durations)
                    }
            
            # Section summary
            if section_analysis["by_driver"]:
                best_times = [(driver, data["best_ms"]) for driver, data in section_analysis["by_driver"].items()]
                fastest_driver, fastest_time = min(best_times, key=lambda x: x[1])
                
                section_analysis["summary"] = {
                    "fastest_driver": fastest_driver,
                    "fastest_time_ms": fastest_time,
                    "time_spread_ms": max(data["best_ms"] for data in section_analysis["by_driver"].values()) - fastest_time
                }
            
            analysis["by_section"][section_name] = section_analysis
        
        # Driver strengths by section
        for driver in drivers:
            strengths = []
            weaknesses = []
            
            for section_name, section_data in analysis["by_section"].items():
                if driver in section_data["by_driver"]:
                    driver_time = section_data["by_driver"][driver]["best_ms"]
                    fastest_time = section_data["summary"]["fastest_time_ms"]
                    
                    if abs(driver_time - fastest_time) < 50:  # Within 50ms of fastest
                        strengths.append(section_name)
                    elif driver_time - fastest_time > 200:  # More than 200ms slower
                        weaknesses.append(section_name)
            
            analysis["driver_strengths"][driver] = {
                "strengths": strengths,
                "weaknesses": weaknesses
            }
        
        return analysis
    
    def compare_telemetry_profiles(self, drivers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compare telemetry profiles across drivers.
        
        Args:
            drivers: List of drivers to compare (None = all)
            
        Returns:
            Dictionary with telemetry comparison data
        """
        if drivers is None:
            drivers = self.drivers
        
        comparison = {
            "speed_profiles": {},
            "braking_analysis": {},
            "driving_styles": {}
        }
        
        # Group telemetry by driver using lap mapping
        lap_driver_map = {lap.lap_no: lap.driver for lap in self.bundle.laps if lap.driver}
        driver_telemetry = defaultdict(list)
        
        for telemetry in self.bundle.telemetry:
            # Find driver for this telemetry point
            driver = None
            # This is simplified - in practice we'd need more sophisticated mapping
            # For now, we'll use a simple approach based on timing
            
        # For each driver, analyze their telemetry patterns
        for driver in drivers:
            if driver not in driver_telemetry:
                continue
            
            telemetry_points = driver_telemetry[driver]
            
            # Speed profile analysis
            speeds = [t.speed_kph for t in telemetry_points if t.speed_kph is not None]
            if speeds:
                speed_profile = {
                    "max_speed_kph": max(speeds),
                    "avg_speed_kph": sum(speeds) / len(speeds),
                    "speed_variance": statistics.variance(speeds) if len(speeds) > 1 else 0,
                    "time_at_high_speed": sum(1 for s in speeds if s > 150) / len(speeds)
                }
                comparison["speed_profiles"][driver] = speed_profile
            
            # Braking analysis
            brake_points = [t.brake_bar for t in telemetry_points if t.brake_bar is not None and t.brake_bar > 0]
            if brake_points:
                braking_analysis = {
                    "max_brake_bar": max(brake_points),
                    "avg_brake_bar": sum(brake_points) / len(brake_points),
                    "brake_events": len(brake_points),
                    "brake_aggressiveness": sum(brake_points) / len(telemetry_points)
                }
                comparison["braking_analysis"][driver] = braking_analysis
        
        return comparison
    
    def generate_team_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive team summary.
        
        Returns:
            Dictionary with team summary data
        """
        if not self.drivers:
            return {"error": "No drivers found in session"}
        
        lap_comparison = self.compare_lap_times()
        section_analysis = self.analyze_section_performance()
        
        summary = {
            "driver_count": len(self.drivers),
            "drivers": self.drivers,
            "best_lap": {},
            "most_consistent": {},
            "best_per_section": {},
            "team_metrics": {}
        }
        
        # Best lap overall
        if lap_comparison["by_driver"]:
            best_driver_data = min(lap_comparison["by_driver"].items(), 
                                key=lambda x: x[1]["best_lap_ms"])
            summary["best_lap"] = {
                "driver": best_driver_data[0],
                "laptime_ms": best_driver_data[1]["best_lap_ms"]
            }
        
        # Most consistent driver
        if lap_comparison["by_driver"]:
            consistent_driver_data = max(lap_comparison["by_driver"].items(), 
                                      key=lambda x: x[1]["consistency_score"])
            summary["most_consistent"] = {
                "driver": consistent_driver_data[0],
                "consistency_score": consistent_driver_data[1]["consistency_score"]
            }
        
        # Best per section
        for section_name, section_data in section_analysis["by_section"].items():
            if "summary" in section_data and "fastest_driver" in section_data["summary"]:
                summary["best_per_section"][section_name] = {
                    "driver": section_data["summary"]["fastest_driver"],
                    "time_ms": section_data["summary"]["fastest_time_ms"]
                }
        
        # Team metrics
        if lap_comparison["summary"]:
            summary["team_metrics"] = {
                "pace_spread_ms": lap_comparison["summary"]["pace_spread_ms"],
                "avg_consistency": lap_comparison["summary"]["avg_consistency"],
                "competitive_balance": 1.0 - (lap_comparison["summary"]["pace_spread_ms"] / 10000)  # Normalized
            }
        
        return summary
```

## 2. API Endpoint Extensions

### File: `backend/src/tracknarrator/api.py` (Additions)

```python
# Add these imports at the top
from .driver_comparison import DriverComparison

# Add these endpoints after the existing session endpoints

@app.get("/session/{session_id}/compare")
async def compare_drivers(
    session_id: str,
    drivers: str = Query(None, description="Comma-separated list of drivers to compare"),
    metrics: str = Query(None, description="Comma-separated list of metrics to include"),
    lang: str = Query("zh-Hant", description="Language for responses (zh-Hant or en)")
) -> Dict[str, Any]:
    """
    Compare multiple drivers in a session.
    
    Args:
        session_id: Session ID to compare
        drivers: Comma-separated list of drivers (None = all)
        metrics: Comma-separated list of metrics (None = all)
        lang: Language for responses
        
    Returns:
        Dictionary with driver comparison data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Parse drivers list
    driver_list = None
    if drivers:
        driver_list = [d.strip() for d in drivers.split(",") if d.strip()]
    
    # Initialize comparison
    comparison = DriverComparison(bundle)
    
    # Parse metrics list
    metrics_list = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",") if m.strip()]
    
    result = {
        "session_id": session_id,
        "drivers": comparison.drivers,
        "comparison": {}
    }
    
    # Include requested metrics
    if metrics_list is None or "lap_times" in metrics_list:
        result["comparison"]["lap_times"] = comparison.compare_lap_times(driver_list)
    
    if metrics_list is None or "section_analysis" in metrics_list:
        result["comparison"]["section_analysis"] = comparison.analyze_section_performance(driver_list)
    
    if metrics_list is None or "telemetry_comparison" in metrics_list:
        result["comparison"]["telemetry_comparison"] = comparison.compare_telemetry_profiles(driver_list)
    
    return result


@app.get("/session/{session_id}/team")
async def get_team_summary(
    session_id: str,
    lang: str = Query("zh-Hant", description="Language for responses (zh-Hant or en)")
) -> Dict[str, Any]:
    """
    Get team summary for a session.
    
    Args:
        session_id: Session ID to analyze
        lang: Language for responses
        
    Returns:
        Dictionary with team summary data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    comparison = DriverComparison(bundle)
    return {
        "session_id": session_id,
        "team_summary": comparison.generate_team_summary()
    }


@app.get("/session/{session_id}/ranking")
async def get_driver_rankings(
    session_id: str,
    metric: str = Query("laptime", description="Ranking metric (laptime, consistency, sections)"),
    lap_range: str = Query(None, description="Lap range (e.g., '1-5')"),
    lang: str = Query("zh-Hant", description="Language for responses (zh-Hant or en)")
) -> Dict[str, Any]:
    """
    Get driver rankings for a session.
    
    Args:
        session_id: Session ID to analyze
        metric: Ranking metric
        lap_range: Lap range to consider
        lang: Language for responses
        
    Returns:
        Dictionary with driver rankings
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    comparison = DriverComparison(bundle)
    
    # Parse lap range
    lap_start, lap_end = None, None
    if lap_range:
        try:
            parts = lap_range.split("-")
            if len(parts) == 2:
                lap_start = int(parts[0].strip())
                lap_end = int(parts[1].strip())
        except ValueError:
            pass  # Invalid range, ignore
    
    # Get rankings based on metric
    if metric == "laptime":
        lap_data = comparison.compare_lap_times()
        rankings = []
        
        for driver, data in lap_data["by_driver"].items():
            rankings.append({
                "rank": 0,  # Will be set after sorting
                "driver": driver,
                "value": data["best_lap_ms"],
                "details": {
                    "avg_lap_ms": data["avg_lap_ms"],
                    "consistency": data["consistency_score"],
                    "lap_count": data["lap_count"]
                }
            })
        
        # Sort and assign ranks
        rankings.sort(key=lambda x: x["value"])
        for i, ranking in enumerate(rankings):
            ranking["rank"] = i + 1
    
    elif metric == "consistency":
        lap_data = comparison.compare_lap_times()
        rankings = []
        
        for driver, data in lap_data["by_driver"].items():
            rankings.append({
                "rank": 0,
                "driver": driver,
                "value": data["consistency_score"],
                "details": {
                    "best_lap_ms": data["best_lap_ms"],
                    "avg_lap_ms": data["avg_lap_ms"],
                    "lap_count": data["lap_count"]
                }
            })
        
        rankings.sort(key=lambda x: x["value"], reverse=True)
        for i, ranking in enumerate(rankings):
            ranking["rank"] = i + 1
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    
    return {
        "session_id": session_id,
        "ranking_metric": metric,
        "rankings": rankings
    }


@app.get("/session/{session_id}/export/comparison")
async def export_comparison(
    session_id: str,
    drivers: str = Query(None, description="Comma-separated list of drivers to include"),
    format: str = Query("json", description="Export format (json, csv)"),
    lang: str = Query("zh-Hant", description="Language for narratives")
):
    """
    Export driver comparison data.
    
    Args:
        session_id: Session ID to export
        drivers: Comma-separated list of drivers (None = all)
        format: Export format
        lang: Language for narratives
        
    Returns:
        Export file with comparison data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Parse drivers list
    driver_list = None
    if drivers:
        driver_list = [d.strip() for d in drivers.split(",") if d.strip()]
    
    comparison = DriverComparison(bundle)
    
    # Get all comparison data
    comparison_data = {
        "session_id": session_id,
        "drivers": driver_list or comparison.drivers,
        "lap_times": comparison.compare_lap_times(driver_list),
        "section_analysis": comparison.analyze_section_performance(driver_list),
        "telemetry_comparison": comparison.compare_telemetry_profiles(driver_list),
        "team_summary": comparison.generate_team_summary()
    }
    
    if format.lower() == "json":
        # Return JSON file
        return Response(
            content=json.dumps(comparison_data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={session_id}_comparison.json"}
        )
    
    elif format.lower() == "csv":
        # Create CSV content
        import io
        import csv
        
        output = io.StringIO()
        
        # Lap times CSV
        if "lap_times" in comparison_data and "by_driver" in comparison_data["lap_times"]:
            writer = csv.writer(output)
            writer.writerow(["Driver", "Best Lap (ms)", "Avg Lap (ms)", "Consistency", "Lap Count"])
            
            for driver, data in comparison_data["lap_times"]["by_driver"].items():
                writer.writerow([
                    driver,
                    data["best_lap_ms"],
                    data["avg_lap_ms"],
                    data["consistency_score"],
                    data["lap_count"]
                ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={session_id}_comparison.csv"}
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
```

## 3. Visualization Components

### File: `docs/multi-driver-comparison.js` (New Frontend Component)

```javascript
/**
 * Multi-driver comparison visualization components for TrackNarrator
 */

class MultiDriverComparison {
    constructor(containerId, sessionId) {
        this.container = document.getElementById(containerId);
        this.sessionId = sessionId;
        this.drivers = [];
        this.comparisonData = null;
        this.selectedDrivers = new Set();
        this.selectedMetrics = new Set(['lap_times', 'section_analysis']);
    }

    async initialize() {
        await this.loadComparisonData();
        this.renderDriverSelector();
        this.renderMetricSelector();
        this.renderComparisonViews();
    }

    async loadComparisonData() {
        try {
            const response = await fetch(`/api/session/${this.sessionId}/compare`);
            this.comparisonData = await response.json();
            this.drivers = this.comparisonData.drivers;
            
            // Select all drivers by default
            this.drivers.forEach(driver => this.selectedDrivers.add(driver));
        } catch (error) {
            console.error('Failed to load comparison data:', error);
        }
    }

    renderDriverSelector() {
        const selectorContainer = document.createElement('div');
        selectorContainer.className = 'driver-selector';
        
        const title = document.createElement('h3');
        title.textContent = 'Select Drivers';
        selectorContainer.appendChild(title);
        
        const driverList = document.createElement('div');
        driverList.className = 'driver-list';
        
        this.drivers.forEach(driver => {
            const driverItem = document.createElement('div');
            driverItem.className = 'driver-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `driver-${driver}`;
            checkbox.checked = this.selectedDrivers.has(driver);
            checkbox.addEventListener('change', () => this.toggleDriver(driver));
            
            const label = document.createElement('label');
            label.htmlFor = `driver-${driver}`;
            label.textContent = driver;
            
            driverItem.appendChild(checkbox);
            driverItem.appendChild(label);
            driverList.appendChild(driverItem);
        });
        
        selectorContainer.appendChild(driverList);
        this.container.appendChild(selectorContainer);
    }

    renderMetricSelector() {
        const selectorContainer = document.createElement('div');
        selectorContainer.className = 'metric-selector';
        
        const title = document.createElement('h3');
        title.textContent = 'Select Metrics';
        selectorContainer.appendChild(title);
        
        const metrics = [
            { id: 'lap_times', name: 'Lap Times' },
            { id: 'section_analysis', name: 'Section Analysis' },
            { id: 'telemetry_comparison', name: 'Telemetry Profiles' }
        ];
        
        const metricList = document.createElement('div');
        metricList.className = 'metric-list';
        
        metrics.forEach(metric => {
            const metricItem = document.createElement('div');
            metricItem.className = 'metric-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `metric-${metric.id}`;
            checkbox.checked = this.selectedMetrics.has(metric.id);
            checkbox.addEventListener('change', () => this.toggleMetric(metric.id));
            
            const label = document.createElement('label');
            label.htmlFor = `metric-${metric.id}`;
            label.textContent = metric.name;
            
            metricItem.appendChild(checkbox);
            metricItem.appendChild(label);
            metricList.appendChild(metricItem);
        });
        
        selectorContainer.appendChild(metricList);
        this.container.appendChild(selectorContainer);
    }

    renderComparisonViews() {
        const viewsContainer = document.createElement('div');
        viewsContainer.className = 'comparison-views';
        
        // Lap Times Comparison
        if (this.selectedMetrics.has('lap_times')) {
            viewsContainer.appendChild(this.renderLapTimesComparison());
        }
        
        // Section Analysis
        if (this.selectedMetrics.has('section_analysis')) {
            viewsContainer.appendChild(this.renderSectionAnalysis());
        }
        
        // Telemetry Comparison
        if (this.selectedMetrics.has('telemetry_comparison')) {
            viewsContainer.appendChild(this.renderTelemetryComparison());
        }
        
        this.container.appendChild(viewsContainer);
    }

    renderLapTimesComparison() {
        const container = document.createElement('div');
        container.className = 'lap-times-comparison';
        
        const title = document.createElement('h3');
        title.textContent = 'Lap Times Comparison';
        container.appendChild(title);
        
        if (this.comparisonData.comparison.lap_times) {
            // Create chart container
            const chartContainer = document.createElement('div');
            chartContainer.id = 'lap-times-chart';
            chartContainer.style.height = '400px';
            container.appendChild(chartContainer);
            
            // Create summary table
            const summaryTable = this.createLapTimesSummary();
            container.appendChild(summaryTable);
            
            // Render chart
            this.renderLapTimesChart(chartContainer);
        }
        
        return container;
    }

    renderLapTimesChart(container) {
        const lapData = this.comparisonData.comparison.lap_times.by_driver;
        const selectedDrivers = Array.from(this.selectedDrivers);
        
        const traces = selectedDrivers.map(driver => {
            const driverData = lapData[driver];
            if (!driverData) return null;
            
            return {
                x: driverData.laps.map(lap => lap.lap_no),
                y: driverData.laps.map(lap => lap.laptime_ms),
                type: 'scatter',
                mode: 'lines+markers',
                name: driver,
                line: { shape: 'spline' }
            };
        }).filter(trace => trace !== null);
        
        const layout = {
            title: 'Lap Times by Driver',
            xaxis: { title: 'Lap Number' },
            yaxis: { title: 'Lap Time (ms)' },
            hovermode: 'closest'
        };
        
        Plotly.newPlot(container, traces, layout);
    }

    createLapTimesSummary() {
        const table = document.createElement('table');
        table.className = 'comparison-table';
        
        const header = document.createElement('thead');
        header.innerHTML = `
            <tr>
                <th>Driver</th>
                <th>Best Lap</th>
                <th>Avg Lap</th>
                <th>Consistency</th>
                <th>Lap Count</th>
            </tr>
        `;
        table.appendChild(header);
        
        const tbody = document.createElement('tbody');
        const lapData = this.comparisonData.comparison.lap_times.by_driver;
        
        Array.from(this.selectedDrivers).forEach(driver => {
            const data = lapData[driver];
            if (!data) return;
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${driver}</td>
                <td>${data.best_lap_ms}ms</td>
                <td>${Math.round(data.avg_lap_ms)}ms</td>
                <td>${(data.consistency_score * 100).toFixed(1)}%</td>
                <td>${data.lap_count}</td>
            `;
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        return table;
    }

    renderSectionAnalysis() {
        const container = document.createElement('div');
        container.className = 'section-analysis';
        
        const title = document.createElement('h3');
        title.textContent = 'Section Performance Analysis';
        container.appendChild(title);
        
        if (this.comparisonData.comparison.section_analysis) {
            // Section radar chart
            const radarContainer = document.createElement('div');
            radarContainer.id = 'section-radar-chart';
            radarContainer.style.height = '400px';
            container.appendChild(radarContainer);
            
            // Driver strengths table
            const strengthsTable = this.createDriverStrengthsTable();
            container.appendChild(strengthsTable);
            
            // Render radar chart
            this.renderSectionRadarChart(radarContainer);
        }
        
        return container;
    }

    renderSectionRadarChart(container) {
        const sectionData = this.comparisonData.comparison.section_analysis.by_section;
        const selectedDrivers = Array.from(this.selectedDrivers);
        
        const sections = Object.keys(sectionData);
        const traces = selectedDrivers.map(driver => {
            const values = sections.map(section => {
                const sectionInfo = sectionData[section].by_driver[driver];
                return sectionInfo ? sectionInfo.best_ms : null;
            });
            
            return {
                r: values,
                theta: sections,
                type: 'scatterpolar',
                fill: 'toself',
                name: driver
            };
        });
        
        const layout = {
            title: 'Section Performance Comparison',
            polar: {
                radialaxis: {
                    visible: true,
                    range: [0, Math.max(...traces.flatMap(t => t.r))]
                }
            }
        };
        
        Plotly.newPlot(container, traces, layout);
    }

    createDriverStrengthsTable() {
        const table = document.createElement('table');
        table.className = 'comparison-table';
        
        const header = document.createElement('thead');
        header.innerHTML = `
            <tr>
                <th>Driver</th>
                <th>Strengths</th>
                <th>Weaknesses</th>
            </tr>
        `;
        table.appendChild(header);
        
        const tbody = document.createElement('tbody');
        const strengthsData = this.comparisonData.comparison.section_analysis.driver_strengths;
        
        Array.from(this.selectedDrivers).forEach(driver => {
            const data = strengthsData[driver];
            if (!data) return;
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${driver}</td>
                <td>${data.strengths.join(', ')}</td>
                <td>${data.weaknesses.join(', ')}</td>
            `;
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        return table;
    }

    toggleDriver(driver) {
        if (this.selectedDrivers.has(driver)) {
            this.selectedDrivers.delete(driver);
        } else {
            this.selectedDrivers.add(driver);
        }
        this.refreshComparison();
    }

    toggleMetric(metric) {
        if (this.selectedMetrics.has(metric)) {
            this.selectedMetrics.delete(metric);
        } else {
            this.selectedMetrics.add(metric);
        }
        this.refreshComparison();
    }

    refreshComparison() {
        // Clear existing comparison views
        const viewsContainer = this.container.querySelector('.comparison-views');
        if (viewsContainer) {
            viewsContainer.remove();
        }
        
        // Re-render comparison views
        this.renderComparisonViews();
    }
}

// Initialize multi-driver comparison when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const comparisonContainer = document.getElementById('multi-driver-comparison');
    if (comparisonContainer) {
        const sessionId = comparisonContainer.dataset.sessionId;
        const comparison = new MultiDriverComparison('multi-driver-comparison', sessionId);
        comparison.initialize();
    }
});
```

## 4. CSS Styles

### File: `docs/multi-driver-comparison.css` (New Stylesheet)

```css
/* Multi-driver comparison styles */

.driver-selector, .metric-selector {
    margin-bottom: 20px;
    padding: 15px;
    border: 1px solid #ddd;
    border-radius: 5px;
}

.driver-list, .metric-list {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
}

.driver-item, .metric-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.driver-item input[type="checkbox"],
.metric-item input[type="checkbox"] {
    margin: 0;
}

.comparison-views {
    display: grid;
    gap: 30px;
}

.lap-times-comparison, .section-analysis {
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 20px;
}

.comparison-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

.comparison-table th,
.comparison-table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.comparison-table th {
    background-color: #f5f5f5;
    font-weight: bold;
}

.comparison-table tr:hover {
    background-color: #f9f9f9;
}

/* Chart containers */
#lap-times-chart, #section-radar-chart {
    margin: 20px 0;
}

/* Responsive design */
@media (max-width: 768px) {
    .driver-list, .metric-list {
        flex-direction: column;
        gap: 10px;
    }
    
    .comparison-views {
        grid-template-columns: 1fr;
    }
    
    .comparison-table {
        font-size: 14px;
    }
    
    .comparison-table th,
    .comparison-table td {
        padding: 8px;
    }
}
```

## 5. HTML Template

### File: `docs/multi-driver-comparison.html` (New Page)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Driver Comparison - TrackNarrator</title>
    <link rel="stylesheet" href="styles.css">
    <link rel="stylesheet" href="multi-driver-comparison.css">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <header>
        <h1>TrackNarrator - Multi-Driver Comparison</h1>
        <nav>
            <a href="index.html">Home</a>
            <a href="multi-driver-comparison.html" class="active">Driver Comparison</a>
        </nav>
    </header>
    
    <main>
        <div class="session-info">
            <h2>Session: <span id="session-title">Loading...</span></h2>
            <p>Compare performance across multiple drivers in this session</p>
        </div>
        
        <div id="multi-driver-comparison" data-session-id="">
            <!-- Multi-driver comparison will be rendered here -->
        </div>
    </main>
    
    <footer>
        <p>&copy; 2025 TrackNarrator - Multi-Driver Analysis</p>
    </footer>
    
    <script src="multi-driver-comparison.js"></script>
    <script>
        // Get session ID from URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session') || 'barber-demo-r1';
        
        // Set session ID and title
        document.getElementById('multi-driver-comparison').dataset.sessionId = sessionId;
        document.getElementById('session-title').textContent = sessionId;
    </script>
</body>
</html>
```

## 6. Test Cases

### File: `backend/tests/test_driver_comparison.py` (New Test File)

```python
"""Tests for multi-driver comparison functionality."""

import pytest
from tracknarrator.driver_comparison import DriverComparison
from tracknarrator.schema import SessionBundle, Session, Lap, Section, Telemetry


@pytest.fixture
def multi_driver_bundle():
    """Create a test bundle with multiple drivers."""
    session = Session(
        id="test-session",
        source="test",
        track="Test Track",
        track_id="test-track",
        schema_version="0.1.2"
    )
    
    # Create laps for 3 drivers
    laps = [
        # Driver A
        Lap(session_id="test-session", lap_no=1, driver="Driver A", laptime_ms=95000),
        Lap(session_id="test-session", lap_no=2, driver="Driver A", laptime_ms=96000),
        Lap(session_id="test-session", lap_no=3, driver="Driver A", laptime_ms=94500),
        
        # Driver B
        Lap(session_id="test-session", lap_no=1, driver="Driver B", laptime_ms=97000),
        Lap(session_id="test-session", lap_no=2, driver="Driver B", laptime_ms=96500),
        Lap(session_id="test-session", lap_no=3, driver="Driver B", laptime_ms=97500),
        
        # Driver C
        Lap(session_id="test-session", lap_no=1, driver="Driver C", laptime_ms=98000),
        Lap(session_id="test-session", lap_no=2, driver="Driver C", laptime_ms=99000),
        Lap(session_id="test-session", lap_no=3, driver="Driver C", laptime_ms=98500),
    ]
    
    # Create sections
    sections = []
    for lap_no in range(1, 4):
        for driver in ["Driver A", "Driver B", "Driver C"]:
            sections.extend([
                Section(
                    session_id="test-session",
                    lap_no=lap_no,
                    driver=driver,
                    name="IM1a",
                    t_start_ms=0,
                    t_end_ms=15000
                ),
                Section(
                    session_id="test-session",
                    lap_no=lap_no,
                    driver=driver,
                    name="IM1",
                    t_start_ms=15000,
                    t_end_ms=30000
                )
            ])
    
    return SessionBundle(session=session, laps=laps, sections=sections, telemetry=[], weather=[])


def test_driver_comparison_initialization(multi_driver_bundle):
    """Test DriverComparison initialization."""
    comparison = DriverComparison(multi_driver_bundle)
    
    assert len(comparison.drivers) == 3
    assert "Driver A" in comparison.drivers
    assert "Driver B" in comparison.drivers
    assert "Driver C" in comparison.drivers
    
    assert len(comparison.driver_laps) == 3
    assert len(comparison.driver_laps["Driver A"]) == 3


def test_compare_lap_times(multi_driver_bundle):
    """Test lap time comparison."""
    comparison = DriverComparison(multi_driver_bundle)
    result = comparison.compare_lap_times()
    
    assert "by_driver" in result
    assert "summary" in result
    assert "head_to_head" in result
    
    # Check driver-specific data
    driver_a_data = result["by_driver"]["Driver A"]
    assert driver_a_data["best_lap_ms"] == 94500
    assert driver_a_data["avg_lap_ms"] == pytest.approx(95167, rel=1e-2)
    assert driver_a_data["lap_count"] == 3
    
    # Check summary
    assert result["summary"]["fastest_driver"] == "Driver A"
    assert result["summary"]["most_consistent"] == "Driver A"  # Most consistent lap times


def test_analyze_section_performance(multi_driver_bundle):
    """Test section performance analysis."""
    comparison = DriverComparison(multi_driver_bundle)
    result = comparison.analyze_section_performance()
    
    assert "by_section" in result
    assert "driver_strengths" in result
    
    # Check section analysis
    im1a_data = result["by_section"]["IM1a"]
    assert "by_driver" in im1a_data
    assert "summary" in im1a_data
    
    # Check driver strengths
    assert "Driver A" in result["driver_strengths"]
    assert "strengths" in result["driver_strengths"]["Driver A"]
    assert "weaknesses" in result["driver_strengths"]["Driver A"]


def test_generate_team_summary(multi_driver_bundle):
    """Test team summary generation."""
    comparison = DriverComparison(multi_driver_bundle)
    result = comparison.generate_team_summary()
    
    assert result["driver_count"] == 3
    assert result["best_lap"]["driver"] == "Driver A"
    assert result["best_lap"]["laptime_ms"] == 94500
    assert "team_metrics" in result
    assert "pace_spread_ms" in result["team_metrics"]


def test_head_to_head_matrix(multi_driver_bundle):
    """Test head-to-head comparison matrix."""
    comparison = DriverComparison(multi_driver_bundle)
    result = comparison.compare_lap_times()
    
    matrix = result["head_to_head"]
    
    # Check matrix structure
    assert "Driver A" in matrix
    assert "Driver B" in matrix["Driver A"]
    assert "Driver C" in matrix["Driver A"]
    
    # Check self-comparison
    assert matrix["Driver A"]["Driver A"]["status"] == "same"
    assert matrix["Driver A"]["Driver A"]["advantage_ms"] == 0.0
    
    # Check cross-comparison
    assert matrix["Driver A"]["Driver B"]["status"] == "faster"
    assert matrix["Driver A"]["Driver B"]["advantage_ms"] > 0
```

This implementation specification provides a comprehensive foundation for multi-driver comparison features in TrackNarrator. The code is modular, follows existing patterns, and provides both backend analytics and frontend visualization capabilities.