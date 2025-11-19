#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 16: coach scoring + gauge viz"

# Compute directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT="$(cd "${BACKEND_DIR}/.." && pwd)"

# Server configuration
SERVER_LOG="$(mktemp /tmp/tn_accept16_server.XXXXXX.log)"
HOST="127.0.0.1"
PORT="8000"
BASE_URL="http://${HOST}:${PORT}"

# Start server
if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run uvicorn (backend/)"
    ( cd "${BACKEND_DIR}" && \
      TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_CORS_ORIGINS="*" TN_COOKIE_SECURE="0" \
      uv run uvicorn tracknarrator.main:app --host "${HOST}" --port "${PORT}" ) >"${SERVER_LOG}" 2>&1 &
else
    echo "[server] python -m uvicorn (backend/)"
    ( cd "${BACKEND_DIR}" && \
      TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_CORS_ORIGINS="*" TN_COOKIE_SECURE="0" \
      python -m uvicorn tracknarrator.main:app --host "${HOST}" --port "${PORT}" ) >"${SERVER_LOG}" 2>&1 &
fi
SERVER_PID=$!

# Cleanup function
cleanup() {
    echo "--- tail of server log (accept_step16) ---"
    tail -n 200 "${SERVER_LOG}" || true
    if kill -0 "${SERVER_PID}" 2>/dev/null; then
        kill "${SERVER_PID}" || true
        wait "${SERVER_PID}" 2>/dev/null || true
    fi
    rm -f "${SERVER_LOG}" || true
}
trap cleanup EXIT

# Wait for server to be ready
echo "[accept_step16] waiting for server to be ready..."
for i in {1..180}; do
    if curl -sf "${BASE_URL}/docs" >/dev/null 2>&1; then
        echo "[accept_step16] server is ready"
        break
    fi
    sleep 0.5
done

# Verify server is actually ready
curl -sf "${BASE_URL}/docs" >/dev/null || {
    echo "[accept_step16] ERROR: Server not ready after waiting"
    exit 1
}

# Seed data
echo "[accept_step16] seeding data..."
SEED_RESPONSE=$(curl -sS -X POST "${BASE_URL}/dev/seed" \
    -H 'Content-Type: application/json' \
    --data-binary "@${ROOT}/fixtures/bundle_sample_barber.json") || {
    echo "[accept_step16] ERROR: Failed to seed data"
    exit 1
}

SESSION_ID=$(echo "${SEED_RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'barber'))")
echo "[accept_step16] using session_id: ${SESSION_ID}"

# Test coach endpoint
echo "[accept_step16] testing coach endpoint..."
COACH_RESPONSE=$(curl -sS -f "${BASE_URL}/session/${SESSION_ID}/coach") || {
    echo "[accept_step16] ERROR: coach endpoint failed"
    echo "---- curl response ----"
    curl -sS "${BASE_URL}/session/${SESSION_ID}/coach" || true
    exit 1
}


# Verify coach response contains expected fields
python3 -c "
import json, sys
try:
    data = json.loads('''${COACH_RESPONSE}''')
    required_fields = ['total_score', 'badge', 'dimensions']
    for field in required_fields:
        if field not in data:
            print(f'[accept_step16] ERROR: Missing field \"{field}\" in coach response')
            sys.exit(1)
    
    # Validate score ranges
    if 'total_score' in data:
        score = int(data['total_score'])
        if not (0 <= score <= 100):
            print(f'[accept_step16] ERROR: total_score {score} not in range [0, 100]')
            sys.exit(1)
    
    print('[accept_step16] coach response validation passed')
except json.JSONDecodeError as e:
    print(f'[accept_step16] ERROR: Invalid JSON in coach response: {e}')
    sys.exit(1)
except Exception as e:
    print(f'[accept_step16] ERROR: Unexpected error: {e}')
    sys.exit(1)
"

# Test export contains coach_score.json
echo "[accept_step16] testing export pack..."
EXPORT_ZIP="/tmp/exp_accept16.zip"
curl -sS -o "${EXPORT_ZIP}" "${BASE_URL}/session/${SESSION_ID}/export" || {
    echo "[accept_step16] ERROR: export endpoint failed"
    exit 1
}

python3 - <<'PY'
import zipfile, json, sys, os
zip_path = "/tmp/exp_accept16.zip"
try:
    with zipfile.ZipFile(zip_path) as z:
        if "coach_score.json" not in z.namelist():
            print("[accept_step16] ERROR: coach_score.json not found in export")
            sys.exit(1)
        
        data = json.loads(z.read("coach_score.json"))
        if "total_score" not in data:
            print("[accept_step16] ERROR: total_score not found in coach_score.json")
            sys.exit(1)
        
        score = int(data["total_score"])
        if not (0 <= score <= 100):
            print(f"[accept_step16] ERROR: total_score {score} not in range [0, 100]")
            sys.exit(1)
    
    print("[accept_step16] export pack validation passed")
finally:
    if os.path.exists(zip_path):
        os.remove(zip_path)
PY

echo "[accept_step16] OK"