#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 3: weather E2E check"

# Normalize to repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

LOG="/tmp/dev_step3.log"

start_server() {
  # Prefer Makefile in backend/
  if [ -f "backend/Makefile" ] && grep -qE '^[[:space:]]*dev:' backend/Makefile; then
    echo "[server] make -C backend dev"
    make -C backend dev > "$LOG" 2>&1 & 
    echo $! > /tmp/tn_dev_pid
    return 0
  fi
  # Else uv + uvicorn
  if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run (uvicorn) in backend/"
    ( cd backend && uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
    echo $! > /tmp/tn_dev_pid
    return 0
  fi
  # Else python -m uvicorn (assuming uvicorn installed via deps)
  if command -v python >/dev/null 2>&1; then
    echo "[server] python -m uvicorn in backend/"
    ( cd backend && python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
    echo $! > /tmp/tn_dev_pid
    return 0
  fi
  echo "[server] No launcher found (make/uv/python)"
  return 1
}

start_server
DEV_PID="$(cat /tmp/tn_dev_pid 2>/dev/null || echo "")"

cleanup() {
  echo "--- tail of server log (accept_step3) ---"
  tail -n 200 "$LOG" || true
  if [ -n "${DEV_PID}" ] && ps -p "${DEV_PID}" >/dev/null 2>&1; then
    kill "${DEV_PID}" >/dev/null 2>&1 || true
    wait "${DEV_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Wait for readiness
READY=0
for i in {1..180}; do
  if curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1; then READY=1; break; fi
  sleep 0.5
done
if [ "$READY" -ne 1 ]; then
  echo "Server did not become ready in time"
  exit 20
fi

# Seed fixture
BUNDLE="backend/tests/fixtures/bundle_sample_barber.json"
if [ ! -f "$BUNDLE" ]; then
  echo "Missing fixture: $BUNDLE"
  exit 21
fi
curl -fsS --retry 5 --retry-all-errors -X POST \
  -H 'Content-Type: application/json' --data-binary @"$BUNDLE" \
  http://127.0.0.1:8000/dev/seed >/dev/null

# Obtain session id
SID="$(curl -fsS --retry 5 --retry-all-errors http://127.0.0.1:8000/sessions | python - <<'PY'
import sys,json
arr=json.loads(sys.stdin.read())
print(arr[0]["session_id"] if arr else "")
PY
)"
if [ -z "$SID" ]; then
  echo "Failed to obtain session_id"
  exit 22
fi
echo "Using session ID: $SID"

# Weather samples
FIX="backend/tests/fixtures"
OK="$FIX/weather_ok.csv"
UTC="$FIX/weather_utc.csv"
SEM="$FIX/weather_semicolon.csv"
for f in "$OK" "$UTC" "$SEM"; do
  if [ ! -f "$f" ]; then
    echo "Missing weather sample: $f"
    exit 23
  fi
done

inspect_weather() {
  local file="$1"
  local label="$2"
  RESP="$(curl -fsS --retry 5 --retry-all-errors -X POST \
    -F "file=@${file}" \
    "http://127.0.0.1:8000/dev/inspect/weather?session_id=${SID}" || true)"
  if [ -z "$RESP" ]; then
    echo "[${label}] empty response from /dev/inspect/weather"
    exit 26
  fi
  echo "$RESP" | python - <<'PY'
import sys,json
j=json.loads(sys.stdin.read())
assert "headers" in j and isinstance(j["headers"], list)
assert "recognized" in j and isinstance(j["recognized"], dict)
assert "reasons" in j and isinstance(j["reasons"], list)
PY
  echo "[${label}] inspect OK"
}

inspect_weather "$OK"  "ok"
inspect_weather "$UTC" "utc"
inspect_weather "$SEM" "semicolon"

echo "[accept_step3] OK"
