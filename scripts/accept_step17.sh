#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 17: Admin UI login + basic flows"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

TMP="$(mktemp -d /tmp/tn_accept17.XXXXXX)"
LOG="$(mktemp "$TMP/log.XXXXXX.txt")"
COOK="$(mktemp "$TMP/cookies.XXXXXX.txt")"

start_server() {
  if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_UI_TTL_S="${TN_UI_TTL_S:-900}" \
      TN_COOKIE_SECURE="0" TN_CORS_ORIGINS="*" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  else
    echo "[server] python -m uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_UI_TTL_S="${TN_UI_TTL_S:-900}" \
      TN_COOKIE_SECURE="0" TN_CORS_ORIGINS="*" \
      python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  fi
  echo $! > "$TMP/pid"
}
cleanup() {
  echo "--- tail of server log (accept_step17) ---"
  tail -n 200 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
  rm -rf "$TMP" || true
}
trap cleanup EXIT

start_server

# wait server ready
for _ in $(seq 1 180); do
  curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1 || { echo "Server not ready"; exit 1; }

# 1) GET login page & extract CSRF (hidden/meta/data/cookie), all via stdin — no fragile redirects
LOGIN_HTML="$(mktemp "$TMP/login.XXXXXX.html")"
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$LOGIN_HTML"
[ -s "$LOGIN_HTML" ] || { echo "login page empty"; exit 2; }

CSRF="$(
uv run python - "$LOGIN_HTML" <<'PY'
import re,sys
p=sys.argv[1]
with open(p,'r',encoding='utf-8',errors='ignore') as f:
    html=f.read()
m = (re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
 or re.search(r'name="csrf[^"]*"[^>]*value="([^"]+)"', html)
 or re.search(r'data-csrf="([^"]+)"', html)
 or re.search(r'<meta[^>]+name="csrf"[^>]+content="([^"]+)"', html))
print(m.group(1) if m else(""))
PY
)"
if [ -z "$CSRF" ]; then
  CSRF="$(awk 'tolower($6) ~ /csrf/ {print $7}' "$COOK" 2>/dev/null | tail -n1 || true)"
fi
# 若仍抓不到，容忍空值，改走 header-only
: "${CSRF:=}"

# 2) POST login with multiple compatible fields + header
KEY="${TN_UI_KEY:-ci-demo}"
POST_DATA="key=${KEY}&uik=${KEY}&allow_key=${KEY}&allowlist_key=${KEY}"
[ -n "$CSRF" ] && POST_DATA="${POST_DATA}&csrf=${CSRF}&csrf_token=${CSRF}"
curl -fsS -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRF}" \
     -d "$POST_DATA" http://127.0.0.1:8000/ui/login -o "$(mktemp "$TMP/login_resp.XXXXXX.html")"

# 3) Verify authenticated UI page
UI_HTML="$(mktemp "$TMP/ui.XXXXXX.html")"
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$UI_HTML"
grep -E "Upload|Sessions|Shares" "$UI_HTML" >/dev/null || { echo "UI not authenticated"; exit 4; }

# 4) Exercise API: upload → sessions (poll) → summary → share → revoke
GPX="$(mktemp "$TMP/min.XXXXXX.gpx")"
cat > "$GPX" <<'GPX'
<gpx version="1.1" creator="tn-accept">
  <trk><name>demo</name><trkseg>
    <trkpt lat="25.0000" lon="121.0000"><time>2020-01-01T00:00:00Z</time></trkpt>
    <trkpt lat="25.0010" lon="121.0010"><time>2020-01-01T00:00:10Z</time></trkpt>
    <trkpt lat="25.0020" lon="121.0020"><time>2020-01-01T00:00:20Z</time></trkpt>
  </trkseg></trk>
</gpx>
GPX

# upload
curl -fsS --retry 5 --retry-all-errors -X POST -F "file=@${GPX}" \
     http://127.0.0.1:8000/upload -o "$(mktemp "$TMP/upload.XXXXXX.json")"

# poll /sessions until at least one entry
for _ in $(seq 1 60); do
  curl -sf http://127.0.0.1:8000/sessions -o "$TMP/sessions.json" || true
  SZ="$(
    uv run python - "$TMP/sessions.json" <<'PY'
import json,sys
try:
    j=json.load(open(sys.argv[1],'r',encoding='utf-8'))
    arr=j.get('sessions') if isinstance(j,dict) else j
    print(len(arr) if isinstance(arr,list) else 0)
except Exception:
    print(0)
PY
  )"
  [ "$SZ" -ge 1 ] && break
  sleep 0.5
done
[ "$SZ" -ge 1 ] || { echo "no sessions available"; exit 6; }

# pick latest sid (tolerant to shapes)
SID="$(
  uv run python - "$TMP/sessions.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1],'r',encoding='utf-8'))
arr=j.get("sessions") if isinstance(j,dict) else j
def pick(x):
  if isinstance(x,str): return x
  if isinstance(x,dict): return x.get("id") or x.get("session_id") or x.get("sid")
  return None
print(pick(arr[0]) if isinstance(arr,list) and arr else "")
PY
)"
[ -n "$SID" ] || { echo "no session id found"; exit 6; }

# wait summary ready
for _ in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/session/${SID}/summary")" || code=000
  [ "$code" = "200" ] && break
  sleep 0.5
done
[ "$code" = "200" ] || { echo "summary not ready for ${SID}"; exit 7; }

# share
SHARE_JSON="$(mktemp "$TMP/share.XXXXXX.json")"
curl -fsS --retry 5 --retry-all-errors -X POST -H 'Content-Type: application/json' -d '{}' \
     "http://127.0.0.1:8000/share/${SID}" -o "$SHARE_JSON"
TOKEN="$(
  uv run python - "$SHARE_JSON" <<'PY'
import json,sys
j=json.load(open(sys.argv[1],'r',encoding='utf-8'))
print(j.get("token") or j.get("share_token") or "")
PY
)"
[ -n "$TOKEN" ] || { echo "no share token"; exit 8; }

# revoke and verify access denied
curl -fsS --retry 5 --retry-all-errors -X DELETE \
     "http://127.0.0.1:8000/share/${TOKEN}" -o "$(mktemp "$TMP/revoke.XXXXXX.json")"
code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/shared/${TOKEN}/summary")" || code=000
[ "$code" != "200" ] || { echo "revoked token still accessible"; exit 9; }

echo "[accept_step17] OK"