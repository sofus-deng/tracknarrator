# Multi-Driver Narrative Generation Specification

## Overview
This document outlines the design for generating multi-driver narratives that provide team insights and coaching recommendations for TrackNarrator's comparison features.

## Narrative Types

### 1. Team Summary Narrative
Provides a high-level overview of team performance and dynamics.

#### Structure
```python
def generate_team_summary_narrative(
    team_summary: Dict[str, Any],
    lang: str = "zh-Hant"
) -> List[str]:
    """
    Generate team summary narrative.
    
    Args:
        team_summary: Team summary data from DriverComparison.generate_team_summary()
        lang: Language for narrative (zh-Hant/en)
        
    Returns:
        List of narrative strings
    """
```

#### Content Examples
**English:**
- "Team analysis shows Driver A leading the pace with a best lap of 94.5s, while Driver B demonstrates the most consistency at 92%."
- "The team shows a competitive spread of 3.5s across all drivers, indicating balanced performance levels."
- "Driver C shows potential in section IM1a, consistently posting competitive times despite overall slower pace."

**Chinese (Traditional):**
- "團隊分析顯示選手A以94.5秒的最快圈速領先，而選手B展現出92%的最高一致性。"
- "團隊在所有選手之間顯示3.5秒的競爭差距，表明性能水平平衡。"
- "選手C在IM1a路段展現潛力，儘管整體節奏較慢，但持續創造有競爭力的時間。"

### 2. Head-to-Head Comparison Narrative
Focuses on direct comparisons between specific drivers.

#### Structure
```python
def generate_head_to_head_narrative(
    comparison_data: Dict[str, Any],
    driver1: str,
    driver2: str,
    lang: str = "zh-Hant"
) -> List[str]:
    """
    Generate head-to-head comparison narrative.
    
    Args:
        comparison_data: Full comparison data
        driver1: First driver to compare
        driver2: Second driver to compare
        lang: Language for narrative
        
    Returns:
        List of narrative strings
    """
```

#### Content Examples
**English:**
- "When comparing Driver A vs Driver B, Driver A holds a 1.2s advantage on average lap times."
- "Driver B shows better consistency with 85% vs Driver A's 78%, suggesting more stable performance."
- "In section analysis, Driver A excels in high-speed sections (IM1a, IM2a) while Driver B performs better in technical sections (IM1, IM2)."

**Chinese (Traditional):**
- "比較選手A與選手B時，選手A在平均圈速上保持1.2秒的優勢。"
- "選手B表現出更好的一致性，85%對比選手A的78%，表明性能更穩定。"
- "在路段分析中，選手A在高速路段（IM1a、IM2a）表現出色，而選手B在技術路段（IM1、IM2）表現更好。"

### 3. Driver Spotlight Narrative
Highlights individual driver strengths and areas for improvement.

#### Structure
```python
def generate_driver_spotlight_narrative(
    driver_data: Dict[str, Any],
    team_context: Dict[str, Any],
    lang: str = "zh-Hant"
) -> List[str]:
    """
    Generate driver spotlight narrative.
    
    Args:
        driver_data: Individual driver comparison data
        team_context: Team context for relative comparison
        lang: Language for narrative
        
    Returns:
        List of narrative strings
    """
```

#### Content Examples
**English:**
- "Driver A demonstrates exceptional pace with the team's best lap time, but consistency at 78% suggests room for improvement."
- "Strengths identified in high-speed sections (IM1a, IM2a) where Driver A consistently outperforms teammates."
- "Recommendation: Focus on consistency in technical sections to convert speed advantage into more consistent lap times."

**Chinese (Traditional):**
- "選手A展現出卓越的節奏，擁有團隊最快圈速，但78%的一致性表明仍有改進空間。"
- "在高速路段（IM1a、IM2a）識別出優勢，選手A在此持續超越隊友。"
- "建議：專注於技術路段的一致性，將速度優勢轉化為更一致的圈速。"

### 4. Section Analysis Narrative
Provides detailed insights about performance on specific track sections.

