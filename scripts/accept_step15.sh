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

# extract session_id from JSON safely
python - "$UPLOAD_JSON" <<'PY'
import sys, json
p=sys.argv[1]
data=open(p,"rb").read().decode("utf-8","ignore")
j=json.loads(data)
sid=j.get("session_id") or j.get("id") or j.get("sessionId")
assert isinstance(sid,str) and len(sid)>0, "missing session_id"
print(sid)
PY
SID="$(python - "$UPLOAD_JSON" <<'PY'
import sys, json
p=sys.argv[1]
data=open(p,"rb").read().decode("utf-8","ignore")
j=json.loads(data)
sid=j.get("session_id") or j.get("id") or j.get("sessionId")
assert isinstance(sid,str) and len(sid)>0
print(sid)
PY
)"

# wait until the session is queryable to avoid 404 race
wait_for_session() {
  local sid="$1"
  # try summary endpoint first
  for _ in $(seq 1 60); do
    code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/session/${sid}/summary")" || code=000
    if [ "$code" = "200" ]; then return 0; fi
    # fallback: check it appears in /sessions listing
    if curl -sf "http://127.0.0.1:8000/sessions" | grep -q "\"${sid}\""; then return 0; fi
    sleep 0.5
  done
  echo "Session ${sid} not visible after wait"
  return 1
}
wait_for_session "$SID"

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
