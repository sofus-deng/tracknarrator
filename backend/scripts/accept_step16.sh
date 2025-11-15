#!/usr/bin/env bash
set -euo pipefail
# start server
make dev > /dev/null 2>&1 &
DEV_PID=$!
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 0.5; done
# seed
SESSION_ID=$(curl -sS -X POST http://127.0.0.1:8000/dev/seed -H 'Content-Type: application/json' --data-binary @../fixtures/bundle_sample_barber.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'barber'))")
# coach endpoint
curl -sS http://127.0.0.1:8000/session/${SESSION_ID}/coach | grep -E '"total_score"|"badge"|"dimensions"' >/dev/null
# export contains coach_score.json
curl -sS -o /tmp/exp.zip "http://127.0.0.1:8000/session/${SESSION_ID}/export"
python3 - <<'PY'
import zipfile, json, sys
z = zipfile.ZipFile("/tmp/exp.zip")
assert "coach_score.json" in z.namelist()
data = json.loads(z.read("coach_score.json"))
assert 0 <= int(data["total_score"]) <= 100
PY
echo "[accept_step16] OK"