#### Structure
```python
def generate_section_analysis_narrative(
    section_data: Dict[str, Any],
    team_context: Dict[str, Any],
    lang: str = "zh-Hant"
) -> List[str]:
    """
    Generate section analysis narrative.
    
    Args:
        section_data: Section performance data
        team_context: Team context for comparison
        lang: Language for narrative
        
    Returns:
        List of narrative strings
    """
```

#### Content Examples
**English:**
- "IM1a section shows the smallest performance spread (0.8s) across the team, indicating this is a strength area for all drivers."
- "IM2 section reveals the largest performance gap (2.3s), with Driver A excelling while Driver C struggles significantly."
- "Technical sections (IM1, IM2) show higher variability than high-speed sections, suggesting these are key differentiators."

**Chinese (Traditional):**
- "IM1a路段顯示團隊中最小的性能差距（0.8秒），表明這是所有選手的優勢區域。"
- "IM2路段揭示最大的性能差距（2.3秒），選手A表現出色，而選手C明顯掙扎。"
- "技術路段（IM1、IM2）比高速路段顯示更高的變異性，表明這些是關鍵差異化因素。"

## Implementation Details

### File: `backend/src/tracknarrator/multi_driver_narrative.py`

```python
"""Multi-driver narrative generation for TrackNarrator."""

from typing import Dict, List, Any, Optional
import math

from .driver_comparison import DriverComparison


class MultiDriverNarrative:
    """Generate narratives for multi-driver comparisons."""
    
    def __init__(self, bundle: SessionBundle):
        """Initialize with session bundle."""
        self.bundle = bundle
        self.comparison = DriverComparison(bundle)
    
    def generate_team_narrative(self, lang: str = "zh-Hant") -> List[str]:
        """Generate team summary narrative."""
        team_summary = self.comparison.generate_team_summary()
        
        if lang.startswith("zh"):
            return self._generate_team_narrative_zh(team_summary)
        else:
            return self._generate_team_narrative_en(team_summary)
    
    def _generate_team_narrative_en(self, team_summary: Dict[str, Any]) -> List[str]:
        """Generate team narrative in English."""
        narratives = []
        
        # Pace leadership
        if "best_lap" in team_summary:
            best_driver = team_summary["best_lap"]["driver"]
            best_time = team_summary["best_lap"]["laptime_ms"]
            best_time_s = best_time / 1000
            narratives.append(
                f"Team analysis shows {best_driver} leading the pace with a best lap of {best_time_s:.1f}s"
            )
        
        # Consistency leader
        if "most_consistent" in team_summary:
            consistent_driver = team_summary["most_consistent"]["driver"]
            consistency = team_summary["most_consistent"]["consistency_score"]
            consistency_pct = consistency * 100
            narratives.append(
                f"while {consistent_driver} demonstrates the most consistency at {consistency_pct:.0f}%"
            )
        
        # Team dynamics
        if "team_metrics" in team_summary:
            pace_spread = team_summary["team_metrics"]["pace_spread_ms"]
            pace_spread_s = pace_spread / 1000
            competitive_balance = team_summary["team_metrics"]["competitive_balance"]
            
            if pace_spread < 2000:  # Less than 2 seconds
                narratives.append(
                    f"The team shows a tight spread of {pace_spread_s:.1f}s across all drivers, "
                    f"indicating closely matched performance levels"
                )
            else:
                narratives.append(
                    f"The team shows a competitive spread of {pace_spread_s:.1f}s across all drivers, "
                    f"indicating diverse performance levels"
                )
        
        # Section-specific insights
        if "best_per_section" in team_summary:
            section_leaders = team_summary["best_per_section"]
            if section_leaders:
                # Find driver with most section wins
                section_wins = {}
                for section, leader in section_leaders.items():
                    driver = leader["driver"]
                    section_wins[driver] = section_wins.get(driver, 0) + 1
                
                if section_wins:
                    top_section_driver = max(section_wins, key=section_wins.get)
                    win_count = section_wins[top_section_driver]
                    narratives.append(
                        f"{top_section_driver} excels in {win_count} sections, "
                        f"showing particular strength in specific track areas"
                    )
        
        return narratives
    
    def _generate_team_narrative_zh(self, team_summary: Dict[str, Any]) -> List[str]:
        """Generate team narrative in Chinese (Traditional)."""
        narratives = []
        
        # Pace leadership
        if "best_lap" in team_summary:
            best_driver = team_summary["best_lap"]["driver"]
            best_time = team_summary["best_lap"]["laptime_ms"]
            best_time_s = best_time / 1000
            narratives.append(
                f"團隊分析顯示{best_driver}以{best_time_s:.1f}秒的最快圈速領先"
            )
        
        # Consistency leader
        if "most_consistent" in team_summary:
            consistent_driver = team_summary["most_consistent"]["driver"]
            consistency = team_summary["most_consistent"]["consistency_score"]
            consistency_pct = consistency * 100
            narratives.append(
                f"而{consistent_driver}展現出{consistency_pct:.0f}%的最高一致性"
            )
        
        # Team dynamics
        if "team_metrics" in team_summary:
            pace_spread = team_summary["team_metrics"]["pace_spread_ms"]
            pace_spread_s = pace_spread / 1000
            
            if pace_spread < 2000:  # Less than 2 seconds
                narratives.append(
                    f"團隊在所有選手之間顯示{pace_spread_s:.1f}秒的緊密差距，表明性能水平接近"
                )
            else:
                narratives.append(
                    f"團隊在所有選手之間顯示{pace_spread_s:.1f}秒的競爭差距，表明性能水平多樣化"
                )
        
        # Section-specific insights
        if "best_per_section" in team_summary:
            section_leaders = team_summary["best_per_section"]
            if section_leaders:
                # Find driver with most section wins
                section_wins = {}
                for section, leader in section_leaders.items():
                    driver = leader["driver"]
                    section_wins[driver] = section_wins.get(driver, 0) + 1
                
                if section_wins:
                    top_section_driver = max(section_wins, key=section_wins.get)
                    win_count = section_wins[top_section_driver]
                    narratives.append(
                        f"{top_section_driver}在{win_count}個路段表現出色，在特定賽道區域展現特殊優勢"
                    )
        
        return narratives
    
    def generate_head_to_head_narrative(
        self, 
        driver1: str, 
        driver2: str, 
        lang: str = "zh-Hant"
    ) -> List[str]:
        """Generate head-to-head comparison narrative."""
        lap_comparison = self.comparison.compare_lap_times([driver1, driver2])
        section_analysis = self.comparison.analyze_section_performance([driver1, driver2])
        
        if lang.startswith("zh"):
            return self._generate_head_to_head_narrative_zh(
                lap_comparison, section_analysis, driver1, driver2
            )
        else:
            return self._generate_head_to_head_narrative_en(
                lap_comparison, section_analysis, driver1, driver2
            )
    
    def _generate_head_to_head_narrative_en(
        self, 
        lap_data: Dict[str, Any], 
        section_data: Dict[str, Any],
        driver1: str, 
        driver2: str
    ) -> List[str]:
        """Generate head-to-head narrative in English."""
        narratives = []
        
        if "by_driver" not in lap_data:
            return narratives
        
        d1_data = lap_data["by_driver"].get(driver1)
        d2_data = lap_data["by_driver"].get(driver2)
        
        if not d1_data or not d2_data:
            return narratives
        
        # Pace advantage
        time_diff = d1_data["avg_lap_ms"] - d2_data["avg_lap_ms"]
        if abs(time_diff) > 500:  # More than 0.5 seconds
            if time_diff > 0:
                narratives.append(
                    f"When comparing {driver1} vs {driver2}, {driver2} holds a "
                    f"{abs(time_diff)/1000:.1f}s advantage on average lap times"
                )
            else:
                narratives.append(
                    f"When comparing {driver1} vs {driver2}, {driver1} holds a "
                    f"{abs(time_diff)/1000:.1f}s advantage on average lap times"
                )
        
        # Consistency comparison
        consistency_diff = d1_data["consistency_score"] - d2_data["consistency_score"]
        if abs(consistency_diff) > 0.1:  # More than 10% difference
            if consistency_diff > 0:
                narratives.append(
                    f"{driver1} shows better consistency with {d1_data['consistency_score']*100:.0f}% "
                    f"vs {driver2}'s {d2_data['consistency_score']*100:.0f}%, "
                    f"suggesting more stable performance"
                )
            else:
                narratives.append(
                    f"{driver2} shows better consistency with {d2_data['consistency_score']*100:.0f}% "
                    f"vs {driver1}'s {d1_data['consistency_score']*100:.0f}%, "
                    f"suggesting more stable performance"
                )
        
        # Section performance
        if "driver_strengths" in section_data:
            d1_strengths = section_data["driver_strengths"].get(driver1, {})
            d2_strengths = section_data["driver_strengths"].get(driver2, {})
            
            # Identify complementary strengths
            d1_strong_sections = set(d1_strengths.get("strengths", []))
            d2_strong_sections = set(d2_strengths.get("strengths", []))
            
            if d1_strong_sections and d2_strong_sections:
                if d1_strong_sections != d2_strong_sections:
                    narratives.append(
                        f"In section analysis, {driver1} excels in {', '.join(d1_strong_sections)} "
                        f"while {driver2} performs better in {', '.join(d2_strong_sections)}"
                    )
        
        return narratives
    
    def _generate_head_to_head_narrative_zh(
        self, 
        lap_data: Dict[str, Any], 
        section_data: Dict[str, Any],
        driver1: str, 
        driver2: str
    ) -> List[str]:
        """Generate head-to-head narrative in Chinese (Traditional)."""
        narratives = []
        
        if "by_driver" not in lap_data:
            return narratives
        
        d1_data = lap_data["by_driver"].get(driver1)
        d2_data = lap_data["by_driver"].get(driver2)
        
        if not d1_data or not d2_data:
            return narratives
        
        # Pace advantage
        time_diff = d1_data["avg_lap_ms"] - d2_data["avg_lap_ms"]
        if abs(time_diff) > 500:  # More than 0.5 seconds
            if time_diff > 0:
                narratives.append(
                    f"比較{driver1}與{driver2}時，{driver2}在平均圈速上保持"
                    f"{abs(time_diff)/1000:.1f}秒的優勢"
                )
            else:
                narratives.append(
                    f"比較{driver1}與{driver2}時，{driver1}在平均圈速上保持"
                    f"{abs(time_diff)/1000:.1f}秒的優勢"
                )
        
        # Consistency comparison
        consistency_diff = d1_data["consistency_score"] - d2_data["consistency_score"]
        if abs(consistency_diff) > 0.1:  # More than 10% difference
            if consistency_diff > 0:
                narratives.append(
                    f"{driver1}表現出更好的一致性，{d1_data['consistency_score']*100:.0f}%"
                    f"對比{driver2}的{d2_data['consistency_score']*100:.0f}%，表明性能更穩定"
                )
            else:
                narratives.append(
                    f"{driver2}表現出更好的一致性，{d2_data['consistency_score']*100:.0f}%"
                    f"對比{driver1}的{d1_data['consistency_score']*100:.0f}%，表明性能更穩定"
                )
        
        # Section performance
        if "driver_strengths" in section_data:
            d1_strengths = section_data["driver_strengths"].get(driver1, {})
            d2_strengths = section_data["driver_strengths"].get(driver2, {})
            
            # Identify complementary strengths
            d1_strong_sections = set(d1_strengths.get("strengths", []))
            d2_strong_sections = set(d2_strengths.get("strengths", []))
            
            if d1_strong_sections and d2_strong_sections:
                if d1_strong_sections != d2_strong_sections:
                    narratives.append(
                        f"在路段分析中，{driver1}在{', '.join(d1_strong_sections)}表現出色，"
                        f"而{driver2}在{', '.join(d2_strong_sections)}表現更好"
                    )
        
        return narratives
    
    def generate_driver_spotlight_narrative(
        self, 
        driver: str, 
        lang: str = "zh-Hant"
    ) -> List[str]:
        """Generate driver spotlight narrative."""
        lap_comparison = self.comparison.compare_lap_times([driver])
        section_analysis = self.comparison.analyze_section_performance([driver])
        team_summary = self.comparison.generate_team_summary()
        
        if lang.startswith("zh"):
            return self._generate_driver_spotlight_narrative_zh(
                lap_comparison, section_analysis, team_summary, driver
            )
        else:
            return self._generate_driver_spotlight_narrative_en(
                lap_comparison, section_analysis, team_summary, driver
            )
    
    def _generate_driver_spotlight_narrative_en(
        self, 
        lap_data: Dict[str, Any], 
        section_data: Dict[str, Any],
        team_context: Dict[str, Any],
        driver: str
    ) -> List[str]:
        """Generate driver spotlight narrative in English."""
        narratives = []
        
        if "by_driver" not in lap_data or driver not in lap_data["by_driver"]:
            return narratives
        
        driver_data = lap_data["by_driver"][driver]
        
        # Pace assessment
        if team_context.get("best_lap", {}).get("driver") == driver:
            narratives.append(
                f"{driver} demonstrates exceptional pace with the team's best lap time, "
                f"but consistency at {driver_data['consistency_score']*100:.0f}% suggests room for improvement"
            )
        else:
            best_time = team_context.get("best_lap", {}).get("laptime_ms", 0)
            driver_best = driver_data["best_lap_ms"]
            if best_time > 0:
                gap_ms = driver_best - best_time
                gap_s = gap_ms / 1000
                narratives.append(
                    f"{driver} shows competitive pace with a best lap {gap_s:.1f}s off the team leader"
                )
        
        # Section strengths
        if "driver_strengths" in section_data and driver in section_data["driver_strengths"]:
            strengths = section_data["driver_strengths"][driver].get("strengths", [])
            weaknesses = section_data["driver_strengths"][driver].get("weaknesses", [])
            
            if strengths:
                narratives.append(
                    f"Strengths identified in {', '.join(strengths)} where {driver} "
                    f"consistently outperforms teammates"
                )
            
            if weaknesses:
                narratives.append(
                    f"Areas for improvement include {', '.join(weaknesses)} "
                    f"where {driver} loses significant time to competitors"
                )
        
        # Coaching recommendations
        if driver_data["consistency_score"] < 0.8:
            narratives.append(
                f"Recommendation: Focus on consistency to convert raw pace into more reliable performance"
            )
        
        return narratives
    
    def _generate_driver_spotlight_narrative_zh(
        self, 
        lap_data: Dict[str, Any], 
        section_data: Dict[str, Any],
        team_context: Dict[str, Any],
        driver: str
    ) -> List[str]:
        """Generate driver spotlight narrative in Chinese (Traditional)."""
        narratives = []
        
        if "by_driver" not in lap_data or driver not in lap_data["by_driver"]:
            return narratives
        
        driver_data = lap_data["by_driver"][driver]
        
        # Pace assessment
        if team_context.get("best_lap", {}).get("driver") == driver:
            narratives.append(
                f"{driver}展現出卓越的節奏，擁有團隊最快圈速，"
                f"但{driver_data['consistency_score']*100:.0f}%的一致性表明仍有改進空間"
            )
        else:
            best_time = team_context.get("best_lap", {}).get("laptime_ms", 0)
            driver_best = driver_data["best_lap_ms"]
            if best_time > 0:
                gap_ms = driver_best - best_time
                gap_s = gap_ms / 1000
                narratives.append(
                    f"{driver}展現出競爭力的節奏，最快圈速落後領先者{gap_s:.1f}秒"
                )
        
        # Section strengths
        if "driver_strengths" in section_data and driver in section_data["driver_strengths"]:
            strengths = section_data["driver_strengths"][driver].get("strengths", [])
            weaknesses = section_data["driver_strengths"][driver].get("weaknesses", [])
            
            if strengths:
                narratives.append(
                    f"在{', '.join(strengths)}識別出優勢，{driver}在此持續超越隊友"
                )
            
            if weaknesses:
                narratives.append(
                    f"需要改進的區域包括{', '.join(weaknesses)}，"
                    f"{driver}在此損失大量時間給競爭對手"
                )
        
        # Coaching recommendations
        if driver_data["consistency_score"] < 0.8:
            narratives.append(
                f"建議：專注於一致性，將原始節奏轉化為更可靠的性能"
            )
        
        return narratives
```

