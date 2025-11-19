# Team Comparison Dashboard Design

## Overview
This document outlines the design for a comprehensive team comparison dashboard that integrates multi-driver analysis, visualizations, and narratives in TrackNarrator.

## Dashboard Layout

### Main Components

#### 1. Header Section
- Session information and context
- Language selector
- Export options
- Help/documentation links

#### 2. Control Panel
- Driver selection interface
- Metric selection controls
- Analysis options
- View preferences

#### 3. Main Visualization Area
- Tabbed interface for different analysis views
- Responsive grid layout
- Interactive charts and tables

#### 4. Narrative Panel
- Team summary insights
- Driver spotlights
- Coaching recommendations
- Multi-language support

#### 5. Export & Sharing
- Comparison export options
- Share functionality
- Report generation

## Detailed Component Design

### Header Section

```html
<header class="dashboard-header">
    <div class="session-info">
        <h1>Team Comparison Dashboard</h1>
        <div class="session-details">
            <span class="session-id">Session: <strong id="session-id">Loading...</strong></span>
            <span class="track-name">Track: <strong id="track-name">Loading...</strong></span>
            <span class="driver-count">Drivers: <strong id="driver-count">Loading...</strong></span>
        </div>
    </div>
    
    <div class="header-controls">
        <select id="language-selector" class="control-select">
            <option value="zh-Hant">中文 (繁體)</option>
            <option value="en">English</option>
        </select>
        
        <button id="export-btn" class="btn btn-primary">
            <i class="icon-download"></i> Export
        </button>
        
        <button id="help-btn" class="btn btn-secondary">
            <i class="icon-help"></i> Help
        </button>
    </div>
</header>
```

### Control Panel

```html
<div class="control-panel">
    <div class="control-section">
        <h3>Driver Selection</h3>
        <div class="driver-controls">
            <div class="driver-selection">
                <label class="checkbox-label">
                    <input type="checkbox" id="select-all-drivers" checked>
                    <span>Select All Drivers</span>
                </label>
                <div id="driver-checkboxes" class="driver-list">
                    <!-- Dynamically populated -->
                </div>
            </div>
            
            <div class="comparison-mode">
                <label class="radio-label">
                    <input type="radio" name="comparison-mode" value="all" checked>
                    <span>All Drivers Comparison</span>
                </label>
                <label class="radio-label">
                    <input type="radio" name="comparison-mode" value="head_to_head">
                    <span>Head-to-Head</span>
                </label>
                <div id="head-to-head-selectors" class="head-to-head-controls" style="display: none;">
                    <select id="driver1-select" class="control-select">
                        <option value="">Select Driver 1</option>
                    </select>
                    <select id="driver2-select" class="control-select">
                        <option value="">Select Driver 2</option>
                    </select>
                </div>
            </div>
        </div>
    </div>
    
    <div class="control-section">
        <h3>Metrics & Analysis</h3>
        <div class="metric-controls">
            <div class="metric-group">
                <h4>Performance Metrics</h4>
                <label class="checkbox-label">
                    <input type="checkbox" name="metric" value="lap_times" checked>
                    <span>Lap Times</span>
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" name="metric" value="section_analysis" checked>
                    <span>Section Analysis</span>
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" name="metric" value="telemetry_comparison" checked>
                    <span>Telemetry Profiles</span>
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" name="metric" value="events_comparison" checked>
                    <span>Event Analysis</span>
                </label>
            </div>
            
            <div class="metric-group">
                <h4>Analysis Options</h4>
                <label class="checkbox-label">
                    <input type="checkbox" id="show-statistical-bands" checked>
                    <span>Show Statistical Bands</span>
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" id="show-trend-lines" checked>
                    <span>Show Trend Lines</span>
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" id="enable-animations" checked>
                    <span>Enable Animations</span>
                </label>
            </div>
        </div>
    </div>
    
    <div class="control-section">
        <h3>View Options</h3>
        <div class="view-controls">
            <div class="lap-range-selector">
                <label>Lap Range:</label>
                <input type="number" id="lap-start" min="1" value="1" class="control-input">
                <span>to</span>
                <input type="number" id="lap-end" min="1" value="999" class="control-input">
                <button id="apply-lap-range" class="btn btn-small">Apply</button>
            </div>
            
            <div class="baseline-selector">
                <label>Baseline:</label>
                <select id="baseline-driver" class="control-select">
                    <option value="fastest">Fastest Driver</option>
                    <option value="most_consistent">Most Consistent</option>
                    <option value="team_average">Team Average</option>
                </select>
            </div>
        </div>
    </div>
</div>
```

