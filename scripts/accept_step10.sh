#!/usr/bin/env bash
set -euo pipefail
echo "Running acceptance step 10: share tokens + public shared summary"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# repo-local temp to avoid /tmp quirks on runners
mkdir -p "$ROOT/.accept"
TMP="$(mktemp -d "$ROOT/.accept/step10.XXXXXX")"
LOG="$TMP/server.log"

CURL_MAX_TIME="${CURL_MAX_TIME:-1}"
READY_DEADLINE="${READY_DEADLINE:-20}"

# sensible defaults for Step 10
export SHARE_SECRET="${SHARE_SECRET:-ci-share-secret}"
export TN_UI_KEY="${TN_UI_KEY:-ci-accept}"      # harmless for API; avoids UI guard side effects
export TN_UI_KEYS="${TN_UI_KEYS:-ci-accept}"

start_server() {
  if command -v uv >/dev/null 2>&1; then
    ( cd backend && \
      SHARE_SECRET="$SHARE_SECRET" TN_UI_KEY="$TN_UI_KEY" TN_UI_KEYS="$TN_UI_KEYS" \
      uv run uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) >"$LOG" 2>&1 &
  else
    ( cd backend && \
      SHARE_SECRET="$SHARE_SECRET" TN_UI_KEY="$TN_UI_KEY" TN_UI_KEYS="$TN_UI_KEYS" \
      python -m uvicorn tracknarrator.main:app --host 127.0.0.1 --port 8000 ) >"$LOG" 2>&1 &
  fi
  echo $! > "$TMP/pid"
}

cleanup() {
  echo "--- tail of server log (accept_step10) ---"
  tail -n 120 "$LOG" || true
  if [ -f "$TMP/pid" ] && ps -p "$(cat "$TMP/pid")" >/dev/null 2>&1; then
    kill "$(cat "$TMP/pid")" >/dev/null 2>&1 || true
    wait "$(cat "$TMP/pid")" 2>/dev/null || true
  fi
  rm -rf "$TMP" || true
}
trap cleanup EXIT

start_server

# wait until server ready
ready=0
for _ in $(seq 1 $READY_DEADLINE); do
  if curl -s --max-time "$CURL_MAX_TIME" http://127.0.0.1:8000/health >/dev/null 2>&1 \
     || curl -s --max-time "$CURL_MAX_TIME" http://127.0.0.1:8000/docs   >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo "Server not ready"; exit 1; }

# create a tiny GPX to ensure we have a session without relying on fixtures
cat > "$TMP/ci.gpx" <<'GPX'
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="tn-ci" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>ci</name><trkseg>
    <trkpt lat="25.0000" lon="121.0000"><time>2020-01-01T00:00:00Z</time></trkpt>
    <trkpt lat="25.0001" lon="121.0001"><time>2020-01-01T00:01:00Z</time></trkpt>
    <trkpt lat="25.0002" lon="121.0002"><time>2020-01-01T00:02:00Z</time></trkpt>
  </trkseg></trk>
</gpx>
GPX

# upload GPX (multipart). Do NOT force MIME type; let server infer from filename.
UPCODE="$(curl -sS -o "$TMP/upload.json" -w "%{http_code}" --max-time 5 \
  -F "file=@$TMP/ci.gpx" http://127.0.0.1:8000/upload || true)"
# fallback: some servers accept raw binary with ?filename=
if [ "$UPCODE" != "200" ]; then
  UPCODE="$(curl -sS -o "$TMP/upload2.json" -w "%{http_code}" --max-time 5 \
    -H "Content-Type: application/octet-stream" --data-binary "@$TMP/ci.gpx" \
    "http://127.0.0.1:8000/upload?filename=ci.gpx" || true)"
fi

# resolve session id robustly from /sessions (works regardless of upload response shape)
curl -sS --max-time 5 http://127.0.0.1:8000/sessions -o "$TMP/sessions.json" >/dev/null
SID="$(
python - <<'PY' "$TMP/sessions.json"
import sys, json
from pathlib import Path
raw = Path(sys.argv[1]).read_text(encoding="utf-8") or "[]"
try:
  data=json.loads(raw)
except Exception:
  data=[]
seq=[]
if isinstance(data, dict):
  for k in ("items","sessions","data","results"):
    v=data.get(k)
    if isinstance(v, list):
      seq=v; break
elif isinstance(data, list):
  seq=data
cands=[x.get("id") for x in seq if isinstance(x, dict) and x.get("id")]
# prefer latest gpx_* id
gpx=[c for c in cands if str(c).startswith("gpx_")]
sid=(gpx[-1] if gpx else (cands[-1] if cands else None))
print(sid or "")
PY
)"
[ -n "$SID" ] || { echo "failed to resolve session id"; exit 2; }
echo "session: $SID"

# wait summary ready (handle transient 404)
ok=0
for _ in $(seq 1 10); do
  code="$(curl -s -o "$TMP/summary.json" -w "%{http_code}" --max-time 2 "http://127.0.0.1:8000/session/$SID/summary")" || true
  if [ "$code" = "200" ]; then ok=1; break; fi
  sleep 0.5
done
[ "$ok" -eq 1 ] || { echo "summary not ready for $SID"; exit 3; }

# create share token (ttl 120s)
code="$(curl -s -o "$TMP/share.json" -w "%{http_code}" --max-time 2 -X POST \
  "http://127.0.0.1:8000/share/$SID?ttl_s=120")" || true
[ "$code" = "200" ] || { echo "share create failed ($code)"; exit 4; }

TOKEN="$(
python - <<'PY' "$TMP/share.json"
import sys,json,re
raw=open(sys.argv[1],'rb').read().decode('utf-8','ignore').strip()
tok=""
try:
  obj=json.loads(raw)
  tok=obj.get('token') or obj.get('data') or obj.get('value') or ""
except Exception:
  pass
if not tok:
  m=re.search(r'([A-Za-z0-9_\-\.]{20,})', raw)
  if m: tok=m.group(1)
print(tok)
PY
)"
[ -n "$TOKEN" ] || { echo "token parse failed"; exit 5; }
echo "token: ${TOKEN:0:20}..."

# fetch shared summary
code="$(curl -s -o "$TMP/shared.json" -w "%{http_code}" --max-time 2 \
  "http://127.0.0.1:8000/shared/$TOKEN/summary")" || true
[ "$code" = "200" ] || { echo "shared summary failed ($code)"; exit 6; }

# basic shape check
python - <<'PY' "$TMP/shared.json"
import sys,json
j=json.load(open(sys.argv[1]))
assert "events" in j and "cards" in j and "sparklines" in j
PY

# revoke then verify access denied
curl -s -o /dev/null --max-time 2 -X DELETE "http://127.0.0.1:8000/share/$TOKEN" -w "" >/dev/null
code="$(curl -s -o "$TMP/after.json" -w "%{http_code}" --max-time 2 \
  "http://127.0.0.1:8000/shared/$TOKEN/summary")" || true
[ "$code" != "200" ] || { echo "revocation not enforced"; exit 7; }

echo "[accept_step10] OK"