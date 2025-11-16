#!/usr/bin/env bash
set -euo pipefail

echo "Sync demo artifacts to docs/data (for Pages)"

# Normalize to repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

mkdir -p docs/data
LOG="/tmp/dev_pages.log"

start_server() {
  if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_COOKIE_SECURE="0" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
    echo $! > /tmp/tn_pages_pid
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "[server] python -m uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_COOKIE_SECURE="0" \
      python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
    echo $! > /tmp/tn_pages_pid
    return 0
  fi
  echo "[server] No uv/python found"
  return 1
}

start_server
DEV_PID="$(cat /tmp/tn_pages_pid 2>/dev/null || echo "")"

cleanup() {
  echo "--- tail of server log (pages sync) ---"
  tail -n 200 "$LOG" || true
  if [ -n "${DEV_PID}" ] && ps -p "${DEV_PID}" >/dev/null 2>&1; then
    kill "${DEV_PID}" >/dev/null 2>&1 || true
    wait "${DEV_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Wait for readiness (up to 90s)
READY=0
for i in {1..180}; do
  if curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1; then READY=1; break; fi
  sleep 0.5
done
if [ "$READY" -ne 1 ]; then
  echo "Server not ready"
  exit 1
fi

# Seed sample bundle
BUNDLE="backend/tests/fixtures/bundle_sample_barber.json"
curl -fsS --retry 5 --retry-all-errors -X POST \
  -H 'Content-Type: application/json' --data-binary @"$BUNDLE" \
  http://127.0.0.1:8000/dev/seed >/dev/null

# Pick session id
SID="$(curl -fsS --retry 5 --retry-all-errors http://127.0.0.1:8000/sessions | python - <<'PY'
import sys,json
arr=json.loads(sys.stdin.read())
print(arr[0]["session_id"] if arr else "")
PY
)"
test -n "$SID"

# Generate docs/data artifacts
curl -fsS --retry 5 --retry-all-errors \
  "http://127.0.0.1:8000/session/${SID}/summary" -o docs/data/summary.json
curl -fsS --retry 3 --retry-all-errors \
  "http://127.0.0.1:8000/session/${SID}/viz" -o docs/data/viz.json || true
curl -fsS --retry 3 --retry-all-errors \
  "http://127.0.0.1:8000/session/${SID}/coach" -o docs/data/coach_score.json || true

echo "[sync_demo_to_docs] OK"