### Main Visualization Area

```html
<div class="visualization-area">
    <div class="view-tabs">
        <button class="tab-btn active" data-view="overview">Overview</button>
        <button class="tab-btn" data-view="lap-times">Lap Times</button>
        <button class="tab-btn" data-view="sections">Section Analysis</button>
        <button class="tab-btn" data-view="telemetry">Telemetry</button>
        <button class="tab-btn" data-view="events">Events</button>
        <button class="tab-btn" data-view="rankings">Rankings</button>
    </div>
    
    <div class="view-content">
        <!-- Overview View -->
        <div id="overview-view" class="view-panel active">
            <div class="overview-grid">
                <div class="overview-card">
                    <h3>Team Summary</h3>
                    <div id="team-summary-content">
                        <!-- Team summary metrics -->
                    </div>
                </div>
                
                <div class="overview-card">
                    <h3>Performance Rankings</h3>
                    <div id="rankings-content">
                        <!-- Driver rankings -->
                    </div>
                </div>
                
                <div class="overview-card">
                    <h3>Key Insights</h3>
                    <div id="insights-content">
                        <!-- Narrative insights -->
                    </div>
                </div>
                
                <div class="overview-card">
                    <h3>Quick Stats</h3>
                    <div id="quick-stats-content">
                        <!-- Statistical summary -->
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Lap Times View -->
        <div id="lap-times-view" class="view-panel">
            <div class="lap-times-container">
                <div class="chart-container">
                    <div id="lap-times-chart"></div>
                </div>
                <div class="analysis-panel">
                    <div id="lap-times-table"></div>
                    <div id="lap-times-distribution"></div>
                </div>
            </div>
        </div>
        
        <!-- Section Analysis View -->
        <div id="sections-view" class="view-panel">
            <div class="sections-container">
                <div class="chart-container">
                    <div id="section-radar-chart"></div>
                </div>
                <div class="analysis-panel">
                    <div id="section-comparison-table"></div>
                    <div id="driver-strengths-panel"></div>
                </div>
            </div>
        </div>
        
        <!-- Telemetry View -->
        <div id="telemetry-view" class="view-panel">
            <div class="telemetry-container">
                <div class="chart-tabs">
                    <button class="chart-tab-btn active" data-chart="speed">Speed Profiles</button>
                    <button class="chart-tab-btn" data-chart="braking">Braking Analysis</button>
                    <button class="chart-tab-btn" data-chart="steering">Steering Patterns</button>
                </div>
                
                <div class="chart-content">
                    <div id="telemetry-chart"></div>
                </div>
                
                <div class="telemetry-analysis">
                    <div id="telemetry-metrics-table"></div>
                    <div id="driving-style-analysis"></div>
                </div>
            </div>
        </div>
        
        <!-- Events View -->
        <div id="events-view" class="view-panel">
            <div class="events-container">
                <div class="events-timeline">
                    <div id="events-timeline-chart"></div>
                </div>
                <div class="events-analysis">
                    <div id="events-by-driver"></div>
                    <div id="events-summary"></div>
                </div>
            </div>
        </div>
        
        <!-- Rankings View -->
        <div id="rankings-view" class="view-panel">
            <div class="rankings-container">
                <div class="ranking-metrics">
                    <select id="ranking-metric" class="control-select">
                        <option value="laptime">Best Lap Time</option>
                        <option value="consistency">Consistency</option>
                        <option value="improvement">Improvement Rate</option>
                        <option value="section_performance">Section Performance</option>
                    </select>
                </div>
                
                <div class="rankings-display">
                    <div id="rankings-chart"></div>
                    <div id="rankings-table"></div>
                </div>
            </div>
        </div>
    </div>
</div>
```

### Narrative Panel

