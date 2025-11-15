# TrackNarrator API Quick Reference

## Stable Endpoints

### Data Import
- `POST /dev/seed` - Seed test data from JSON
- `POST /ingest/mylaps-sections` - Import MYLAPS sections CSV
- `POST /ingest/trd-long` - Import TRD telemetry CSV
- `POST /ingest/racechrono` - Import RaceChrono CSV
- `POST /ingest/weather` - Import weather CSV
- `POST /upload` - Upload file (CSV, GPX, or ZIP containing supported files)

### Session Management
- `GET /sessions?limit=&offset=` - List all sessions with pagination
- `DELETE /session/{id}` - Delete a session by ID

### Analysis & Export
- `GET /session/{id}/summary?ai_native=on|off` - Session summary with optional AI narrative
- `GET /session/{id}/narrative?lang=zh-Hant|en&ai_native=on|off` - AI-generated narrative
- `GET /session/{id}/export?lang=zh-Hant|en` - Complete export ZIP package
- `GET /session/{id}/coach?lang=zh-Hant|en` - Coach v1.5 scoring (0–100) with dimensions and badge. Deterministic; uses sparklines/events.
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

### Upload File
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@data.csv" \
  -F "name=My Session"
```

### List Sessions
```bash
curl "http://localhost:8000/sessions?limit=10" | jq .
```

### Delete Session
```bash
curl -X DELETE "http://localhost:8000/session/barber-demo-r1"
```

## Share Management

### Create Share Token
```bash
curl -X POST "http://localhost:8000/share/barber-demo-r1?ttl_s=3600&label=my-share"
```

### List Shares
```bash
curl "http://localhost:8000/shares?session_id=barber-demo-r1"
```

### List All Shares
```bash
curl "http://localhost:8000/shares"
```

### Revoke Share
```bash
curl -X DELETE "http://localhost:8000/share/{token}"
```

### Access Shared Summary
```bash
curl "http://localhost:8000/shared/{token}/summary"
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
- `coach_score.json` - Coach v1.5 scoring with dimensions and badge

## CORS Configuration

- CORS: enable by setting `TN_CORS_ORIGINS="*"` for demo, or a comma-separated allowlist for production.
- Web uploader: open `docs/upload.html`; set API Base to your backend; upload CSV/GPX/ZIP → share token & viewer link.
### Admin UI env
- Create a `.env` file (or export OS env) with:
  - `TN_UI_KEY=<your-strong-key>` to enable `/ui` (htmx admin).
- On startup the backend auto-loads `.env` (stdlib parser).
### Admin UI (protected, htmx)
- Set env `TN_UI_KEY="..."` to enable.
- `GET /ui/login` → login form
- `POST /ui/login` (form key) → set signed cookie, redirect /ui
- `GET /ui` → admin shell
- `GET /ui/sessions` → sessions table (fragment)
- `POST /ui/upload` (multipart) → HTML result (fragment)
- `POST /ui/share/{session_id}` → create share, returns shares table (fragment)
- `GET /ui/shares?session_id=...` → list active shares (fragment)
- `DELETE /ui/share/{token}` → revoke (fragment)

### Admin security (Step 18)
- Allowlist: set `TN_UI_KEYS="key1,key2"` - /ui endpoints require a matching allowlist key (cookie `tn_uik` or header `X-API-Key`). If empty, allowlist is disabled.
- Audit: signed records stored in SQLite table `audits`; developer endpoint `GET /dev/audits` returns recent entries.
- Rate limiting: simple token bucket per remote address (burst 20, ~5 rps). Excess returns HTTP 429.
- Cookies: `TN_UI_TTL_S` controls login TTL seconds. Set `TN_COOKIE_SECURE=1` under HTTPS.