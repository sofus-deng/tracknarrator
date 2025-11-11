# TrackNarrator Demo Script (Judge Talk Track)

## 30s Problem/Solution
TrackNarrator transforms raw racing telemetry into actionable insights. Drivers upload CSV files from multiple data sources (MYLAPS, TRD, RaceChrono, weather), and our system automatically detects events, generates narratives, and exports complete analysis packages in multiple languages.

## 60s Walkthrough: Importers→Events→Cards→Narrative→Coach→Export

### 1. Data Import (30s)
```bash
# Start the development server
make dev

# Import telemetry data
curl -X POST "http://localhost:8000/ingest/mylaps-sections?session_id=demo" \
  -F "file=@mylaps_data.csv"

curl -X POST "http://localhost:8000/ingest/trd-long?session_id=demo" \
  -F "file=@telemetry.csv"

curl -X POST "http://localhost:8000/ingest/weather?session_id=demo" \
  -F "file=@weather.csv"
```

### 2. Event Detection (10s)
```bash
# Get detected events
curl "http://localhost:8000/session/demo/events"
```

### 3. Summary with Cards & Sparklines (10s)
```bash
# Get comprehensive summary
curl "http://localhost:8000/session/demo/summary"
```

### 4. AI-Native Narrative (10s)
```bash
# Get AI-generated narrative (Chinese)
curl "http://localhost:8000/session/demo/narrative?lang=zh-Hant&ai_native=on"

# Get AI-generated narrative (English)
curl "http://localhost:8000/session/demo/narrative?lang=en&ai_native=on"
```

### 5. Coach Tips & Export (10s)
```bash
# Get complete export package with coaching tips (Chinese)
curl "http://localhost:8000/session/demo/export?lang=zh-Hant" -o demo_export_zh.zip

# Get complete export package with coaching tips (English)
curl "http://localhost:8000/session/demo/export?lang=en" -o demo_export_en.zip
```

## 30s Why Deterministic + Multilingual + Export-First Matters

### Deterministic
- Same input always produces same output using hash-based template selection
- Critical for reproducible analysis and consistent driver feedback
- Enables A/B testing with confidence intervals

### Multilingual
- Native support for Traditional Chinese (zh-Hant) and English (en)
- Templates localized for racing terminology in both languages
- Expands accessibility to global racing community

### Export-First
- All analysis packaged as downloadable ZIP files
- Includes JSON, narrative, coaching tips, events, cards, sparklines
- Works offline - perfect for pit lane analysis and post-session reviews
- Standardized format enables integration with existing tools