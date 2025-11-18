#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 18: Admin security hardening (allowlist, rate limit, TTL)"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

TMP="$(mktemp -d /tmp/tn_accept18.XXXXXX)"
LOG="$(mktemp "$TMP/log.XXXXXX.txt")"
COOK="$(mktemp "$TMP/cookies.XXXXXX.txt")"

ALLOWED_KEY="${TN_UI_KEY:-ci-allow}"
DENY_KEY="not-allowed"

start_server() {
  if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run uvicorn (backend/)"
    ( cd backend && \
      TN_UI_KEY="${ALLOWED_KEY}" TN_UI_KEYS="${ALLOWED_KEY}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" \
      TN_UI_TTL_S="${TN_UI_TTL_S:-3}" TN_COOKIE_SECURE="0" TN_CORS_ORIGINS="*" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  else
    echo "[server] python -m uvicorn (backend/)"
    ( cd backend && \
      TN_UI_KEY="${ALLOWED_KEY}" TN_UI_KEYS="${ALLOWED_KEY}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" \
      TN_UI_TTL_S="${TN_UI_TTL_S:-3}" TN_COOKIE_SECURE="0" TN_CORS_ORIGINS="*" \
      python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  fi
  echo $! > "$TMP/pid"
}

cleanup() {
  echo "--- tail of server log (accept_step18) ---"
  tail -n 200 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
  rm -rf "$TMP" || true
}
trap cleanup EXIT

start_server

# wait until server ready
for _ in $(seq 1 180); do
  curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1 || { echo "Server not ready"; exit 1; }

# Helper: extract CSRF from login page (hidden/meta/data/cookie)
get_csrf() {
  local login_html="$1"
  local csrf
  csrf="$(python - "$login_html" <<'PY'
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
  if [ -z "$csrf" ]; then
    csrf="$(awk 'tolower($6) ~ /csrf/ {print $7}' "$COOK" 2>/dev/null | tail -n1 || true)"
  fi
  echo "$csrf"
}

login_page="$TMP/login.html"
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$login_page"
[ -s "$login_page" ] || { echo "login page empty"; exit 2; }
CSRF="$(get_csrf "$login_page")"
: "${CSRF:=}"  # allow empty, we'll also send header

# 1) Deny wrong key: POST with bad key, then /ui should NOT be authenticated
curl -fsS -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRF}" \
     -d "key=${DENY_KEY}&allow_key=${DENY_KEY}&uik=${DENY_KEY}&allowlist_key=${DENY_KEY}&csrf=${CSRF}&csrf_token=${CSRF}" \
     http://127.0.0.1:8000/ui/login -o "$TMP/login_bad.html"

curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_bad.html"
if grep -E "Upload|Sessions|Shares" "$TMP/ui_bad.html" >/dev/null; then
  echo "allowlist failed: bad key got authenticated"
  exit 3
fi

# 2) Login with allowed key and verify authenticated UI
curl -fsS -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRF}" \
     -d "key=${ALLOWED_KEY}&allow_key=${ALLOWED_KEY}&uik=${ALLOWED_KEY}&allowlist_key=${ALLOWED_KEY}&csrf=${CSRF}&csrf_token=${CSRF}" \
     http://127.0.0.1:8000/ui/login -o "$TMP/login_ok.html"

curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_ok.html"
grep -E "Upload|Sessions|Shares" "$TMP/ui_ok.html" >/dev/null || { echo "login with allowed key did not authenticate"; exit 4; }

# 3) Rate limiting: hammer an API and expect >=1 HTTP 429
# Prefer hitting /sessions (idempotent, cheap)
RL429=0
for i in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w "%{http_code}" -b "$COOK" http://127.0.0.1:8000/sessions || echo 000)"
  [ "$code" = "429" ] && RL429=$((RL429+1))
done
if [ "$RL429" -eq 0 ]; then
  # fallback: hammer login POST with bad key to trigger limiter
  for i in $(seq 1 60); do
    code="$(curl -s -o /dev/null -w "%{http_code}" -c "$COOK" -b "$COOK" \
      -H "Content-Type: application/x-www-form-urlencoded" -H "X-CSRF-Token: ${CSRF}" \
      -d "key=${DENY_KEY}&allow_key=${DENY_KEY}&uik=${DENY_KEY}&allowlist_key=${DENY_KEY}&csrf=${CSRF}&csrf_token=${CSRF}" \
      http://127.0.0.1:8000/ui/login || echo 000)"
    [ "$code" = "429" ] && RL429=$((RL429+1))
  done
fi
[ "$RL429" -ge 1 ] || { echo "rate limiting did not trigger (no 429 observed)"; exit 7; }

# 4) Cookie TTL expiry: TN_UI_TTL_S=3 — wait >3s and verify /ui no longer authenticated
sleep 4
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_after_ttl.html" || true
if grep -E "Upload|Sessions|Shares" "$TMP/ui_after_ttl.html" >/dev/null; then
  echo "TTL not enforced: session remained authenticated after expiry"
  exit 8
fi

echo "[accept_step18] OK"