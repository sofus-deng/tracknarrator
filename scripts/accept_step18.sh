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

extract_form_fields() {
  local html="$1"
  python - "$html" <<'PY'
import re, sys, urllib.parse
p=sys.argv[1]
with open(p,'r',encoding='utf-8',errors='ignore') as f:
    html=f.read()

# 找出所有 input name/value
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
    # 偵測 key 欄位：name 含 key/uik/allow，或 type=password/text 且 name含key字根
    if re.search(r'(key|uik|allow)', nm, flags=re.I):
        key_names.append(nm)
    elif typ in ('password','text') and re.search(r'key', nm, flags=re.I):
        key_names.append(nm)
    # 偵測 csrf 欄位名
    if re.search(r'^csrf(_token)?$', nm, flags=re.I) or re.search(r'csrf', nm, flags=re.I):
        if not csrf_name:
            csrf_name = nm
        if val:
            csrf_val = val
    # 收集 hidden 欄位以便保守帶回（避免必填）
    if typ == 'hidden' and nm and val:
        hidden_pairs.append((nm, val))

# 也嘗試讀 data-csrf / meta name=csrf
if not csrf_val:
    m=re.search(r'data-csrf="([^"]+)"', html, flags=re.I)
    if m: csrf_val=m.group(1)
if not csrf_val:
    m=re.search(r'<meta[^>]+name="csrf"[^>]+content="([^"]+)"', html, flags=re.I)
    if m: csrf_val=m.group(1)

# 輸出：JSON 一行
out = {
  "key_names": list(dict.fromkeys(key_names)) or ["key","uik","allow_key","allowlist_key"],
  "csrf_name": csrf_name or "csrf_token",
  "csrf_val": csrf_val or "",
  "hidden": hidden_pairs[:20]
}
print(urllib.parse.quote_plus(str(out)))
PY
}

# 先抓 login 頁面
login_html="$TMP/login1.html"
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$login_html"
[ -s "$login_html" ] || { echo "login page empty"; exit 2; }

ENC="$(extract_form_fields "$login_html")"
# 解析回 bash 變數
python - <<PY > "$TMP/form1.env"
import ast,sys,urllib.parse,shlex
d=ast.literal_eval(urllib.parse.unquote_plus("$ENC"))
print("KEYS=" + shlex.quote(",".join(d["key_names"])))
print("CSRFN=" + shlex.quote(d["csrf_name"]))
print("CSRFT=" + shlex.quote(d["csrf_val"]))
# 也把 hidden 轉成 a=b&a=b 的片段（不含 csrf/key）
pairs=[(k,v) for (k,v) in d["hidden"] if "csrf" not in k.lower() and "key" not in k.lower()]
print("HIDDEN=" + shlex.quote("&".join(f"{k}={v}" for k,v in pairs)))
PY
# shellcheck source=/dev/null
. "$TMP/form1.env"

# 建立表單資料字串的函式：帶入 key 值
build_form() {
  local val="$1"
  local acc=""
  IFS=',' read -ra arr <<< "$KEYS"
  for nm in "${arr[@]}"; do
    [ -z "$nm" ] && continue
    if [ -n "$acc" ]; then acc="${acc}&"; fi
    acc="${acc}${nm}=${val}"
  done
  # csrf（同時也會在 header 帶 X-CSRF-Token）
  if [ -n "${CSRFT}" ]; then
    acc="${acc}&${CSRFN}=${CSRFT}&csrf=${CSRFT}&csrf_token=${CSRFT}"
  fi
  # 附上 hidden pairs（避免缺欄位）
  if [ -n "${HIDDEN}" ]; then
    acc="${acc}&${HIDDEN}"
  fi
  echo "$acc"
}

# 1) 錯誤 key：應該無法登入
BAD_FORM="$(build_form "$DENY_KEY")"
curl -fsS -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRFT}" \
     -d "$BAD_FORM" http://127.0.0.1:8000/ui/login -o "$TMP/login_bad.html"

curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_bad.html" || true
if grep -E "Upload|Sessions|Shares" "$TMP/ui_bad.html" >/dev/null; then
  echo "allowlist failed: bad key got authenticated"
  exit 3
fi

# 2) 正確 key：先重新抓 login 與新 CSRF/欄位，避免前一步殘留
login_html2="$TMP/login2.html"
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui/login -o "$login_html2"
ENC2="$(extract_form_fields "$login_html2")"
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
curl -fsS -L -c "$COOK" -b "$COOK" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "X-CSRF-Token: ${CSRFT}" \
     -d "$OK_FORM" http://127.0.0.1:8000/ui/login -o "$TMP/login_ok.html"

curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_ok.html" || true
grep -E "Upload|Sessions|Shares" "$TMP/ui_ok.html" >/dev/null || { echo "login with allowed key did not authenticate"; exit 4; }

# 3) Rate limiting：連打 /sessions 嘗試觸發 429（若沒中，再退而求其次打 /ui/login）
RL429=0
for i in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w "%{http_code}" -b "$COOK" http://127.0.0.1:8000/sessions || echo 000)"
  [ "$code" = "429" ] && RL429=$((RL429+1))
done
if [ "$RL429" -eq 0 ]; then
  for i in $(seq 1 60); do
    code="$(curl -s -o /dev/null -w "%{http_code}" -c "$COOK" -b "$COOK" \
      -H "Content-Type: application/x-www-form-urlencoded" -H "X-CSRF-Token: ${CSRFT}" \
      -d "$BAD_FORM" http://127.0.0.1:8000/ui/login || echo 000)"
    [ "$code" = "429" ] && RL429=$((RL429+1))
  done
fi
[ "$RL429" -ge 1 ] || { echo "rate limiting did not trigger (no 429 observed)"; exit 7; }

# 4) Cookie TTL：等 >3 秒，/ui 應回到未登入狀態
sleep 4
curl -fsS -c "$COOK" -b "$COOK" http://127.0.0.1:8000/ui -o "$TMP/ui_after_ttl.html" || true
if grep -E "Upload|Sessions|Shares" "$TMP/ui_after_ttl.html" >/dev/null; then
  echo "TTL not enforced: session remained authenticated after expiry"
  exit 8
fi

echo "[accept_step18] OK"