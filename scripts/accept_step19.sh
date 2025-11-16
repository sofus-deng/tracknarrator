#!/usr/bin/env bash
set -euo pipefail
export TN_UI_KEY="${TN_UI_KEY:-demo-key}"
export TN_SHARE_SECRET="${TN_SHARE_SECRET:-secret123}"
cd backend && make dev > /dev/null 2>&1 & 
DEV_PID=$!
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/ui/login >/dev/null && break; sleep 0.5; done
# login with CSRF
CSRF=$(curl -s http://127.0.0.1:8000/ui/login | grep -o 'name="csrf" value="[0-9a-f]*"' | sed 's/.*value="\([0-9a-f]*\)".*/\1/')
curl -s -c /tmp/ui19.ck -d "key=${TN_UI_KEY}&csrf=${CSRF}" -X POST -L http://127.0.0.1:8000/ui/login >/dev/null
# seed and export
cat fixtures/bundle_sample_barber.json | curl -s -X POST -H 'Content-Type: application/json' -d @- http://127.0.0.1:8000/dev/seed >/dev/null
# Get first session ID
SESSIONS=$(curl -s http://127.0.0.1:8000/sessions)
SID=$(echo "$SESSIONS" | /usr/bin/python3 -c "import sys, json; print(json.loads(sys.stdin.read())['sessions'][0]['session_id'])")
curl -s -o /tmp/out.zip "http://127.0.0.1:8000/session/${SID}/export"
/usr/bin/python3 scripts/verify_export.py /tmp/out.zip | grep -q OK
echo "[accept_step19] OK"