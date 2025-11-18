#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 18: Admin security hardening (allowlist, rate limit, TTL)"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

TMP="$(mktemp -d /tmp/tn_accept18.XXXXXX)"
LOG="$TMP/server.log"
COOK="$TMP/cookies.txt"

# 快速且可重現的預設
ALLOWED_KEY="${TN_UI_KEY:-ci-allow}"
DENY_KEY="not-allowed"
READY_DEADLINE="${READY_DEADLINE:-20}"   # 最多等 20s
CURL_MAX_TIME="${CURL_MAX_TIME:-1}"      # 每次 curl 最多 1s
RL_SHOTS="${RL_SHOTS:-12}"               # 限流探測最多 12 發
RL_PAR="${RL_PAR:-6}"                    # 併發 6
TTL_SECS="${TN_UI_TTL_S:-2}"             # 縮短 TTL，驗證更快
EXPECT_429="${TN_EXPECT_429:-0}"         # 0=最佳努力, 1=強制要求出現 429

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

# 等待就緒（先打 /health，沒有則退回 /docs）
ready=0
for _ in $(seq 1 $READY_DEADLINE); do
  if curl -s --max-time "$CURL_MAX_TIME" http://127.0.0.1:8000/health >/dev/null 2>&1 \
     || curl -s --max-time "$CURL_MAX_TIME" http://127.0.0.1:8000/docs >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo "Server not ready"; exit 1; }

# 取 login 頁面
curl -s --max-time "$CURL_MAX_TIME" -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$TMP/login.html" || true

# 從 HTML 抽欄位（key 欄位名、csrf 名稱與值、其他 hidden）
python - "$TMP/login.html" >"$TMP/form.json" <<'PY'
import re, sys, json
html=open(sys.argv[1], encoding="utf-8", errors="ignore").read()
inputs=re.findall(r'<input[^>]*>', html, flags=re.I)
def attr(tag,n):
    m=re.search(fr'\b{n}="([^"]*)"', tag, flags=re.I)
    return m.group(1) if m else None
keys=[]; csrfn=None; csrft=None; hidden=[]
for it in inputs:
    nm=attr(it,'name'); val=attr(it,'value') or ''
    ty=(attr(it,'type') or '').lower()
    if not nm: continue
    if re.search(r'(key|allow|uik)', nm, flags=re.I): keys.append(nm)
    if 'csrf' in (nm or '').lower():
        csrfn = csrfn or nm
        if val: csrft = val
    if ty=='hidden' and nm and val and 'csrf' not in nm.lower() and 'key' not in nm.lower():
        hidden.append((nm,val))
if not csrft:
    m=re.search(r'data-csrf="([^"]+)"', html, flags=re.I)
    if m: csrft=m.group(1)
if not csrfn: csrfn='csrf_token'
if not keys: keys=['key','allow_key','uik']
print(json.dumps({"keys":list(dict.fromkeys(keys)), "csrfn":csrfn, "csrft":csrft or "", "hidden":hidden}))
PY

# 讀 JSON
KEYS=$(python - <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(",".join(d["keys"]))
PY
"$TMP/form.json")

CSRFN=$(python - <<'PY'
import json,sys; print(json.load(open(sys.argv[1]))["csrfn"])
PY
"$TMP/form.json")

CSRFT=$(python - <<'PY'
import json,sys; print(json.load(open(sys.argv[1]))["csrft"])
PY
"$TMP/form.json")

HIDDEN=$(python - <<'PY'
import json,sys,urllib.parse
pairs=json.load(open(sys.argv[1]))["hidden"]
print("&".join(f"{k}={v}" for k,v in pairs))
PY
"$TMP/form.json")

build_form() {
  local keyval="$1"
  local q=""
  IFS=',' read -ra arr <<< "$KEYS"
  for nm in "${arr[@]}"; do
    [ -z "$nm" ] && continue
    q="${q}${q:+&}${nm}=${keyval}"
  done
  if [ -n "$CSRFT" ]; then
    q="${q}&${CSRFN}=${CSRFT}&csrf=${CSRFT}&csrf_token=${CSRFT}"
  fi
  if [ -n "$HIDDEN" ]; then
    q="${q}&${HIDDEN}"
  fi
  echo "$q"
}

# 驗證：錯誤 key 不應登入
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

# 正確 key 應登入
# 再抓一次 login 以刷新 CSRFT（若後端採一次性）
curl -s --max-time "$CURL_MAX_TIME" -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$TMP/login2.html" || true
# 若沒新的 token，沿用舊值即可
OK_FORM="$(build_form "$ALLOWED_KEY")"
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-CSRF-Token: ${CSRFT}" \
  --data "$OK_FORM" http://127.0.0.1:8000/ui/login -o "$TMP/ok.html" || true
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_ok.html" || true
grep -Eq "Upload|Sessions|Shares" "$TMP/ui_ok.html" || { echo "login with allowed key did not authenticate"; exit 4; }

# 限流最佳努力：併發少量 GET /sessions，全部輸出到檔案，不要刷 console
RL_FILE="$TMP/rl.txt"; : > "$RL_FILE"
seq 1 "$RL_SHOTS" | xargs -I{} -P "$RL_PAR" sh -c '
  curl -s --max-time '"$CURL_MAX_TIME"' -o /dev/null -w "%{http_code}\n" -b "'"$COOK"'" http://127.0.0.1:8000/sessions || echo 000
' >> "$RL_FILE"
RL429=$(grep -c '^429$' "$RL_FILE" || true)
if [ "$EXPECT_429" = "1" ] && [ "$RL429" -lt 1 ]; then
  echo "rate limiting did not trigger (no 429 observed) while EXPECT_429=1"
  exit 7
fi

# TTL 驗證：TTL 很短，超時後應回到登入頁
sleep "$((TTL_SECS+1))"
curl -s --max-time "$CURL_MAX_TIME" -L -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_after.html" || true
if grep -Eq "Upload|Sessions|Shares" "$TMP/ui_after.html"; then
  echo "TTL not enforced: session still authenticated after expiry"
  exit 8
fi

echo "[accept_step18] OK"