# Multi-Driver Comparison Testing Specification

## Overview
This document outlines comprehensive testing strategy for multi-driver comparison features in TrackNarrator, ensuring reliability, performance, and correctness of the new functionality.

## Test Categories

### 1. Unit Tests

#### 1.1 DriverComparison Analytics Tests
**File**: `backend/tests/test_driver_comparison.py`

```python
import pytest
from tracknarrator.driver_comparison import DriverComparison
from tracknarrator.schema import SessionBundle, Session, Lap, Section, Telemetry


class TestDriverComparison:
    """Test suite for DriverComparison class."""
    
    @pytest.fixture
    def multi_driver_bundle(self):
        """Create test bundle with multiple drivers."""
        # Implementation from implementation spec
        pass
    
    def test_initialization(self, multi_driver_bundle):
        """Test DriverComparison initialization."""
        comparison = DriverComparison(multi_driver_bundle)
        
        assert len(comparison.drivers) == 3
        assert "Driver A" in comparison.drivers
        assert "Driver B" in comparison.drivers
        assert "Driver C" in comparison.drivers
    
    def test_lap_time_comparison(self, multi_driver_bundle):
        """Test lap time comparison functionality."""
        comparison = DriverComparison(multi_driver_bundle)
        result = comparison.compare_lap_times()
        
        # Verify structure
        assert "by_driver" in result
        assert "summary" in result
        assert "head_to_head" in result
        
        # Verify driver-specific data
        driver_a_data = result["by_driver"]["Driver A"]
        assert driver_a_data["best_lap_ms"] == 94500
        assert driver_a_data["lap_count"] == 3
        assert 0 <= driver_a_data["consistency_score"] <= 1
    
    def test_section_analysis(self, multi_driver_bundle):
        """Test section performance analysis."""
        comparison = DriverComparison(multi_driver_bundle)
        result = comparison.analyze_section_performance()
        
        # Verify structure
        assert "by_section" in result
        assert "driver_strengths" in result
        
        # Verify section analysis
        im1a_data = result["by_section"]["IM1a"]
        assert "by_driver" in im1a_data
        assert "summary" in im1a_data
    
    def test_team_summary(self, multi_driver_bundle):
        """Test team summary generation."""
        comparison = DriverComparison(multi_driver_bundle)
        result = comparison.generate_team_summary()
        
        # Verify structure
        assert "driver_count" in result
        assert "best_lap" in result
        assert "most_consistent" in result
        assert "team_metrics" in result
        
        # Verify values
        assert result["driver_count"] == 3
        assert result["best_lap"]["driver"] == "Driver A"
        assert result["most_consistent"]["driver"] == "Driver A"
    
    def test_head_to_head_matrix(self, multi_driver_bundle):
        """Test head-to-head comparison matrix."""
        comparison = DriverComparison(multi_driver_bundle)
        result = comparison.compare_lap_times()
        matrix = result["head_to_head"]
        
        # Verify matrix structure
        assert "Driver A" in matrix
        assert "Driver B" in matrix["Driver A"]
        assert "Driver C" in matrix["Driver A"]
        
        # Verify self-comparison
        assert matrix["Driver A"]["Driver A"]["status"] == "same"
        assert matrix["Driver A"]["Driver A"]["advantage_ms"] == 0.0
    
    def test_driver_filtering(self, multi_driver_bundle):
        """Test filtering to specific drivers."""
        comparison = DriverComparison(multi_driver_bundle)
        
        # Test with specific drivers
        result = comparison.compare_lap_times(["Driver A", "Driver B"])
        
        assert "by_driver" in result
        assert "Driver A" in result["by_driver"]
        assert "Driver B" in result["by_driver"]
        assert "Driver C" not in result["by_driver"]
    
    def test_empty_session_handling(self):
        """Test handling of sessions with no data."""
        empty_bundle = SessionBundle(
            session=Session(id="empty", source="test", track_id="test"),
            laps=[], sections=[], telemetry=[], weather=[]
        )
        
        comparison = DriverComparison(empty_bundle)
        assert len(comparison.drivers) == 0
        
        # Should not crash on empty data
        lap_result = comparison.compare_lap_times()
        assert lap_result["by_driver"] == {}
        
        section_result = comparison.analyze_section_performance()
        assert section_result["by_section"] == {}
        
        team_result = comparison.generate_team_summary()
        assert "error" in team_result
```