```html
<div class="narrative-panel">
    <div class="narrative-tabs">
        <button class="narrative-tab-btn active" data-narrative="team">Team Summary</button>
        <button class="narrative-tab-btn" data-narrative="spotlight">Driver Spotlight</button>
        <button class="narrative-tab-btn" data-narrative="recommendations">Coaching Tips</button>
    </div>
    
    <div class="narrative-content">
        <div id="team-narrative" class="narrative-section active">
            <h3>Team Analysis</h3>
            <div id="team-narrative-content">
                <!-- Team narrative content -->
            </div>
        </div>
        
        <div id="spotlight-narrative" class="narrative-section">
            <h3>Driver Spotlight</h3>
            <div class="spotlight-selector">
                <select id="spotlight-driver-select" class="control-select">
                    <option value="">Select Driver</option>
                </select>
            </div>
            <div id="spotlight-narrative-content">
                <!-- Driver spotlight content -->
            </div>
        </div>
        
        <div id="recommendations-narrative" class="narrative-section">
            <h3>Coaching Recommendations</h3>
            <div id="recommendations-narrative-content">
                <!-- Coaching recommendations -->
            </div>
        </div>
    </div>
</div>
```

## CSS Styling

### Layout and Responsive Design

```css
/* Dashboard Layout */
.team-dashboard {
    display: grid;
    grid-template-areas: 
        "header header"
        "controls controls"
        "main main"
        "narrative narrative";
    grid-template-columns: 1fr;
    gap: 20px;
    max-width: 1600px;
    margin: 0 auto;
    padding: 20px;
}

.dashboard-header {
    grid-area: header;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.control-panel {
    grid-area: controls;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
}

.visualization-area {
    grid-area: main;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    overflow: hidden;
}

.narrative-panel {
    grid-area: narrative;
    background: #f8f9fa;
    border-radius: 8px;
    padding: 20px;
}

/* Responsive Design */
@media (max-width: 1200px) {
    .team-dashboard {
        grid-template-areas:
            "header"
            "controls"
            "main"
            "narrative";
    }
}

@media (max-width: 768px) {
    .control-panel {
        grid-template-columns: 1fr;
    }
    
    .dashboard-header {
        flex-direction: column;
        gap: 15px;
        text-align: center;
    }
    
    .overview-grid {
        grid-template-columns: 1fr;
    }
}

/* Component Styles */
.control-section {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.control-section h3 {
    margin-top: 0;
    color: #333;
    border-bottom: 2px solid #007bff;
    padding-bottom: 8px;
}

.driver-controls, .metric-controls, .view-controls {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.driver-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
    margin: 10px 0;
}

.checkbox-label, .radio-label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 5px;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.checkbox-label:hover, .radio-label:hover {
    background-color: #f0f0f0;
}

.control-select, .control-input {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
}

.btn-primary {
    background-color: #007bff;
    color: white;
}

.btn-primary:hover {
    background-color: #0056b3;
}

.btn-secondary {
    background-color: #6c757d;
    color: white;
}

.btn-secondary:hover {
    background-color: #545b62;
}

/* View Tabs */
.view-tabs, .chart-tabs, .narrative-tabs {
    display: flex;
    background: #f8f9fa;
    border-bottom: 1px solid #dee2e6;
}

.tab-btn, .chart-tab-btn, .narrative-tab-btn {
    padding: 12px 20px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
    border-bottom: 3px solid transparent;
}

.tab-btn.active, .chart-tab-btn.active, .narrative-tab-btn.active {
    background: white;
    border-bottom-color: #007bff;
    color: #007bff;
}

.view-panel {
    display: none;
    padding: 20px;
}

.view-panel.active {
    display: block;
}

/* Overview Grid */
.overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
}

.overview-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.overview-card h3 {
    margin-top: 0;
    color: #333;
    border-bottom: 2px solid #007bff;
    padding-bottom: 8px;
}

/* Chart Containers */
.chart-container {
    height: 400px;
    margin: 20px 0;
    background: white;
    border-radius: 8px;
    padding: 20px;
}

/* Analysis Panels */
.analysis-panel {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 20px;
}

@media (max-width: 1024px) {
    .analysis-panel {
        grid-template-columns: 1fr;
    }
}

/* Loading States */
.loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px;
    color: #6c757d;
}

.loading::after {
    content: "";
    width: 20px;
    height: 20px;
    border: 2px solid #007bff;
    border-radius: 50%;
    border-top-color: transparent;
    animation: spin 1s linear infinite;
    margin-left: 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
```

## JavaScript Implementation

### Main Dashboard Controller

