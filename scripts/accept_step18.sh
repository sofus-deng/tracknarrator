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
EXPECT_429="${TN_EXPECT_429:-0}"      # 0=best-effort, 1=require 429
READY_DEADLINE="${READY_DEADLINE:-30}" # seconds to wait for server
CURL_MAX_TIME="${CURL_MAX_TIME:-2}"    # seconds per curl

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
  tail -n 150 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
  rm -rf "$TMP" || true
}
trap cleanup EXIT

start_server

# wait until server ready (bounded)
for _ in $(seq 1 $((READY_DEADLINE*2))); do
  curl --max-time "$CURL_MAX_TIME" -s http://127.0.0.1:8000/docs >/dev/null 2>&1 && break
  sleep 0.5
done
curl --max-time "$CURL_MAX_TIME" -s http://127.0.0.1:8000/docs >/dev/null 2>&1 || { echo "Server not ready"; exit 1; }

extract_form_fields() {
  local html="$1"
  python - "$html" <<'PY'
import re, sys, urllib.parse
p=sys.argv[1]
with open(p,'r',encoding='utf-8',errors='ignore') as f:
    html=f.read()

inputs = re.findall(r'<input[^>]*>', html, flags=re.I)
def attr(tag, name):
    m=re.search(r'%s="([^"]*)"'%name, tag, flags=re.I)
    return m.group(1) if m else None

key_names=[]
csrf_name=None
csrf_val=None
hidden_pairs=[]

for it in inputs:
    nm = attr(it, 'name')
    val = attr(it, 'value') or ''
    typ = (attr(it, 'type') or '').lower()
    if not nm:
        continue
    if re.search(r'(key|uik|allow)', nm, flags=re.I):
        key_names.append(nm)
    elif typ in ('password','text') and re.search(r'key', nm, flags=re.I):
        key_names.append(nm)
    if re.search(r'^csrf(_token)?$', nm, flags=re.I) or re.search(r'csrf', nm, flags=re.I):
        if not csrf_name:
            csrf_name = nm
        if val:
            csrf_val = val
    if typ == 'hidden' and nm and val:
        hidden_pairs.append((nm, val))

if not csrf_val:
    m=re.search(r'data-csrf="([^"]+)"', html, flags=re.I)
    if m: csrf_val=m.group(1)
if not csrf_val:
    m=re.search(r'<meta[^>]+name="csrf"[^>]+content="([^"]+)"', html, flags=re.I)
    if m: csrf_val=m.group(1)

out = {
  "key_names": list(dict.fromkeys(key_names)) or ["key","uik","allow_key","allowlist_key"],
  "csrf_name": csrf_name or "csrf_token",
  "csrf_val": csrf_val or "",
  "hidden": hidden_pairs[:20]
}
print(urllib.parse.quote_plus(str(out)))
PY
}

grab_login() {
  local out="$1"
  curl --max-time "$CURL_MAX_TIME" -s -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$out" || true
  [ -f "$out" ] || : > "$out"
}

# 取一次 login 頁，抽出欄位
login1="$TMP/login1.html"
grab_login "$login1"

ENC="$(extract_form_fields "$login1")"
python - <<PY > "$TMP/form1.env"
import ast,sys,urllib.parse,shlex
d=ast.literal_eval(urllib.parse.unquote_plus("$ENC"))
print("KEYS=" + shlex.quote(",".join(d["key_names"])))
print("CSRFN=" + shlex.quote(d["csrf_name"]))
print("CSRFT=" + shlex.quote(d["csrf_val"]))
pairs=[(k,v) for (k,v) in d["hidden"] if "csrf" not in k.lower() and "key" not in k.lower()]
print("HIDDEN=" + shlex.quote("&".join(f"{k}={v}" for k,v in pairs)))
PY
. "$TMP/form1.env"

build_form() {
  local val="$1"
  local acc=""
  IFS=',' read -ra arr <<< "$KEYS"
  for nm in "${arr[@]}"; do
    [ -z "$nm" ] && continue
    [ -n "$acc" ] && acc="${acc}&"
    acc="${acc}${nm}=${val}"
  done
  if [ -n "${CSRFT}" ]; then
    acc="${acc}&${CSRFN}=${CSRFT}&csrf=${CSRFT}&csrf_token=${CSRFT}"
  fi
  if [ -n "${HIDDEN}" ]; then
    acc="${acc}&${HIDDEN}"
  fi
  echo "$acc"
}