#### 1.2 Multi-Driver Narrative Tests
**File**: `backend/tests/test_multi_driver_narrative.py`

```python
import pytest
from tracknarrator.multi_driver_narrative import MultiDriverNarrative
from tracknarrator.schema import SessionBundle, Session, Lap


class TestMultiDriverNarrative:
    """Test suite for MultiDriverNarrative class."""
    
    @pytest.fixture
    def multi_driver_bundle(self):
        """Create test bundle with multiple drivers."""
        # Reuse from DriverComparison tests
        pass
    
    def test_team_narrative_generation(self, multi_driver_bundle):
        """Test team narrative generation."""
        narrative = MultiDriverNarrative(multi_driver_bundle)
        
        # Test English
        en_narratives = narrative.generate_team_narrative("en")
        assert isinstance(en_narratives, list)
        assert len(en_narratives) > 0
        
        # Test Chinese
        zh_narratives = narrative.generate_team_narrative("zh-Hant")
        assert isinstance(zh_narratives, list)
        assert len(zh_narratives) > 0
        
        # Verify different content
        assert en_narratives != zh_narratives
    
    def test_head_to_head_narrative(self, multi_driver_bundle):
        """Test head-to-head narrative generation."""
        narrative = MultiDriverNarrative(multi_driver_bundle)
        
        result = narrative.generate_head_to_head_narrative("Driver A", "Driver B", "en")
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Verify content mentions both drivers
        narrative_text = " ".join(result)
        assert "Driver A" in narrative_text
        assert "Driver B" in narrative_text
    
    def test_driver_spotlight_narrative(self, multi_driver_bundle):
        """Test driver spotlight narrative generation."""
        narrative = MultiDriverNarrative(multi_driver_bundle)
        
        result = narrative.generate_driver_spotlight_narrative("Driver A", "en")
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Verify content mentions the driver
        narrative_text = " ".join(result)
        assert "Driver A" in narrative_text
    
    def test_narrative_language_switching(self, multi_driver_bundle):
        """Test language switching in narratives."""
        narrative = MultiDriverNarrative(multi_driver_bundle)
        
        en_result = narrative.generate_team_narrative("en")
        zh_result = narrative.generate_team_narrative("zh-Hant")
        
        # Should produce different content
        assert en_result != zh_result
        
        # Verify language-specific content
        en_text = " ".join(en_result)
        zh_text = " ".join(zh_result)
        
        # Basic language detection (simplified)
        assert any(char in en_text for char in "abcdefghijklmnopqrstuvwxyz")
        assert any(char in zh_text for char in "一個人在中有")
    
    def test_narrative_with_missing_driver(self, multi_driver_bundle):
        """Test narrative generation with non-existent driver."""
        narrative = MultiDriverNarrative(multi_driver_bundle)
        
        result = narrative.generate_driver_spotlight_narrative("NonExistent Driver", "en")
        
        # Should handle gracefully
        assert isinstance(result, list)
        # May return empty list or error message
```

### 2. Integration Tests

#### 2.1 API Endpoint Tests
**File**: `backend/tests/test_api_multi_driver.py`

