#!/usr/bin/env bash
set -euo pipefail
export TN_UI_KEY="${TN_UI_KEY:-demo-key}"
# Set environment variable for the current shell
export TN_UI_KEY
# Start the server with the environment variable set
(make dev > /dev/null 2>&1 &) 
DEV_PID=$(jobs -p | head -1)
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/ui/login >/dev/null && break; sleep 0.5; done
# login (save cookie)
curl -s -c /tmp/ui.ck -d "key=${TN_UI_KEY}" -X POST -L http://127.0.0.1:8000/ui/login >/dev/null
# seed small GPX via UI upload
GPX='<?xml version="1.0"?><gpx><trk><trkseg><trkpt lat="25" lon="121"><time>2024-10-05T01:02:03Z</time></trkpt></trkseg></trk></gpx>'
printf "%s" "$GPX" > /tmp/mini.gpx
curl -s -b /tmp/ui.ck -F "file=@/tmp/mini.gpx;type=application/gpx+xml" -X POST http://127.0.0.1:8000/ui/upload | grep -q "Uploaded"
# Create a share for first session
SID=$(curl -s http://127.0.0.1:8000/sessions | python3 -c "import sys,json; data=json.loads(sys.stdin.read()); arr=data.get('sessions', []); print(arr[0]['session_id'] if arr else 'none')")
test "$SID" != "none"
curl -s -b /tmp/ui.ck -X POST "http://127.0.0.1:8000/ui/share/${SID}" | grep -q "Viewer"
echo "[accept_step17] OK"
