#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 15: web uploader + share API check"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

LOG="/tmp/dev_step15.log"
TMP="/tmp/tn_accept15"
mkdir -p "$TMP"

start_server() {
  if command -v uv >/dev/null 2>&1; then
    echo "[server] uv run uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_CORS_ORIGINS="*" TN_COOKIE_SECURE="0" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  else
    echo "[server] python -m uvicorn (backend/)"
    ( cd backend && TN_UI_KEY="${TN_UI_KEY:-ci-demo}" TN_UI_KEYS="${TN_UI_KEYS:-ci-demo}" \
      TN_CSRF_SECRET="${TN_CSRF_SECRET:-ci-csrf}" TN_CORS_ORIGINS="*" TN_COOKIE_SECURE="0" \
      python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) > "$LOG" 2>&1 &
  fi
  echo $! > "$TMP/pid"
}

cleanup() {
  echo "--- tail of server log (accept_step15) ---"
  tail -n 200 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
}
trap cleanup EXIT

start_server

# wait up to 90s
for _ in $(seq 1 180); do
  if curl -sf http://127.0.0.1:8000/docs >/dev/null 2>&1; then break; fi
  sleep 0.5
done
curl -sf http://127.0.0.1:8000/docs >/dev/null || { echo "Server not ready"; exit 1; }

# create a minimal GPX to exercise /upload
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

UPLOAD_JSON="$TMP/upload.json"
if ! curl -fsS --retry 5 --retry-all-errors -X POST \
     -F "file=@${GPX}" "http://127.0.0.1:8000/upload" -o "$UPLOAD_JSON"; then
  echo "Upload API failed"; exit 2
fi
[ -s "$UPLOAD_JSON" ] || { echo "Empty upload response"; exit 2; }

# derive the real persisted session_id from /sessions (some importers emit placeholder IDs)
get_latest_sid() {
  python - <<'PY'
import json,sys,urllib.request,time
def pick_id(item):
    if isinstance(item,str): return item
    if isinstance(item,dict):
        return item.get("id") or item.get("session_id") or item.get("sid")
    return None
url="http://127.0.0.1:8000/sessions"
for _ in range(120):  # up to ~60s
    try:
        raw=urllib.request.urlopen(url,timeout=2).read().decode("utf-8","ignore")
        j=json.loads(raw)
        arr = j.get("sessions") if isinstance(j,dict) else j
        if isinstance(arr,list) and arr:
            sid = pick_id(arr[0])
            if sid:
                print(sid)
                sys.exit(0)
    except Exception:
        pass
    time.sleep(0.5)
print("")
PY
}
SID="$(get_latest_sid)"
[ -n "${SID}" ] || { echo "No session available in /sessions"; exit 2; }

# hard check summary 200 before sharing
for _ in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/session/${SID}/summary")" || code=000
  [ "$code" = "200" ] && break
  sleep 0.5
done
[ "$code" = "200" ] || { echo "summary not ready for ${SID}"; exit 2; }

# create share token (now that session exists)
SHARE_JSON="$TMP/share.json"
curl -fsS --retry 5 --retry-all-errors -X POST -H 'Content-Type: application/json' -d '{}' \
  "http://127.0.0.1:8000/share/${SID}" -o "$SHARE_JSON"

TOKEN="$(python - "$SHARE_JSON" <<'PY'
import sys,json
j=json.load(open(sys.argv[1],"r",encoding="utf-8"))
tok=j.get("token") or j.get("share_token")
assert isinstance(tok,str) and len(tok)>0
print(tok)
PY
)"

# fetch shared summary
SUM_JSON="$TMP/summary.json"
curl -fsS "http://127.0.0.1:8000/shared/${TOKEN}/summary" -o "$SUM_JSON"
python - "$SUM_JSON" <<'PY'
import sys,json
j=json.load(open(sys.argv[1],"r",encoding="utf-8"))
for k in ("events","cards","sparklines"):
    assert k in j, f"missing {k}"
print("shared summary OK")
PY

echo "[accept_step15] OK"