```python
import pytest
from fastapi.testclient import TestClient
from tracknarrator.api import app
from tracknarrator.store import store


class TestMultiDriverAPI:
    """Test suite for multi-driver API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def multi_driver_session(self, client):
        """Create multi-driver session in store."""
        # Create and seed multi-driver bundle
        # Implementation would create test data
        pass
    
    def test_compare_endpoint(self, client, multi_driver_session):
        """Test /session/{session_id}/compare endpoint."""
        response = client.get("/session/test-session/compare")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "drivers" in data
        assert "comparison" in data
        assert "lap_times" in data["comparison"]
        assert "section_analysis" in data["comparison"]
    
    def test_compare_with_driver_filter(self, client, multi_driver_session):
        """Test comparison endpoint with driver filtering."""
        response = client.get("/session/test-session/compare?drivers=Driver%20A,Driver%20B")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include specified drivers
        assert "Driver A" in data["comparison"]["lap_times"]["by_driver"]
        assert "Driver B" in data["comparison"]["lap_times"]["by_driver"]
        assert "Driver C" not in data["comparison"]["lap_times"]["by_driver"]
    
    def test_compare_with_metric_filter(self, client, multi_driver_session):
        """Test comparison endpoint with metric filtering."""
        response = client.get("/session/test-session/compare?metrics=lap_times")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include requested metrics
        assert "lap_times" in data["comparison"]
        assert "section_analysis" not in data["comparison"]
        assert "telemetry_comparison" not in data["comparison"]
    
    def test_team_endpoint(self, client, multi_driver_session):
        """Test /session/{session_id}/team endpoint."""
        response = client.get("/session/test-session/team")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "team_summary" in data
        assert "driver_count" in data["team_summary"]
        assert "best_lap" in data["team_summary"]
    
    def test_ranking_endpoint(self, client, multi_driver_session):
        """Test /session/{session_id}/ranking endpoint."""
        response = client.get("/session/test-session/ranking?metric=laptime")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "ranking_metric" in data
        assert "rankings" in data
        
        # Verify ranking structure
        rankings = data["rankings"]
        assert len(rankings) > 0
        
        # Check that rankings are ordered
        for i in range(1, len(rankings)):
            assert rankings[i]["rank"] > rankings[i-1]["rank"]
    
    def test_export_comparison_endpoint(self, client, multi_driver_session):
        """Test /session/{session_id}/export/comparison endpoint."""
        response = client.get("/session/test-session/export/comparison?format=json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # Verify content is valid JSON
        data = response.json()
        assert "session_id" in data
        assert "lap_times" in data
    
    def test_export_csv_format(self, client, multi_driver_session):
        """Test CSV export format."""
        response = client.get("/session/test-session/export/comparison?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
        
        # Verify CSV content
        content = response.content.decode()
        lines = content.split('\n')
        assert len(lines) > 1  # Header + data
        assert "Driver" in lines[0]  # Header contains Driver column
    
    def test_narrative_endpoint(self, client, multi_driver_session):
        """Test narrative generation endpoint."""
        response = client.get("/session/test-session/compare/narrative?narrative_type=team&lang=en")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "narrative_type" in data
        assert "lines" in data
        assert "lang" in data
        assert data["lang"] == "en"
        assert data["narrative_type"] == "team"
    
    def test_head_to_head_narrative(self, client, multi_driver_session):
        """Test head-to-head narrative endpoint."""
        response = client.get(
            "/session/test-session/compare/narrative"
            "?narrative_type=head_to_head&driver1=Driver%20A&driver2=Driver%20B"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["lines"]) > 0
        narrative_text = " ".join(data["lines"])
        assert "Driver A" in narrative_text
        assert "Driver B" in narrative_text
    
    def test_error_handling(self, client):
        """Test error handling for non-existent sessions."""
        response = client.get("/session/non-existent/compare")
        
        assert response.status_code == 404
        
        response = client.get("/session/non-existent/team")
        assert response.status_code == 404
    
    def test_invalid_parameters(self, client, multi_driver_session):
        """Test handling of invalid parameters."""
        # Invalid narrative type
        response = client.get("/session/test-session/compare/narrative?narrative_type=invalid")
        assert response.status_code == 400
        
        # Missing required parameters for head-to-head
        response = client.get("/session/test-session/compare/narrative?narrative_type=head_to_head")
        assert response.status_code == 400
```

