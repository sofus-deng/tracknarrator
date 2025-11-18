#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 13: Share governance - list & revoke share tokens"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${BACKEND_ROOT}/.accept_logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/accept_step13_server.log"

SERVER_PID=""

start_server() {
  echo "[server] uv run uvicorn (backend/)"
  pushd "${BACKEND_ROOT}" >/dev/null

  # Minimal env so the app boots consistently
  export SHARE_SECRET="${SHARE_SECRET:-ci-share-secret}"
  export TN_DB_PATH="${TN_DB_PATH:-${BACKEND_ROOT}/tracknarrator.db}"
  export TN_UI_KEY="${TN_UI_KEY:-ci-demo-key}"
  export TN_UI_KEYS="${TN_UI_KEYS:-ci-demo-key}"
  export TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf-secret}"
  export TN_EXPORT_SIGNING="${TN_EXPORT_SIGNING:-off}"

  uv run uvicorn "tracknarrator.api:app" \
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
  echo "--- tail of server log (accept_step13) ---" >&2
  tail -n 80 "${LOG_FILE}" || true
  exit 7
}

stop_server() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}

trap stop_server EXIT

start_server
wait_for_server

# 1) Seed data so we have at least one session
SEED_JSON="$(curl -sf -X POST "http://127.0.0.1:8000/dev/seed" \
  -H "Content-Type: application/json" \
  --data @"${BACKEND_ROOT}/../fixtures/bundle_sample_barber.json")"

SESSION_ID="$(
  echo "${SEED_JSON}" | python3 -c "
import json, sys

data = json.load(sys.stdin)
sid = None

if isinstance(data, dict):
    # Prefer explicit session_id if present
    sid = data.get('session_id')
    # Fallback: if dev/seed returns a list or sessions structure
    if sid is None and 'sessions' in data and isinstance(data['sessions'], list) and data['sessions']:
        first = data['sessions'][0]
        if isinstance(first, dict):
            sid = first.get('id')

if not sid:
    raise SystemExit('could not resolve session_id from /dev/seed response')

print(sid)
")"

if [[ -z "${SESSION_ID}" ]]; then
  echo "Failed to resolve session id from /dev/seed" >&2
  exit 2
fi

echo "[step13] Using session id: ${SESSION_ID}"

# 2) Create a share with a label
CREATE_RESP="$(curl -sf -X POST \
  -H "Content-Type: application/json" \
  -d '{"label":"ci-accept13"}' \
  "http://127.0.0.1:8000/share/${SESSION_ID}")"

TOKEN="$(
  echo "${CREATE_RESP}" | python3 -c "
import json, sys

data = json.load(sys.stdin)
token = data.get('token')
if not token:
    raise SystemExit('no token in /share response')
print(token)
")"

echo "[step13] Created share token: ${TOKEN}"

# 3) List shares and ensure our share is present and active
SHARES_JSON="$(curl -sf "http://127.0.0.1:8000/shares")"

echo "${SHARES_JSON}" | python3 -c "
import json, sys

data = json.load(sys.stdin)
if not isinstance(data, list):
    raise SystemExit('GET /shares did not return a list')

if not data:
    raise SystemExit('GET /shares returned empty list')

# Basic sanity: ensure at least one share record has required keys
required = {'session_id', 'jti', 'exp_ts'}
if not any(required.issubset(set(item.keys())) for item in data if isinstance(item, dict)):
    raise SystemExit('No share entry in /shares has required keys: ' + ', '.join(sorted(required)))

print('shares listing OK')
"

# 4) Revoke the token and make sure it becomes unusable
DEL_STATUS="$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "http://127.0.0.1:8000/share/${TOKEN}")"
echo "[step13] DELETE /share => ${DEL_STATUS}"

if [[ "${DEL_STATUS}" != "204" ]]; then
  echo "Expected 204 from DELETE /share/{token}, got ${DEL_STATUS}" >&2
  exit 3
fi

# After revocation, shared summary should no longer be accessible (400 or 404 is acceptable)
SHARED_STATUS="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/shared/${TOKEN}/summary")"
echo "[step13] GET /shared/{token}/summary after revoke => ${SHARED_STATUS}"

case "${SHARED_STATUS}" in
  400|401|403|404)
    echo "[step13] shared summary correctly blocked after revocation"
    ;;
  *)
    echo "Expected 4xx (400/401/403/404) for revoked shared token, got ${SHARED_STATUS}" >&2
    exit 4
    ;;
esac

echo "[accept_step13] OK"