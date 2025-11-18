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
# up to 30 tries x 0.5s = 15s, accommodate slower CI nodes
SUMMARY_WAIT_TRIES="${SUMMARY_WAIT_TRIES:-30}"

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

# discover upload contract from openapi
curl -sS --max-time 4 "http://127.0.0.1:8000/openapi.json" -o "$TMP/openapi.json" || true
UPLOAD_HINTS="$(python - "$TMP/openapi.json" <<'PY'
import sys,json
try:
  doc=json.load(open(sys.argv[1]))
except Exception:
  doc={}
paths=doc.get("paths",{})
schema=None
for p, methods in paths.items():
  if p.endswith("/upload") or p=="/upload":
    for m, spec in methods.items():
      rb=(spec or {}).get("requestBody",{})
      content=(rb or {}).get("content",{})
      if "multipart/form-data" in content:
        schema=content["multipart/form-data"].get("schema",{})
        break
    if schema: break
required=set(schema.get("required",[])) if schema else set()
props=(schema or {}).get("properties",{}) if schema else {}
# We will default file field to 'file' if exists; add any other required fields with defaults.
hints=[]
if props:
  if "file" in props:
    hints.append("file")
  for k in required:
    if k=="file": continue
    hints.append(k)
print(",".join(hints))
PY
)"

# create a valid GPX with time/lat/lon so importer won't reject
cat > "$TMP/ci.gpx" <<'GPX'
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="tn-ci" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>ci</name><trkseg>
    <trkpt lat="25.0330" lon="121.5654"><ele>10.0</ele><time>2020-01-01T00:00:00Z</time></trkpt>
    <trkpt lat="25.0331" lon="121.5655"><ele>10.2</ele><time>2020-01-01T00:00:01Z</time></trkpt>
    <trkpt lat="25.0332" lon="121.5657"><ele>10.4</ele><time>2020-01-01T00:00:02Z</time></trkpt>
    <trkpt lat="25.0333" lon="121.5659"><ele>10.6</ele><time>2020-01-01T00:00:03Z</time></trkpt>
    <trkpt lat="25.0334" lon="121.5661"><ele>10.8</ele><time>2020-01-01T00:00:04Z</time></trkpt>
    <trkpt lat="25.0335" lon="121.5663"><ele>11.0</ele><time>2020-01-01T00:00:05Z</time></trkpt>
    <trkpt lat="25.0336" lon="121.5665"><ele>11.1</ele><time>2020-01-01T00:00:06Z</time></trkpt>
    <trkpt lat="25.0337" lon="121.5667"><ele>11.2</ele><time>2020-01-01T00:00:07Z</time></trkpt>
  </trkseg></trk>
</gpx>
GPX

# upload GPX (multipart) according to openapi hints
UPLOAD_URL="http://127.0.0.1:8000/upload"
FORM_ARGS=(-F "file=@$TMP/ci.gpx")
if [ -n "$UPLOAD_HINTS" ]; then
  IFS=',' read -ra H <<< "$UPLOAD_HINTS"
  found_file=0
  for k in "${H[@]}"; do
    [ -z "$k" ] && continue
    if [ "$k" = "file" ]; then found_file=1; continue; fi
    # best-effort defaults: kind=gpx / source=accept / filename=ci.gpx
    case "$k" in
      kind) FORM_ARGS+=(-F "kind=gpx");;
      source) FORM_ARGS+=(-F "source=accept");;
      filename) FORM_ARGS+=(-F "filename=ci.gpx");;
      *) FORM_ARGS+=(-F "${k}=ci");;
    esac
  done
  if [ "$found_file" -eq 0 ]; then
    # some schemas might use a different field name for file - try 'upload'
    FORM_ARGS=(-F "upload=@$TMP/ci.gpx" "${FORM_ARGS[@]}")
  fi
fi
# also proactively add kind=gpx if not already included
add_kind=1
for a in "${FORM_ARGS[@]}"; do
  case "$a" in *"kind="*) add_kind=0;; esac
done
[ $add_kind -eq 1 ] && FORM_ARGS+=(-F "kind=gpx")
UPCODE="$(curl -sS -o "$TMP/upload.json" -w "%{http_code}" --max-time 8 \
  "${FORM_ARGS[@]}" "$UPLOAD_URL" || true)"
if [ "$UPCODE" != "200" ]; then
  echo "[upload] HTTP $UPCODE"; echo "--- body ---"; cat "$TMP/upload.json" || true; echo "------------"
  # fallback: raw binary as last resort
  UPCODE="$(curl -sS -o "$TMP/upload2.json" -w "%{http_code}" --max-time 6 \
    -H "Content-Type: application/octet-stream" --data-binary "@$TMP/ci.gpx" \
    "$UPLOAD_URL?filename=ci.gpx" || true)"
  if [ "$UPCODE" != "200" ]; then
    echo "[upload fallback] HTTP $UPCODE"; echo "--- body2 ---"; cat "$TMP/upload2.json" || true; echo "-------------"
  fi
fi

# try resolve session id from upload response first
SID_FROM_UPLOAD="$(
python - <<'PY' "$TMP/upload.json" "$TMP/upload2.json"
import sys, json, os
sid=None
for p in sys.argv[1:]:
  if not os.path.exists(p): continue
  try:
    data=json.load(open(p))
  except Exception:
    continue
  for k in ("session_id","id","sid","sessionId"):
    if isinstance(data, dict) and data.get(k):
      sid=data[k]; break
  if sid: break
print(sid or "")
PY
)"

# resolve session id robustly from /sessions (works regardless of upload response shape)
curl -sS --max-time 6 http://127.0.0.1:8000/sessions -o "$TMP/sessions.json" >/dev/null
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
[ -n "$SID_FROM_UPLOAD" ] && SID="$SID_FROM_UPLOAD"
[ -n "$SID" ] || { echo "failed to resolve session id"; exit 2; }
echo "session: $SID"

# wait summary ready (handle transient 404)
ok=0
for _ in $(seq 1 $SUMMARY_WAIT_TRIES); do
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