### 3. Performance Tests

#### 3.1 Load Testing
**File**: `backend/tests/test_performance_multi_driver.py`

```python
import pytest
import time
from tracknarrator.driver_comparison import DriverComparison
from tracknarrator.schema import SessionBundle, Session, Lap


class TestMultiDriverPerformance:
    """Performance tests for multi-driver features."""
    
    @pytest.fixture
    def large_multi_driver_bundle(self):
        """Create bundle with many drivers and laps."""
        # Create 20 drivers with 50 laps each
        session = Session(id="large", source="test", track_id="test")
        laps = []
        
        for driver_idx in range(1, 21):  # 20 drivers
            driver_name = f"Driver {driver_idx}"
            for lap_no in range(1, 51):  # 50 laps each
                laps.append(Lap(
                    session_id="large",
                    lap_no=lap_no,
                    driver=driver_name,
                    laptime_ms=90000 + (driver_idx * 1000) + (lap_no * 100)
                ))
        
        return SessionBundle(session=session, laps=laps, sections=[], telemetry=[], weather=[])
    
    def test_comparison_performance(self, large_multi_driver_bundle):
        """Test performance of comparison operations."""
        comparison = DriverComparison(large_multi_driver_bundle)
        
        # Time lap time comparison
        start_time = time.time()
        result = comparison.compare_lap_times()
        end_time = time.time()
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert end_time - start_time < 5.0  # 5 seconds max
        assert len(result["by_driver"]) == 20
    
    def test_section_analysis_performance(self, large_multi_driver_bundle):
        """Test performance of section analysis."""
        comparison = DriverComparison(large_multi_driver_bundle)
        
        start_time = time.time()
        result = comparison.analyze_section_performance()
        end_time = time.time()
        
        assert end_time - start_time < 3.0  # 3 seconds max
        assert len(result["by_section"]) > 0
    
    def test_team_summary_performance(self, large_multi_driver_bundle):
        """Test performance of team summary generation."""
        comparison = DriverComparison(large_multi_driver_bundle)
        
        start_time = time.time()
        result = comparison.generate_team_summary()
        end_time = time.time()
        
        assert end_time - start_time < 2.0  # 2 seconds max
        assert result["driver_count"] == 20
    
    def test_memory_usage(self, large_multi_driver_bundle):
        """Test memory usage doesn't grow excessively."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Run multiple comparisons
        comparison = DriverComparison(large_multi_driver_bundle)
        
        for _ in range(10):
            comparison.compare_lap_times()
            comparison.analyze_section_performance()
            comparison.generate_team_summary()
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB)
        assert memory_growth < 100 * 1024 * 1024  # 100MB
```

### 4. Frontend Tests

#### 4.1 Component Tests
**File**: `docs/tests/test_multi_driver_ui.js`