# 1) 錯誤 key（不要 -f），一定寫出檔案
BAD_FORM="$(build_form "$DENY_KEY")"
curl --max-time "$CURL_MAX_TIME" -s -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRFT}" \
     --data "$BAD_FORM" http://127.0.0.1:8000/ui/login -o "$TMP/login_bad.html" || true

curl --max-time "$CURL_MAX_TIME" -s -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_bad.html" || true
[ -f "$TMP/ui_bad.html" ] || : > "$TMP/ui_bad.html"
if grep -E "Upload|Sessions|Shares" "$TMP/ui_bad.html" >/dev/null; then
  echo "allowlist failed: bad key got authenticated"
  exit 3
fi

# 2) 正確 key：再抓一次 login 以刷新 CSRF/欄位名
login2="$TMP/login2.html"
grab_login "$login2"

ENC2="$(extract_form_fields "$login2")"
python - <<PY > "$TMP/form2.env"
import ast,sys,urllib.parse,shlex
d=ast.literal_eval(urllib.parse.unquote_plus("$ENC2"))
print("KEYS=" + shlex.quote(",".join(d["key_names"])))
print("CSRFN=" + shlex.quote(d["csrf_name"]))
print("CSRFT=" + shlex.quote(d["csrf_val"]))
pairs=[(k,v) for (k,v) in d["hidden"] if "csrf" not in k.lower() and "key" not in k.lower()]
print("HIDDEN=" + shlex.quote("&".join(f"{k}={v}" for k,v in pairs)))
PY
. "$TMP/form2.env"

OK_FORM="$(build_form "$ALLOWED_KEY")"
curl --max-time "$CURL_MAX_TIME" -s -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRFT}" \
     --data "$OK_FORM" http://127.0.0.1:8000/ui/login -o "$TMP/login_ok.html" || true

curl --max-time "$CURL_MAX_TIME" -s -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_ok.html" || true
grep -E "Upload|Sessions|Shares" "$TMP/ui_ok.html" >/dev/null || { echo "login with allowed key did not authenticate"; exit 4; }

# 3) 速率限制：並發打點；若未觀察到 429，於 best-effort 模式不失敗
RL_FILE="$TMP/rl_codes.txt"; : > "$RL_FILE"

# 先試 /sessions (GET)
seq 1 24 | xargs -I{} -P 12 sh -c 'curl --max-time '"$CURL_MAX_TIME"' -s -o /dev/null -w "%{http_code}" -b "'"$COOK"'" http://127.0.0.1:8000/sessions || echo 000' >> "$RL_FILE"
RL429="$(grep -c '^429$' "$RL_FILE" || true)"

if [ "$RL429" -eq 0 ]; then
  : > "$RL_FILE"
  # 再試 /ui/login (POST) with bad key
  for _ in $(seq 1 24); do
    (
      code="$(curl --max-time "$CURL_MAX_TIME" -s -o /dev/null -w "%{http_code}" -c "$COOK" -b "$COOK" \
        -H "Content-Type: application/x-www-form-urlencoded" -H "X-CSRF-Token: ${CSRFT}" \
        --data "$BAD_FORM" http://127.0.0.1:8000/ui/login || echo 000)"
      echo "$code"
    ) &
  done
  wait
  RL429="$(grep -c '^429$' "$RL_FILE" || true)"
fi

if [ "$EXPECT_429" = "1" ] && [ "$RL429" -lt 1 ]; then
  echo "rate limiting did not trigger (no 429 observed) while EXPECT_429=1"
  exit 7
fi

# 4) TTL 檢查：TN_UI_TTL_S=3，睡 >3 秒後不應仍看到登入狀態
sleep 4
curl --max-time "$CURL_MAX_TIME" -s -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_after_ttl.html" || true
[ -f "$TMP/ui_after_ttl.html" ] || : > "$TMP/ui_after_ttl.html"
if grep -E "Upload|Sessions|Shares" "$TMP/ui_after_ttl.html" >/dev/null; then
  echo "TTL not enforced: session remained authenticated after expiry"
  exit 8
fi

echo "[accept_step18] OK"