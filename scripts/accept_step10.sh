#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 10: share tokens + public shared summary"

# Resolve repo root and backend dir
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

LOG_DIR="$(mktemp -d /tmp/tn_accept10.XXXXXX)"
LOG_FILE="$LOG_DIR/server.log"

# Start backend server via uv + uvicorn
(
  uv run uvicorn tracknarrator.api:app \
    --host 127.0.0.1 \
    --port 8000 \
    >"$LOG_FILE" 2>&1
) &
SERVER_PID=$!

cleanup() {
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Wait for /health to become ready
READY_DEADLINE="${READY_DEADLINE:-30}"  # seconds
deadline=$((SECONDS + READY_DEADLINE))
ready=0
while [ $SECONDS -lt "$deadline" ]; do
  if curl -fsS --max-time 1 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "Server did not become ready in time"
  tail -n 80 "$LOG_FILE" || true
  exit 20
fi

TMP_DIR="$(mktemp -d /tmp/tn_accept10_data.XXXXXX)"

# 1) Seed known-good barber bundle via /dev/seed
FIXTURE="$ROOT_DIR/fixtures/bundle_sample_barber.json"
if [ ! -f "$FIXTURE" ]; then
  echo "Missing fixture: $FIXTURE"
  tail -n 80 "$LOG_FILE" || true
  exit 21
fi

SEED_OUT="$TMP_DIR/seed.json"
SEED_CODE="$(curl -sS -o "$SEED_OUT" -w "%{http_code}" \
  -X POST "http://127.0.0.1:8000/dev/seed" \
  -H "Content-Type: application/json" \
  --data-binary "@$FIXTURE" || true)"

if [ "$SEED_CODE" != "200" ]; then
  echo "Seed failed: HTTP $SEED_CODE"
  cat "$SEED_OUT" || true
  tail -n 80 "$LOG_FILE" || true
  exit 22
fi

# 2) Resolve a session id from /sessions in a schema-agnostic way
SESS_OUT="$TMP_DIR/sessions.json"
curl -sS --max-time 5 "http://127.0.0.1:8000/sessions" -o "$SESS_OUT"

SID="$(
uv run python - <<'PY' "$SESS_OUT"
import sys, json
from pathlib import Path

path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8") if path.exists() else ""
if not raw.strip():
    print("")
    raise SystemExit(0)

try:
    data = json.loads(raw)
except Exception:
    print("")
    raise SystemExit(0)

cands = []

def collect(obj):
    if isinstance(obj, dict):
        # wrapper-style keys
        for wrap in ("items", "sessions", "data", "results"):
            val = obj.get(wrap)
            if isinstance(val, list):
                for x in val:
                    collect(x)
        # direct id-style keys
        for key in ("id", "session_id", "sid"):
            if isinstance(obj.get(key), str):
                cands.append(obj[key])
                break
        # nested dict/list values
        for v in obj.values():
            if isinstance(v, (dict, list)):
                collect(v)
    elif isinstance(obj, list):
        for x in obj:
            collect(x)

collect(data)
# Prefer barber-demo-r1 if found (our seeded session), otherwise use latest
barber_id = next((c for c in cands if c == "barber-demo-r1"), None)
print(barber_id if barber_id else (cands[-1] if cands else ""))
PY
)"

if [ -z "$SID" ]; then
  echo "failed to resolve session id"
  cat "$SESS_OUT" || true
  tail -n 80 "$LOG_FILE" || true
  exit 23
fi

echo "session: $SID"

# 3) Create a share token via /share/{session_id}
SHARE_OUT="$TMP_DIR/share.json"
SHARE_CODE="$(curl -sS -o "$SHARE_OUT" -w "%{http_code}" \
  -X POST "http://127.0.0.1:8000/share/$SID" \
  -H "Content-Type: application/json" \
  -d '{}' || true)"

if [ "$SHARE_CODE" != "200" ]; then
  echo "share creation failed: HTTP $SHARE_CODE"
  cat "$SHARE_OUT" || true
  tail -n 80 "$LOG_FILE" || true
  exit 24
fi

TOKEN="$(
uv run python - <<'PY' "$SHARE_OUT"
import sys, json
from pathlib import Path

path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8") if path.exists() else ""
if not raw.strip():
    print("")
    raise SystemExit(0)

try:
    data = json.loads(raw)
except Exception:
    print("")
    raise SystemExit(0)

token = None
if isinstance(data, dict):
    for key in ("token", "share_token"):
        if isinstance(data.get(key), str):
            token = data[key]
            break
    # best-effort extraction from URL if needed
    if token is None and isinstance(data.get("url"), str):
        url = data["url"]
        segs = [s for s in url.split("/") if s]
        if segs:
            # if URL ends with /summary, take the previous segment as token
            if segs[-1] in ("summary",) and len(segs) >= 2:
                token = segs[-2]
            else:
                token = segs[-1]

print(token or "")
PY
)"

if [ -z "$TOKEN" ]; then
  echo "failed to resolve share token"
  cat "$SHARE_OUT" || true
  tail -n 80 "$LOG_FILE" || true
  exit 25
fi

echo "token: $TOKEN"

# 4) Fetch /shared/{token}/summary and validate contract
SHARED_OUT="$TMP_DIR/shared_summary.json"
SHARED_CODE="$(curl -sS -o "$SHARED_OUT" -w "%{http_code}" \
  "http://127.0.0.1:8000/shared/$TOKEN/summary" || true)"

if [ "$SHARED_CODE" != "200" ]; then
  echo "shared summary failed: HTTP $SHARED_CODE"
  cat "$SHARED_OUT" || true
  tail -n 80 "$LOG_FILE" || true
  exit 26
fi

uv run python - <<'PY' "$SHARED_OUT"
import sys, json
from pathlib import Path

path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8")
data = json.loads(raw)

# basic contract check: presence of key sections
for key in ("events", "cards", "sparklines"):
    if key not in data:
        raise SystemExit(f"missing key in shared summary: {key}")
print("shared summary OK")
PY

echo "[accept_step10] OK"