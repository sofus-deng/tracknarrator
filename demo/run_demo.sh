#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

# Start dev server
cd backend &&
# Export environment variables from .env file in root
if [ -f "../.env" ]; then
  export $(cat ../.env | xargs)
fi
make dev >../demo/dev.log 2>&1 &
DEV_PID=$!
cleanup() { kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT

# Wait for server ready
echo "Waiting for server to be ready..."
for i in {1..60}; do
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    echo "Server is ready!"
    break
  fi
  sleep 0.5
  if [ "$i" -eq 60 ]; then
    echo "Server not ready"; exit 1
  fi
done

mkdir -p demo/export

# Seed barber fixture
echo "Seeding barber fixture..."
cd "$ROOT_DIR"  # Go back to root for the curl command
SEED_RESP="$(curl -sS -X POST http://127.0.0.1:8000/dev/seed -H 'Content-Type: application/json' --data-binary @fixtures/bundle_sample_barber.json)"
cd backend  # Go back to backend for rest of script
echo "Seed response: $SEED_RESP"

# Derive session_id (prefer API JSON, fallback to regex, default to barber)
SESSION_ID="$(python3 - <<'PY' "$SEED_RESP"
import json,sys,re
s=sys.argv[1]
try:
    print(json.loads(s).get("session_id","barber"))
except Exception:
    m=re.search(r'"session_id"\s*:\s*"([^"]+)"', s)
    print(m.group(1) if m else "barber")
PY
)"
echo "session_id=$SESSION_ID"

# Pull summary + exports (zh-Hant/en)
echo "Getting summary..."
curl -sS "http://127.0.0.1:8000/session/${SESSION_ID}/summary?ai_native=on" -o demo/export/summary.json
echo "Getting zh-Hant export..."
curl -sS "http://127.0.0.1:8000/session/${SESSION_ID}/export?lang=zh-Hant" -o demo/export/export_zh.zip
echo "Getting en export..."
curl -sS "http://127.0.0.1:8000/session/${SESSION_ID}/export?lang=en" -o demo/export/export_en.zip

# add coach_score.json (optional)
DEMO_DIR="$ROOT_DIR/demo"
if command -v curl >/dev/null 2>&1; then
  echo "Generating coach_score.json"
  curl -sS "http://127.0.0.1:8000/session/${SESSION_ID}/coach?lang=zh-Hant" > "$DEMO_DIR/export/coach_score.json" || true
fi

echo "Demo OK → demo/export/{summary.json,export_zh.zip,export_en.zip,coach_score.json}"