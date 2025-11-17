#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 17: Admin UI login + basic flows"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

LOG="/tmp/dev_step17.log"
TMP="/tmp/tn_accept17"
mkdir -p "$TMP"
COOK="$TMP/cookies.txt"

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
}
trap cleanup EXIT

start_server

# wait server ready
for _ in $(seq 1 180); do
  if curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1; then break; fi
  sleep 0.5
done
curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1 || { echo "Server not ready"; exit 1; }

# 1) GET login page & extract CSRF (multiple strategies)
LOGIN_HTML="$TMP/login.html"
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$LOGIN_HTML"
[ -s "$LOGIN_HTML" ] || { echo "login page empty"; exit 2; }

# Flatten for simpler regex
FLAT_HTML="$TMP/login_flat.html"
tr '\n' ' ' < "$LOGIN_HTML" > "$FLAT_HTML" || cp "$LOGIN_HTML" "$FLAT_HTML"

extract_csrf_from_html() {
  python - <<'PY'
import re,sys,io
p=sys.argv[1]
html=open(p,'r',encoding='utf-8',errors='ignore').read()
# Try exact name
m=re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
if not m:
    # Any input whose name starts with csrf
    m=re.search(r'name="csrf[^"]*"\s+value="([^"]+)"', html)
if not m:
    # data-csrf attribute
    m=re.search(r'data-csrf="([^"]+)"', html)
if not m:
    # meta tag
    m=re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', html, re.IGNORECASE)
if not m:
    # meta tag with property
    m=re.search(r'<meta[^>]+property="csrf-token"[^>]+content="([^"]+)"', html, re.IGNORECASE)
print(m.group(1) if m else(""))
PY
"$FLAT_HTML"
}

extract_csrf_from_cookies() {
  # Netscape cookie jar format: columns... name \t value
  awk 'tolower($6) ~ /csrf/ {print $7}' "$COOK" 2>/dev/null | tail -n1 || true
}

CSRF="$(extract_csrf_from_html)"
if [ -z "${CSRF}" ]; then
  CSRF="$(extract_csrf_from_cookies || true)"
fi

if [ -z "${CSRF}" ]; then
  echo "csrf token not found (html/cookie)"; exit 3
fi

# 2) POST login (key + allowlist) — send as form fields and header
KEY="${TN_UI_KEY:-ci-demo}"
POST_DATA="key=${KEY}&allow_key=${KEY}&allowlist_key=${KEY}&csrf=${CSRF}&csrf_token=${CSRF}"
curl -fsS -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRF}" \
     -d "$POST_DATA" http://127.0.0.1:8000/ui/login -o "$TMP/login_resp.html"

# 3) Verify authenticated UI page
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui.html"
grep -E "Upload|Sessions|Shares" "$TMP/ui.html" >/dev/null || { echo "UI not authenticated"; exit 4; }

# 4) Exercise API flow: upload → sessions → share → revoke
GPX="$TMP/min.gpx"
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
     http://127.0.0.1:8000/upload -o "$TMP/upload.json"
[ -s "$TMP/upload.json" ] || { echo "upload response empty"; exit 5; }

# get real session_id from /sessions
curl -fsS http://127.0.0.1:8000/sessions -o "$TMP/sessions.json"
SID="$(python - <<'PY'
import json,sys
j=json.load(open("/tmp/tn_accept17/sessions.json","r",encoding="utf-8"))
arr = j.get("sessions") if isinstance(j,dict) else j
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
curl -fsS --retry 5 --retry-all-errors -X POST -H 'Content-Type: application/json' -d '{}' \
     "http://127.0.0.1:8000/share/${SID}" -o "$TMP/share.json"
TOKEN="$(python - <<'PY'
import json,sys
j=json.load(open("/tmp/tn_accept17/share.json","r",encoding="utf-8"))
print(j.get("token") or j.get("share_token") or "")
PY
)"
[ -n "$TOKEN" ] || { echo "no share token"; exit 8; }

# revoke and verify access denied
curl -fsS --retry 5 --retry-all-errors -X DELETE \
     "http://127.0.0.1:8000/share/${TOKEN}" -o "$TMP/revoke.json"
code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/shared/${TOKEN}/summary")" || code=000
[ "$code" != "200" ] || { echo "revoked token still accessible"; exit 9; }

echo "[accept_step17] OK"