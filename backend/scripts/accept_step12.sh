#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 12: visualization P1 (backend/scripts/accept_step12.sh)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${BACKEND_ROOT}/.accept_logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/accept_step12_server.log"

SERVER_PID=""

start_server() {
  echo "[server] uv run uvicorn (backend/)"
  pushd "${BACKEND_ROOT}" >/dev/null

  # Minimal env so the app boots the same way as in other acceptance scripts
  export SHARE_SECRET="${SHARE_SECRET:-ci-share-secret}"
  export TN_DB_PATH="${TN_DB_PATH:-${BACKEND_ROOT}/tracknarrator.db}"
  export TN_UI_KEY="${TN_UI_KEY:-ci-demo-key}"
  export TN_UI_KEYS="${TN_UI_KEYS:-ci-demo-key}"
  export TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf-secret}"
  export TN_EXPORT_SIGNING="${TN_EXPORT_SIGNING:-off}"

  uv run uvicorn "tracknarrator.main:app" \
    --host 127.0.0.1 \
    --port 8000 \
    >"${LOG_FILE}" 2>&1 &
  SERVER_PID=$!

  popd >/dev/null
}

wait_for_server() {
  echo "[wait] probing /health until ready..."
  for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
      echo "[wait] server is ready"
      return 0
    fi
    sleep 1
  done
  echo "Server did not become ready in time" >&2
  echo "--- tail of server log (accept_step12) ---" >&2
  tail -n 80 "${LOG_FILE}" || true
  exit 7
}

stop_server() {
  if [[ -n "${SERVER_PID}" ]]; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}

trap stop_server EXIT

start_server
wait_for_server

# 1) Seed demo data so we have a session to work with
SEED_JSON="$(curl -sf -X POST "http://127.0.0.1:8000/dev/seed" -H 'Content-Type: application/json' --data-binary @../fixtures/bundle_sample_barber.json)"

SESSION_ID="$(echo "${SEED_JSON}" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('session_id', ''))")"

if [[ -z "${SESSION_ID}" ]]; then
  echo "Failed to resolve session id from /dev/seed" >&2
  exit 2
fi

echo "[step12] Using session id: ${SESSION_ID}"

# 2) Call the viz endpoint
VIZ_JSON="$(curl -sf "http://127.0.0.1:8000/session/${SESSION_ID}/viz")"

echo "${VIZ_JSON}" | python3 -c "
import json, sys
data = json.load(sys.stdin)
required_keys = ('lap_delta_series', 'section_box')
for key in required_keys:
    if key not in data:
        raise SystemExit(f'viz payload missing key: {key}')
if not isinstance(data['lap_delta_series'], list):
    raise SystemExit('viz payload: lap_delta_series is not a list')
print('viz contract OK')
"

echo "[accept_step12] OK"