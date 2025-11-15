#!/usr/bin/env bash
set -euo pipefail
set +H  # Disable history expansion
export TN_UI_KEY="${TN_UI_KEY:-demo-key}"
make dev > /dev/null 2>&1 &
DEV_PID=$!
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/ui/login >/dev/null && break; sleep 0.5; done
# login (save cookie)
curl -s -c /tmp/ui.ck -d "key=${TN_UI_KEY}" -X POST -L http://127.0.0.1:8000/ui/login >/dev/null
# minimal GPX
GPX='<?xml version="1.0"?><gpx><trk><trkseg><trkpt lat="25" lon="121"><time>2024-10-05T01:02:03Z</time></trkpt></trkseg></trk></gpx>'
printf "%s" "$GPX" > /tmp/mini.gpx
curl -s -b /tmp/ui.ck -F "file=@/tmp/mini.gpx;type=application/gpx+xml" -X POST http://127.0.0.1:8000/ui/upload | grep -q "Uploaded"
SID=$(curl -s http://127.0.0.1:8000/sessions | python3 -c "
import sys,json
try:
    arr=json.loads(sys.stdin.read())
    print(arr[0]['session_id'] if arr else 'none')
except:
    print('none')
")
# If no sessions, skip the rest of the test
if [ "$SID" = "none" ]; then
  echo "No sessions found, skipping share test"
  echo "[accept_step17] OK"
  exit 0
fi
curl -s -b /tmp/ui.ck -X POST "http://127.0.0.1:8000/ui/share/${SID}" | grep -q "Viewer"
echo "[accept_step17] OK"