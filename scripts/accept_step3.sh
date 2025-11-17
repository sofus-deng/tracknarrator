#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 3: weather E2E check"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

LOG="/tmp/dev_step3.log"
TMP="/tmp/tn_accept3"; mkdir -p "$TMP"

start_server() {
  if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_COOKIE_SECURE="0" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  else
    echo "[server] python -m uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_COOKIE_SECURE="0" \
      python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  fi
  echo $! > "$TMP/pid"
}
cleanup() {
  echo "--- tail of server log (accept_step3) ---"; tail -n 200 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
}
trap cleanup EXIT

start_server
for _ in $(seq 1 180); do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 0.5; done
curl -sf http://127.0.0.1:8000/docs >/dev/null || { echo "Server did not become ready in time"; exit 20; }

FIX="samples"
for f in "$FIX/weather_ok.csv" "$FIX/weather_utc.csv" "$FIX/weather_semicolon.csv"; do
  [ -f "$f" ] || { echo "Missing weather sample: $f"; exit 23; }
done

inspect_weather() {
  local file="$1"; local label="$2"; local out="$TMP/${label}.json"
  if ! curl -fsS --retry 5 --retry-all-errors -X POST -F "file=@${file}" \
       "http://127.0.0.1:8000/dev/inspect/weather" -o "$out"; then
    echo "[${label}] curl failed"; exit 26
  fi
  [ -s "$out" ] || { echo "[${label}] empty response file"; exit 26; }
  F="$out" python - <<'PY'
import os,json; p=os.environ["F"]
data=open(p,"rb").read().decode("utf-8","ignore")
j=json.loads(data)
assert isinstance(j.get("headers"), list)
assert isinstance(j.get("recognized"), dict)
assert isinstance(j.get("reasons"), list)
PY
  echo "[${label}] inspect OK"
}

inspect_weather "$FIX/weather_ok.csv"        "ok"
inspect_weather "$FIX/weather_utc.csv"       "utc"
inspect_weather "$FIX/weather_semicolon.csv" "semicolon"
echo "[accept_step3] OK"
