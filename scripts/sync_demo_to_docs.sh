#!/usr/bin/env bash
set -euo pipefail

echo "Sync demo artifacts to docs/data (for Pages)"

# Normalize to repo root
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

mkdir -p docs/data
mkdir -p docs/demo/export
LOG="/tmp/dev_pages.log"
TMP="/tmp/tn_pages"
mkdir -p "$TMP"

start_server() {
  if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_COOKIE_SECURE="0" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
    echo $! > "$TMP/pid"
    return 0
  fi
  echo "[server] python -m uvicorn (backend/)"
  ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
    TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_COOKIE_SECURE="0" \
    python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  echo $! > "$TMP/pid"
}

stop_server() {
  echo "--- tail of server log (pages sync) ---"
  tail -n 200 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
}
trap stop_server EXIT

start_server

# Wait for readiness (≤90s)
for _ in $(seq 1 180); do
  if curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1; then break; fi
  sleep 0.5
done

# If still不通，就直接寫 placeholder
if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && \
   ! curl -sf http://127.0.0.1:8000/docs   >/dev/null 2>&1; then
  echo "[sync] backend not reachable, writing placeholder"
  cat > docs/data/summary.json <<'JSON'
{"kpis":{"total_laps":0,"best_lap_ms":null,"median_lap_ms":null,"session_duration_ms":null},"events":[],"cards":[],"sparklines":{"laps_ms":[],"sections_ms":[],"speed_series":[]},"narrative":{"lines":["TrackNarrator demo placeholder"],"lang":"en"}}
JSON
  echo "[sync_demo_to_docs] OK (placeholder: no backend)"
  exit 0
fi

# Seed sample bundle if存在
BUNDLE="backend/tests/fixtures/bundle_sample_barber.json"
if [ -f "$BUNDLE" ]; then
  curl -sS --retry 5 --retry-all-errors -X POST \
    -H 'Content-Type: application/json' --data-binary @"$BUNDLE" \
    http://127.0.0.1:8000/dev/seed >/dev/null || true
fi

# 安全取得 sessions → tmp，再由 Python 解析
curl -sS --retry 5 --retry-all-errors \
  http://127.0.0.1:8000/sessions -o "$TMP/sessions.json" || true

SID="$(uv run python - <<'PY'
import json,sys,os
p=os.environ.get("P","/tmp/tn_pages/sessions.json")
try:
  arr=json.load(open(p,"r"))
  print(arr[0]["session_id"] if arr else(""))
except Exception:
  print("")
PY
P="$TMP/sessions.json")"

# 有 SID 就拉 live API；不然寫 placeholder
write_placeholder() {
  cat > docs/data/summary.json <<'JSON'
{"kpis":{"total_laps":0,"best_lap_ms":null,"median_lap_ms":null,"session_duration_ms":null},"events":[],"cards":[],"sparklines":{"laps_ms":[],"sections_ms":[],"speed_series":[]},"narrative":{"lines":["TrackNarrator demo placeholder"],"lang":"en"}}
JSON
  echo "[sync_demo_to_docs] OK (placeholder: no SID)"
  exit 0
}

if [ -z "$SID" ]; then
  write_placeholder
fi

# 下載各檔：若寫入失敗或空檔，改寫 placeholder 不失敗
fetch_or_fallback() {
  local url="$1"; local out="$2"
  if ! curl -sS --retry 5 --retry-all-errors "$url" -o "$out"; then
    return 1
  fi
  # 確保非空
  if [ ! -s "$out" ]; then
    return 1
  fi
  return 0
}

if ! fetch_or_fallback "http://127.0.0.1:8000/session/${SID}/summary" docs/data/summary.json; then
  write_placeholder
fi

fetch_or_fallback "http://127.0.0.1:8000/session/${SID}/viz"        docs/data/viz.json        || true
fetch_or_fallback "http://127.0.0.1:8000/session/${SID}/coach"      docs/data/coach_score.json || true

# Copy demo/export files to docs/demo/export/ for GitHub Pages
echo "[sync_demo_to_docs] Copying demo files to docs/demo/export/"
cp demo/export/summary.json docs/demo/export/ || echo "Warning: demo/export/summary.json not found"
cp demo/export/coach_score.json docs/demo/export/ || echo "Warning: demo/export/coach_score.json not found"
cp demo/export/export_en.zip docs/demo/export/ || echo "Warning: demo/export/export_en.zip not found"
cp demo/export/export_zh.zip docs/demo/export/ || echo "Warning: demo/export/export_zh.zip not found"

echo "[sync_demo_to_docs] OK (live API)"