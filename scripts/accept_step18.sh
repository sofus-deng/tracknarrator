#!/usr/bin/env bash
set -euo pipefail
set +H  # Disable history expansion
export TN_UI_KEY="${TN_UI_KEY:-demo-key}"
export TN_UI_KEYS="${TN_UI_KEYS:-alpha}"
make dev > /dev/null 2>&1 &
DEV_PID=$!
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/ui/login >/dev/null && break; sleep 0.5; done
# login with allowlist key
curl -s -c /tmp/ui18.ck -d "key=${TN_UI_KEY}&uik=alpha" -X POST -L http://127.0.0.1:8000/ui/login >/dev/null
# list sessions (should be 200)
curl -s -b /tmp/ui18.ck http://127.0.0.1:8000/ui/sessions | grep -q "<table"
# trigger audits
curl -s http://127.0.0.1:8000/dev/audits >/dev/null
# simple rate test: hammer until at least one 429 appears (best-effort)
FAIL="0"
for i in {1..60}; do
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -b /tmp/ui18.ck http://127.0.0.1:8000/ui/sessions || true)
  if [ "$http_code" = "429" ]; then FAIL="1"; break; fi
done
test "$FAIL" = "1"
echo "[accept_step18] OK"