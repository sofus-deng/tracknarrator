#!/usr/bin/env bash
set -euo pipefail

# start server
make dev > /dev/null 2>&1 &
DEV_PID=$!
cleanup() {
    kill "$DEV_PID" >/dev/null 2>&1 || true
    wait "$DEV_PID" 2>/dev/null || true
}
trap cleanup EXIT

# wait for server to start
for i in {1..60}; do 
    curl -sf http://127.0.0.1:8000/docs >/dev/null && break
    sleep 0.5
done

# seed data
SEED=$(cat fixtures/bundle_sample_barber.json | curl -sS -X POST http://127.0.0.1:8000/dev/seed -H 'Content-Type: application/json' -d @-)
SID=$(echo "$SEED" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('session_id','barber'))")

# get share token
SHARE=$(curl -sS -X POST "http://127.0.0.1:8000/share/${SID}?ttl_s=3600")
TOK=$(echo "$SHARE" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['token'])")

# call shared summary
curl -sS "http://127.0.0.1:8000/shared/${TOK}/summary?ai_native=on" | jq -e .events >/dev/null 2>&1 || exit 1

echo "[accept_step10] OK"