```javascript
describe('Multi-Driver Comparison UI', () => {
    let dashboard;
    
    beforeEach(() => {
        // Set up test DOM
        document.body.innerHTML = `
            <div id="team-dashboard" data-session-id="test-session"></div>
        `;
        
        // Mock fetch API
        global.fetch = jest.fn();
        
        dashboard = new TeamDashboard('team-dashboard', 'test-session');
    });
    
    afterEach(() => {
        // Clean up
        document.body.innerHTML = '';
        global.fetch.mockClear();
    });
    
    describe('Initialization', () => {
        test('should initialize with default values', () => {
            expect(dashboard.sessionId).toBe('test-session');
            expect(dashboard.currentView).toBe('overview');
            expect(dashboard.selectedMetrics).toContain('lap_times');
            expect(dashboard.selectedMetrics).toContain('section_analysis');
        });
        
        test('should load session data on initialization', async () => {
            const mockSessionData = { session: { id: 'test-session' } };
            const mockComparisonData = { drivers: ['Driver A', 'Driver B'] };
            
            fetch.mockResolvedValueOnce({
                json: () => Promise.resolve(mockSessionData)
            });
            fetch.mockResolvedValueOnce({
                json: () => Promise.resolve(mockComparisonData)
            });
            
            await dashboard.initialize();
            
            expect(fetch).toHaveBeenCalledWith('/api/session/test-session/bundle');
            expect(fetch).toHaveBeenCalledWith('/api/session/test-session/compare');
        });
    });
    
    describe('Driver Selection', () => {
        test('should toggle driver selection', () => {
            dashboard.selectedDrivers.add('Driver A');
            dashboard.toggleDriver('Driver A', false);
            
            expect(dashboard.selectedDrivers.has('Driver A')).toBe(false);
        });
        
        test('should refresh view when driver selection changes', () => {
            const renderSpy = jest.spyOn(dashboard, 'refreshCurrentView');
            
            dashboard.toggleDriver('Driver A', true);
            
            expect(renderSpy).toHaveBeenCalled();
        });
    });
    
    describe('View Switching', () => {
        test('should switch to lap times view', () => {
            dashboard.switchView('lap-times');
            
            expect(dashboard.currentView).toBe('lap-times');
            expect(document.getElementById('lap-times-view').classList.contains('active')).toBe(true);
        });
        
        test('should update tab states', () => {
            dashboard.switchView('sections');
            
            const tabs = document.querySelectorAll('.tab-btn');
            tabs.forEach(tab => {
                const isActive = tab.classList.contains('active');
                const shouldActive = tab.dataset.view === 'sections';
                expect(isActive).toBe(shouldActive);
            });
        });
    });
    
    describe('Language Switching', () => {
        test('should change language and reload narratives', async () => {
            const loadNarrativesSpy = jest.spyOn(dashboard, 'loadNarratives');
            
            dashboard.changeLanguage('en');
            
            expect(dashboard.currentLanguage).toBe('en');
            expect(loadNarrativesSpy).toHaveBeenCalled();
        });
    });
    
    describe('Export Functionality', () => {
        test('should export comparison data', async () => {
            const mockBlob = new Blob(['test data'], { type: 'application/json' });
            const mockUrl = 'blob:mock-url';
            
            global.URL.createObjectURL = jest.fn(() => mockUrl);
            global.URL.revokeObjectURL = jest.fn();
            
            // Mock fetch for export
            fetch.mockResolvedValueOnce({
                blob: () => Promise.resolve(mockBlob)
            });
            
            // Mock createElement for download link
            const mockAnchor = {
                href: '',
                download: '',
                click: jest.fn()
            };
            global.document.createElement = jest.fn(() => mockAnchor);
            
            await dashboard.exportComparison();
            
            expect(fetch).toHaveBeenCalledWith(
                expect.stringContaining('export/comparison')
            );
            expect(mockAnchor.click).toHaveBeenCalled();
        });
    });
});
```

#### 4.2 Integration Tests
**File**: `docs/tests/test_e2e_multi_driver.js`

