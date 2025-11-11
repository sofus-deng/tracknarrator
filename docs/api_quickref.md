# TrackNarrator API Quick Reference

## Stable Endpoints

### Data Import
- `POST /dev/seed` - Seed test data from JSON
- `POST /ingest/mylaps-sections` - Import MYLAPS sections CSV
- `POST /ingest/trd-long` - Import TRD telemetry CSV
- `POST /ingest/racechrono` - Import RaceChrono CSV
- `POST /ingest/weather` - Import weather CSV

### Analysis & Export
- `GET /session/{id}/summary?ai_native=on|off` - Session summary with optional AI narrative
- `GET /session/{id}/narrative?lang=zh-Hant|en&ai_native=on|off` - AI-generated narrative
- `GET /session/{id}/export?lang=zh-Hant|en` - Complete export ZIP package
- `GET /session/{id}/events` - Detected events
- `GET /session/{id}/sparklines` - Sparkline data

## Example Requests

### Seed Test Data
```bash
curl -X POST "http://localhost:8000/dev/seed" \
  -H "Content-Type: application/json" \
  --data @fixtures/bundle_sample_barber.json
```

### Get Summary with AI Narrative
```bash
curl "http://localhost:8000/session/barber-demo-r1/summary?ai_native=on"
```

### Get Narrative (Chinese)
```bash
curl "http://localhost:8000/session/barber-demo-r1/narrative?lang=zh-Hant&ai_native=on"
```

### Get Narrative (English)
```bash
curl "http://localhost:8000/session/barber-demo-r1/narrative?lang=en&ai_native=on"
```

### Export Package (Chinese)
```bash
curl "http://localhost:8000/session/barber-demo-r1/export?lang=zh-Hant" \
  -o export_zh.zip
```

### Export Package (English)
```bash
curl "http://localhost:8000/session/barber-demo-r1/export?lang=en" \
  -o export_en.zip
```

## Response Examples

### Narrative Response
```json
{
  "lines": [
    "第2圈節奏異常：配速130000ms，比中位數100500ms偏慢了3.0個標準差。",
    "第2圈IM2a路段異常：通過時間45000ms，比中位數25000ms偏慢了2.8個標準差。",
    "第2圈位置變化：5位→3位，上升了2個位置。"
  ],
  "lang": "zh-Hant",
  "ai_native": true
}
```

### Summary Response
```json
{
  "events": [...],
  "cards": [...],
  "sparklines": {...},
  "narrative": {
    "lines": [...],
    "lang": "zh-Hant",
    "ai_native": true
  }
}
```

### Export ZIP Contents
- `summary.json` - Events, cards, sparklines
- `narrative.json` - AI-generated narrative
- `coach_tips.json` - Coaching recommendations
- `events.json` - Detailed event list
- `cards.json` - Shareable social cards
- `sparklines.json` - Telemetry sparklines
- `kpis.json` - Key performance indicators