## API Integration

### Extended API Endpoints

Add narrative generation to existing comparison endpoints:

```python
@app.get("/session/{session_id}/compare/narrative")
async def get_comparison_narrative(
    session_id: str,
    drivers: str = Query(None, description="Comma-separated list of drivers"),
    narrative_type: str = Query("team", description="Narrative type (team, head_to_head, spotlight)"),
    driver1: str = Query(None, description="First driver for head_to_head"),
    driver2: str = Query(None, description="Second driver for head_to_head"),
    spotlight_driver: str = Query(None, description="Driver for spotlight narrative"),
    lang: str = Query("zh-Hant", description="Language for narrative")
) -> Dict[str, Any]:
    """
    Get multi-driver comparison narratives.
    
    Args:
        session_id: Session ID
        drivers: Comma-separated list of drivers
        narrative_type: Type of narrative to generate
        driver1: First driver for head_to_head comparison
        driver2: Second driver for head_to_head comparison
        spotlight_driver: Driver for spotlight narrative
        lang: Language for narrative
        
    Returns:
        Dictionary with narrative data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Parse drivers list
    driver_list = None
    if drivers:
        driver_list = [d.strip() for d in drivers.split(",") if d.strip()]
    
    # Initialize narrative generator
    narrative_gen = MultiDriverNarrative(bundle)
    
    # Generate narrative based on type
    if narrative_type == "team":
        lines = narrative_gen.generate_team_narrative(lang)
    elif narrative_type == "head_to_head":
        if not driver1 or not driver2:
            raise HTTPException(status_code=400, detail="Both driver1 and driver2 required for head_to_head")
        lines = narrative_gen.generate_head_to_head_narrative(driver1, driver2, lang)
    elif narrative_type == "spotlight":
        if not spotlight_driver:
            raise HTTPException(status_code=400, detail="spotlight_driver required for spotlight narrative")
        lines = narrative_gen.generate_driver_spotlight_narrative(spotlight_driver, lang)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown narrative_type: {narrative_type}")
    
    return {
        "session_id": session_id,
        "narrative_type": narrative_type,
        "lines": lines,
        "lang": lang,
        "generated_at": int(time.time() * 1000)
    }
```