```javascript
describe('Multi-Driver E2E Tests', () => {
    let page;
    
    beforeAll(async () => {
        page = await browser.newPage();
        await page.goto('http://localhost:8000/team-dashboard.html?session=test-session');
    });
    
    afterAll(async () => {
        await page.close();
    });
    
    test('should load and display team dashboard', async () => {
        await page.waitForSelector('.team-dashboard');
        
        const sessionId = await page.$eval('#session-id', el => el.textContent);
        expect(sessionId).toContain('test-session');
        
        const driverCount = await page.$eval('#driver-count', el => el.textContent);
        expect(parseInt(driverCount)).toBeGreaterThan(0);
    });
    
    test('should switch between different views', async () => {
        // Switch to lap times view
        await page.click('[data-view="lap-times"]');
        await page.waitForSelector('#lap-times-view.active');
        
        const lapTimesChart = await page.$('#lap-times-chart');
        expect(lapTimesChart).toBeTruthy();
        
        // Switch to sections view
        await page.click('[data-view="sections"]');
        await page.waitForSelector('#sections-view.active');
        
        const sectionRadar = await page.$('#section-radar-chart');
        expect(sectionRadar).toBeTruthy();
    });
    
    test('should filter drivers and update visualizations', async () => {
        // Unselect all drivers except first one
        await page.click('#select-all-drivers');
        await page.click('input[value="Driver B"]');
        await page.click('input[value="Driver C"]');
        
        // Wait for view to update
        await page.waitForTimeout(1000);
        
        // Check that only Driver A data is shown
        const driverCheckboxes = await page.$$('.driver-item input:checked');
        expect(driverCheckboxes).toHaveLength(1);
        
        const checkedLabel = await page.$eval('.driver-item input:checked + span', el => el.textContent);
        expect(checkedLabel).toBe('Driver A');
    });
    
    test('should generate and display narratives', async () => {
        await page.waitForSelector('#team-narrative-content');
        
        const narrativeLines = await page.$$('#team-narrative-content .narrative-line');
        expect(narrativeLines.length).toBeGreaterThan(0);
        
        // Switch language
        await page.select('#language-selector', 'en');
        await page.waitForTimeout(1000);
        
        const englishNarratives = await page.$$('#team-narrative-content .narrative-line');
        expect(englishNarratives.length).toBeGreaterThan(0);
    });
    
    test('should export comparison data', async () => {
        // Set up download monitoring
        const downloadPromise = page.waitForEvent('download');
        
        await page.click('#export-btn');
        
        // Wait for download to start
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toContain('comparison');
    });
});
```

## Test Execution

### 1. Backend Tests
```bash
# Run all multi-driver tests
cd backend
pytest tests/test_driver_comparison.py -v
pytest tests/test_multi_driver_narrative.py -v
pytest tests/test_api_multi_driver.py -v
pytest tests/test_performance_multi_driver.py -v

# Run with coverage
pytest tests/test_driver_comparison.py tests/test_multi_driver_narrative.py --cov=tracknarrator.driver_comparison --cov=tracknarrator.multi_driver_narrative
```

### 2. Frontend Tests
```bash
# Run component tests
cd docs
npm test -- tests/test_multi_driver_ui.js

# Run E2E tests
npm run test:e2e -- tests/test_e2e_multi_driver.js
```

### 3. Integration Tests
```bash
# Run full integration test suite
./scripts/test_multi_driver_integration.sh
```

## Test Data

### Sample Multi-Driver Session
**File**: `tests/fixtures/multi_driver_session.json`

```json
{
  "session": {
    "id": "multi-driver-test",
    "source": "test",
    "track": "Test Track",
    "track_id": "test-track",
    "schema_version": "0.1.2"
  },
  "laps": [
    {"session_id": "multi-driver-test", "lap_no": 1, "driver": "Driver A", "laptime_ms": 95000, "position": 1},
    {"session_id": "multi-driver-test", "lap_no": 2, "driver": "Driver A", "laptime_ms": 94500, "position": 1},
    {"session_id": "multi-driver-test", "lap_no": 3, "driver": "Driver A", "laptime_ms": 96000, "position": 2},
    {"session_id": "multi-driver-test", "lap_no": 1, "driver": "Driver B", "laptime_ms": 97000, "position": 3},
    {"session_id": "multi-driver-test", "lap_no": 2, "driver": "Driver B", "laptime_ms": 96500, "position": 2},
    {"session_id": "multi-driver-test", "lap_no": 3, "driver": "Driver B", "laptime_ms": 97500, "position": 3},
    {"session_id": "multi-driver-test", "lap_no": 1, "driver": "Driver C", "laptime_ms": 98000, "position": 4},
    {"session_id": "multi-driver-test", "lap_no": 2, "driver": "Driver C", "laptime_ms": 99000, "position": 4},
    {"session_id": "multi-driver-test", "lap_no": 3, "driver": "Driver C", "laptime_ms": 98500, "position": 4}
  ],
  "sections": [
    {"session_id": "multi-driver-test", "lap_no": 1, "name": "IM1a", "t_start_ms": 0, "t_end_ms": 15000},
    {"session_id": "multi-driver-test", "lap_no": 1, "name": "IM1", "t_start_ms": 15000, "t_end_ms": 30000},
    {"session_id": "multi-driver-test", "lap_no": 2, "name": "IM1a", "t_start_ms": 0, "t_end_ms": 14500},
    {"session_id": "multi-driver-test", "lap_no": 2, "name": "IM1", "t_start_ms": 14500, "t_end_ms": 29000}
  ],
  "telemetry": [
    {"session_id": "multi-driver-test", "ts_ms": 1000, "speed_kph": 150, "throttle_pct": 80},
    {"session_id": "multi-driver-test", "ts_ms": 2000, "speed_kph": 160, "throttle_pct": 85},
    {"session_id": "multi-driver-test", "ts_ms": 3000, "speed_kph": 140, "throttle_pct": 75}
  ],
  "weather": [
    {"session_id": "multi-driver-test", "ts_ms": 1000, "air_temp_c": 25, "humidity_pct": 60}
  ]
}
```

