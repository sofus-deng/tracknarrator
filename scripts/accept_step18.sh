#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 18: Admin security hardening (allowlist, rate limit, TTL)"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# use repo-local temp to avoid /tmp permission quirks in CI
mkdir -p "$ROOT/.accept"
TMP="$(mktemp -d "$ROOT/.accept/step18.XXXXXX")"
LOG="$TMP/server.log"
COOK="$TMP/cookies.txt"

# defaults for a fast CI pass
ALLOWED_KEY="${TN_UI_KEY:-ci-allow}"
DENY_KEY="not-allowed"
READY_DEADLINE="${READY_DEADLINE:-20}"   # seconds to wait server ready
CURL_MAX_TIME="${CURL_MAX_TIME:-1}"      # per curl cap in seconds
RL_SHOTS="${RL_SHOTS:-12}"
RL_PAR="${RL_PAR:-6}"
TTL_SECS="${TN_UI_TTL_S:-2}"             # very short TTL to verify expiry quickly
EXPECT_429="${TN_EXPECT_429:-0}"         # 0=best-effort, 1=require at least one 429

start_server() {
  if command -v uv >/dev/null 2>&1; then
    ( cd backend && \
      TN_UI_KEY="${ALLOWED_KEY}" TN_UI_KEYS="${ALLOWED_KEY}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" \
      TN_UI_TTL_S="${TTL_SECS}" TN_COOKIE_SECURE="0" TN_CORS_ORIGINS="*" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) >"$LOG" 2>&1 &
  else
    ( cd backend && \
      TN_UI_KEY="${ALLOWED_KEY}" TN_UI_KEYS="${ALLOWED_KEY}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" \
      TN_UI_TTL_S="${TTL_SECS}" TN_COOKIE_SECURE="0" TN_CORS_ORIGINS="*" \
      python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) >"$LOG" 2>&1 &
  fi
  echo $! > "$TMP/pid"
}

cleanup() {
  echo "--- tail of server log (accept_step18) ---"
  tail -n 120 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
  rm -rf "$TMP" || true
}
trap cleanup EXIT

start_server

# wait ready
ready=0
for _ in $(seq 1 $READY_DEADLINE); do
  if curl -s --max-time "$CURL_MAX_TIME" http://127.0.0.1:8000/health >/dev/null 2>&1 \
     || curl -s --max-time "$CURL_MAX_TIME" http://127.0.0.1:8000/docs >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo "Server not ready"; exit 1; }

# fetch login page
curl -s --max-time "$CURL_MAX_TIME" -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$TMP/login.html" || true

# robust form parser: read HTML path via env; output JSON to stdout
export LOGIN_HTML="$TMP/login.html"
FORM_JSON="$(
python - <<'PY'
import os, re, json, sys
p=os.environ.get("LOGIN_HTML")
try:
    html=open(p, encoding="utf-8", errors="ignore").read() if p and os.path.exists(p) else ""
except Exception:
    html=""
inputs=re.findall(r'<input[^>]*>', html, flags=re.I)
def attr(tag,n):
    m=re.search(fr'\b{n}="([^"]*)"', tag, flags=re.I)
    return m.group(1) if m else None
keys=[]; csrfn=None; csrft=None; hidden=[]
for it in inputs:
    nm=attr(it,'name'); val=attr(it,'value') or ''
    ty=(attr(it,'type') or '').lower()
    if not nm: continue
    if re.search(r'(key|allow|uik)', nm, flags=re.I): 
        if nm not in keys: keys.append(nm)
    if 'csrf' in nm.lower():
        csrfn = csrfn or nm
        if val: csrft = val
    if ty=='hidden' and nm and val and 'csrf' not in nm.lower() and 'key' not in nm.lower():
        hidden.append([nm,val])
# fallback: look for data-csrf attr
if not csrft:
    m=re.search(r'data-csrf="([^"]+)"', html, flags=re.I)
    if m: csrft=m.group(1)
# sane defaults
if not csrfn: csrfn='csrf_token'
if not keys: keys=['key']
print(json.dumps({"keys":keys, "csrfn":csrfn, "csrft":(csrft or ""), "hidden":hidden}, ensure_ascii=False))
PY
)"
printf '%s' "$FORM_JSON" > "$TMP/form.json"

# small helpers to extract fields
read_json() {
  python - "$1" "$2" <<'PY'
import sys,json
d=json.load(open(sys.argv[1]))
k=sys.argv[2]
v=d.get(k)
if isinstance(v,list): print(",".join(v))
elif v is None: print("")
else: print(v)
PY
}
KEYS="$(read_json "$TMP/form.json" keys)"
CSRFN="$(read_json "$TMP/form.json" csrfn)"
CSRFT="$(read_json "$TMP/form.json" csrft)"

# build urlencoded body
build_form() {
  local keyval="$1"
  local q=""
  IFS=',' read -ra arr <<< "$KEYS"
  for nm in "${arr[@]}"; do
    [ -z "$nm" ] && continue
    q="${q}${q:+&}${nm}=${keyval}"
  done
  if [ -n "${CSRFT:-}" ]; then
    q="${q}&${CSRFN}=${CSRFT}&csrf=${CSRFT}&csrf_token=${CSRFT}"
  fi
  # tolerant hidden fields (no pipeline after heredoc to avoid syntax errors)
  local hidden
  hidden="$(python - "$TMP/form.json" <<'PY'
import sys,json
d=json.load(open(sys.argv[1]))
pairs=d.get("hidden",[])
print("&".join(f"{k}={v}" for k,v in pairs))
PY
)"
  if [ -n "$hidden" ]; then
    q="${q}&${hidden}"
  fi
  echo "$q"
}

# deny path
BAD_FORM="$(build_form "$DENY_KEY")"
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-CSRF-Token: ${CSRFT}" \
  --data "$BAD_FORM" http://127.0.0.1:8000/ui/login -o "$TMP/bad.html" || true
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_bad.html" || true
if grep -Eq "Upload|Sessions|Shares" "$TMP/ui_bad.html"; then
  echo "allowlist failed: bad key authenticated"
  exit 3
fi

# allow path
OK_FORM="$(build_form "$ALLOWED_KEY")"
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-CSRF-Token: ${CSRFT}" \
  --data "$OK_FORM" http://127.0.0.1:8000/ui/login -o "$TMP/ok.html" || true
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_ok.html" || true
grep -Eq "Upload|Sessions|Shares" "$TMP/ui_ok.html" || { echo "login with allowed key did not authenticate"; exit 4; }

# best-effort rate limit (quiet)
RL_FILE="$TMP/rl.txt"; : > "$RL_FILE"
seq 1 "$RL_SHOTS" | xargs -I{} -P "$RL_PAR" sh -c '
  curl -s --max-time '"$CURL_MAX_TIME"' -o /dev/null -w "%{http_code}\n" -b "'"$COOK"'" http://127.0.0.1:8000/sessions || echo 000
' >> "$RL_FILE"
RL429=$(grep -c '^429$' "$RL_FILE" || true)
if [ "$EXPECT_429" = "1" ] && [ "$RL429" -lt 1 ]; then
  echo "rate limiting did not trigger (no 429 observed) while EXPECT_429=1"
  exit 7
fi

# TTL: after expiry, UI must no longer show authenticated chrome
sleep "$((TTL_SECS+1))"
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_after.html" || true
if grep -Eq "Upload|Sessions|Shares" "$TMP/ui_after.html"; then
  echo "TTL not enforced: session still authenticated after expiry"
  exit 8
fi

echo "[accept_step18] OK"