## Frontend Integration

### Narrative Display Component

```javascript
class NarrativeDisplay {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentNarrative = null;
    }
    
    async loadNarrative(sessionId, narrativeType, options = {}) {
        try {
            const params = new URLSearchParams({
                narrative_type: narrativeType,
                lang: options.lang || 'zh-Hant',
                ...options
            });
            
            const response = await fetch(`/api/session/${sessionId}/compare/narrative?${params}`);
            this.currentNarrative = await response.json();
            this.render();
        } catch (error) {
            console.error('Failed to load narrative:', error);
        }
    }
    
    render() {
        if (!this.currentNarrative) return;
        
        const container = document.createElement('div');
        container.className = 'narrative-container';
        
        const title = document.createElement('h3');
        title.textContent = this.getNarrativeTitle(this.currentNarrative.narrative_type);
        container.appendChild(title);
        
        const narrativeList = document.createElement('div');
        narrativeList.className = 'narrative-list';
        
        this.currentNarrative.lines.forEach(line => {
            const lineElement = document.createElement('p');
            lineElement.className = 'narrative-line';
            lineElement.textContent = line;
            narrativeList.appendChild(lineElement);
        });
        
        container.appendChild(narrativeList);
        
        // Clear existing content and add new
        this.container.innerHTML = '';
        this.container.appendChild(container);
    }
    
    getNarrativeTitle(type) {
        const titles = {
            'team': 'Team Summary',
            'head_to_head': 'Head-to-Head Comparison',
            'spotlight': 'Driver Spotlight'
        };
        return titles[type] || 'Analysis';
    }
}
```

## Usage Examples

### 1. Team Summary
```bash
curl "http://localhost:8000/session/barber-demo-r1/compare/narrative?narrative_type=team&lang=en"
```

### 2. Head-to-Head Comparison
```bash
curl "http://localhost:8000/session/barber-demo-r1/compare/narrative?narrative_type=head_to_head&driver1=Driver%20A&driver2=Driver%20B&lang=zh-Hant"
```

### 3. Driver Spotlight
```bash
curl "http://localhost:8000/session/barber-demo-r1/compare/narrative?narrative_type=spotlight&spotlight_driver=Driver%20A&lang=en"
```

This comprehensive narrative generation system provides rich, multilingual insights for multi-driver comparisons, enhancing the coaching value of TrackNarrator's team analysis features.