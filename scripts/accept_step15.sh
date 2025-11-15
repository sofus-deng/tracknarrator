#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# start backend
(cd backend && make dev > /dev/null 2>&1 &) 
DEV_PID=$!
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 0.5; done
# mini GPX upload
GPX='<?xml version="1.0"?><gpx><trk><trkseg><trkpt lat="25" lon="121"><time>2024-10-05T01:02:03Z</time></trkpt></trkseg></trk></gpx>'
SID=$(curl -s -F "file=@-;type=application/gpx+xml;filename=mini.gpx" --data-binary @<(printf "%s" "$GPX") http://127.0.0.1:8000/upload | python -c "
import sys,json,re
s=sys.stdin.read()
try: 
    print(json.loads(s).get('session_id','unknown'))
except: 
    m=re.search(r'\"session_id\":\"([^\"]+)\"',s)
    print(m.group(1) if m else 'unknown')
")
test "$SID" != "unknown"
# create share and verify
TOK=$(curl -s "http://127.0.0.1:8000/share/${SID}?ttl_s=300" | python -c "
import sys,json
print(json.loads(sys.stdin.read())['token'])
")
code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/shared/${TOK}/summary")
test "$code" = "200"
echo "[accept_step15] OK"