```javascript
class TeamDashboard {
    constructor(containerId, sessionId) {
        this.container = document.getElementById(containerId);
        this.sessionId = sessionId;
        this.currentView = 'overview';
        this.selectedDrivers = new Set();
        this.selectedMetrics = new Set(['lap_times', 'section_analysis']);
        this.currentLanguage = 'zh-Hant';
        this.comparisonData = null;
        this.narrativeData = null;
        
        this.initialize();
    }
    
    async initialize() {
        await this.loadSessionData();
        this.setupEventListeners();
        this.renderDashboard();
    }
    
    async loadSessionData() {
        try {
            // Load basic session info
            const sessionResponse = await fetch(`/api/session/${this.sessionId}/bundle`);
            const sessionData = await sessionResponse.json();
            
            // Load comparison data
            const comparisonResponse = await fetch(`/api/session/${this.sessionId}/compare`);
            this.comparisonData = await comparisonResponse.json();
            
            // Initialize selected drivers
            this.comparisonData.drivers.forEach(driver => {
                this.selectedDrivers.add(driver);
            });
            
            this.updateSessionInfo(sessionData);
        } catch (error) {
            console.error('Failed to load session data:', error);
            this.showError('Failed to load session data');
        }
    }
    
    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchView(btn.dataset.view));
        });
        
        // Driver selection
        document.getElementById('select-all-drivers').addEventListener('change', (e) => {
            this.toggleAllDrivers(e.target.checked);
        });
        
        // Metric selection
        document.querySelectorAll('input[name="metric"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.toggleMetric(checkbox.value, checkbox.checked));
        });
        
        // Language selection
        document.getElementById('language-selector').addEventListener('change', (e) => {
            this.changeLanguage(e.target.value);
        });
        
        // Export functionality
        document.getElementById('export-btn').addEventListener('click', () => {
            this.exportComparison();
        });
        
        // Comparison mode
        document.querySelectorAll('input[name="comparison-mode"]').forEach(radio => {
            radio.addEventListener('change', () => this.changeComparisonMode(radio.value));
        });
    }
    
    renderDashboard() {
        this.renderDriverControls();
        this.renderCurrentView();
        this.loadNarratives();
    }
    
    renderDriverControls() {
        const driverCheckboxes = document.getElementById('driver-checkboxes');
        driverCheckboxes.innerHTML = '';
        
        this.comparisonData.drivers.forEach(driver => {
            const driverItem = document.createElement('label');
            driverItem.className = 'checkbox-label';
            driverItem.innerHTML = `
                <input type="checkbox" value="${driver}" 
                       ${this.selectedDrivers.has(driver) ? 'checked' : ''}>
                <span>${driver}</span>
            `;
            
            driverItem.querySelector('input').addEventListener('change', () => {
                this.toggleDriver(driver, driverItem.querySelector('input').checked);
            });
            
            driverCheckboxes.appendChild(driverItem);
        });
        
        // Update head-to-head selectors
        const driver1Select = document.getElementById('driver1-select');
        const driver2Select = document.getElementById('driver2-select');
        
        [driver1Select, driver2Select].forEach(select => {
            select.innerHTML = '<option value="">Select Driver</option>';
            this.comparisonData.drivers.forEach(driver => {
                const option = document.createElement('option');
                option.value = driver;
                option.textContent = driver;
                select.appendChild(option);
            });
        });
    }
    
    switchView(viewName) {
        // Update tab states
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === viewName);
        });
        
        // Update view panels
        document.querySelectorAll('.view-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        
        const targetPanel = document.getElementById(`${viewName}-view`);
        if (targetPanel) {
            targetPanel.classList.add('active');
        }
        
        this.currentView = viewName;
        this.renderCurrentView();
    }
    
    renderCurrentView() {
        switch (this.currentView) {
            case 'overview':
                this.renderOverviewView();
                break;
            case 'lap-times':
                this.renderLapTimesView();
                break;
            case 'sections':
                this.renderSectionsView();
                break;
            case 'telemetry':
                this.renderTelemetryView();
                break;
            case 'events':
                this.renderEventsView();
                break;
            case 'rankings':
                this.renderRankingsView();
                break;
        }
    }
    
    renderOverviewView() {
        this.renderTeamSummary();
        this.renderRankingsOverview();
        this.renderKeyInsights();
        this.renderQuickStats();
    }
    
    renderTeamSummary() {
        const container = document.getElementById('team-summary-content');
        const teamSummary = this.comparisonData.comparison.team_summary;
        
        container.innerHTML = `
            <div class="summary-metrics">
                <div class="metric">
                    <span class="metric-label">Best Lap:</span>
                    <span class="metric-value">${teamSummary.best_lap.driver}</span>
                    <span class="metric-detail">${(teamSummary.best_lap.laptime_ms / 1000).toFixed(1)}s</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Most Consistent:</span>
                    <span class="metric-value">${teamSummary.most_consistent.driver}</span>
                    <span class="metric-detail">${(teamSummary.most_consistent.consistency_score * 100).toFixed(0)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Pace Spread:</span>
                    <span class="metric-value">${(teamSummary.team_metrics.pace_spread_ms / 1000).toFixed(1)}s</span>
                </div>
            </div>
        `;
    }
    
    async loadNarratives() {
        try {
            const response = await fetch(`/api/session/${this.sessionId}/compare/narrative?narrative_type=team&lang=${this.currentLanguage}`);
            this.narrativeData = await response.json();
            this.renderTeamNarrative();
        } catch (error) {
            console.error('Failed to load narratives:', error);
        }
    }
    
    renderTeamNarrative() {
        const container = document.getElementById('team-narrative-content');
        if (!this.narrativeData) return;
        
        container.innerHTML = this.narrativeData.lines.map(line => 
            `<p class="narrative-line">${line}</p>`
        ).join('');
    }
    
    toggleDriver(driver, isSelected) {
        if (isSelected) {
            this.selectedDrivers.add(driver);
        } else {
            this.selectedDrivers.delete(driver);
        }
        
        // Update comparison mode if needed
        if (this.selectedDrivers.size === 2) {
            const drivers = Array.from(this.selectedDrivers);
            document.getElementById('driver1-select').value = drivers[0];
            document.getElementById('driver2-select').value = drivers[1];
        }
        
        this.refreshCurrentView();
    }
    
    toggleMetric(metric, isSelected) {
        if (isSelected) {
            this.selectedMetrics.add(metric);
        } else {
            this.selectedMetrics.delete(metric);
        }
        
        this.refreshCurrentView();
    }
    
    async changeLanguage(lang) {
        this.currentLanguage = lang;
        await this.loadNarratives();
        this.refreshCurrentView();
    }
    
    refreshCurrentView() {
        // Clear current view and re-render
        this.renderCurrentView();
    }
    
    async exportComparison() {
        try {
            const drivers = Array.from(this.selectedDrivers).join(',');
            const response = await fetch(`/api/session/${this.sessionId}/export/comparison?drivers=${drivers}&format=json`);
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.sessionId}_comparison.json`;
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Export failed:', error);
            this.showError('Export failed');
        }
    }
    
    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        alert(message);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const dashboardContainer = document.getElementById('team-dashboard');
    if (dashboardContainer) {
        const sessionId = dashboardContainer.dataset.sessionId || 'barber-demo-r1';
        const dashboard = new TeamDashboard('team-dashboard', sessionId);
    }
});
```

## Integration Points

### 1. HTML Template
Create `docs/team-dashboard.html` that includes all the dashboard components.

### 2. CSS Styling
Create `docs/team-dashboard.css` with responsive design and component styling.

### 3. JavaScript Controller
Implement the `TeamDashboard` class in `docs/team-dashboard.js`.

### 4. API Integration
Connect to the multi-driver comparison endpoints defined in the implementation specification.

### 5. Data Flow
1. Load session data on initialization
2. Fetch comparison data based on selected drivers/metrics
3. Load narratives in selected language
4. Render visualizations using Plotly.js
5. Update narratives when selections change

## Usage Examples

### Access URL
```
https://your-domain.com/team-dashboard.html?session=barber-demo-r1
```

### Features
1. **Multi-driver Selection**: Choose which drivers to compare
2. **Metric Filtering**: Select specific analysis metrics
3. **View Modes**: Switch between different analysis perspectives
4. **Language Support**: Toggle between Chinese and English
5. **Export Options**: Download comparison data and reports
6. **Responsive Design**: Works on desktop, tablet, and mobile

This comprehensive dashboard design provides a professional, feature-rich interface for team analysis and multi-driver comparisons in TrackNarrator.