#!/usr/bin/env bash
set -euo pipefail
# 1) run tests
uv run pytest -q
# 2) start server
(make dev > /dev/null 2>&1 &) ; DEV_PID=$!
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 0.5; done
# 3) seed a session and check /sessions
SEED="$(curl -sS -X POST http://127.0.0.1:8000/dev/seed -H 'Content-Type: application/json' --data-binary @backend/fixtures/bundle_sample_barber.json)"
SID="$(python - <<'PY' "$SEED"
import json,sys,re;s=sys.argv[1]
try: print(json.loads(s).get("session_id","barber"))
except: import re; m=re.search(r'"session_id":"([^"]+)"',s); print(m.group(1) if m else "barber")
PY
)"
curl -sS http://127.0.0.1:8000/sessions | grep -q "$SID"
# 4) delete and ensure gone
curl -sS -X DELETE http://127.0.0.1:8000/session/"$SID" -o /dev/null -w "%{http_code}\n"
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/session/"$SID"/summary) ; test "$code" = "404" || test "$code" = "410"
# 5) test GPX upload
printf "%s" '<?xml version="1.0"?><gpx><trk><trkseg><trkpt lat="25" lon="121"><time>2024-10-05T01:02:03Z</time></trkpt></trkseg></trk></gpx>' > /tmp/mini.gpx
code=$(curl -s -o /dev/null -w "%{http_code}" -F "file=@/tmp/mini.gpx;type=application/gpx+xml" http://127.0.0.1:8000/upload)
test "$code" = "201" -o "$code" = "200"
echo "[accept_step11] OK"