## Continuous Integration

### GitHub Actions Workflow
**File**: `.github/workflows/test-multi-driver.yml`

```yaml
name: Multi-Driver Tests

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'backend/src/tracknarrator/driver_comparison.py'
      - 'backend/src/tracknarrator/multi_driver_narrative.py'
      - 'backend/tests/test_driver_comparison.py'
      - 'backend/tests/test_multi_driver_narrative.py'
      - 'docs/multi-driver-*.js'
      - 'docs/team-dashboard.js'
  pull_request:
    branches: [ main ]
    paths:
      - 'backend/src/tracknarrator/driver_comparison.py'
      - 'backend/src/tracknarrator/multi_driver_narrative.py'
      - 'backend/tests/test_driver_comparison.py'
      - 'backend/tests/test_multi_driver_narrative.py'
      - 'docs/multi-driver-*.js'
      - 'docs/team-dashboard.js'

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run multi-driver tests
      run: |
        cd backend
        pytest tests/test_driver_comparison.py tests/test_multi_driver_narrative.py tests/test_api_multi_driver.py --cov=tracknarrator.driver_comparison --cov=tracknarrator.multi_driver_narrative --junitxml=reports/junit.xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
        flags: multi-driver
  
  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: |
        cd docs
        npm install
    
    - name: Run frontend tests
      run: |
        cd docs
        npm test -- tests/test_multi_driver_ui.js --coverage
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./docs/coverage/lcov.info
        flags: multi-driver-frontend
  
  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: |
        cd docs
        npm install
    
    - name: Start backend
      run: |
        cd backend
        python -m uvicorn tracknarrator.api:app --host 0.0.0.0 --port 8000 &
        sleep 5
    
    - name: Run E2E tests
      run: |
        cd docs
        npm run test:e2e -- tests/test_e2e_multi_driver.js
    
    - name: Upload E2E results
      uses: actions/upload-artifact@v3
      with:
        name: e2e-results
        path: docs/e2e-results/
```

## Quality Gates

### 1. Code Coverage
- Backend: Minimum 90% coverage for multi-driver modules
- Frontend: Minimum 85% coverage for UI components
- Overall: Minimum 88% coverage for all new features

### 2. Performance Benchmarks
- API response time: < 500ms for comparison endpoints
- UI rendering: < 2 seconds for dashboard initialization
- Memory usage: < 100MB growth for large sessions

### 3. Accessibility
- WCAG 2.1 AA compliance for dashboard UI
- Keyboard navigation support
- Screen reader compatibility
- Color contrast requirements

### 4. Browser Compatibility
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

This comprehensive testing specification ensures the multi-driver comparison features are reliable, performant, and meet quality standards before release.