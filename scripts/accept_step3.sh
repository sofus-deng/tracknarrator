#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE:-http://localhost:8000}

# ---- tools ----
if command -v md5sum >/dev/null 2>&1; then md5hash(){ md5sum | awk '{print $1}'; }
elif command -v md5 >/dev/null 2>&1; then md5hash(){ md5 -q; }
else echo "Need md5sum or md5"; exit 2; fi
jqsort(){ jq -S 'del(.session.start_ts,.session.end_ts)'; }

# ---- samples: 如果沒指定 TRD/RC/MY/WX，就臨時產生最小樣本 ----
TMPDIR="$(mktemp -d)"
cleanup(){ rm -rf "$TMPDIR"; }
trap cleanup EXIT

: "${TRD:=}"; : "${RC:=}"; : "${MY:=}"; : "${WX:=}"

if [[ -z "${TRD}${RC}${MY}${WX}" ]]; then
  # TRD long-CSV (ts_ms,name,value)
  cat > "$TMPDIR/trd.csv" << 'CSV'
ts_ms,name,value
0,speed,102
0,aps,12
0,gear,3
0,accx_can,0.05
0,accy_can,0.02
0,Steering_Angle,5
0,VBOX_Lat_Min,33.5200
0,VBOX_Long_Minutes,-86.6200
50,speed,105
50,aps,18
50,gear,3
CSV
  TRD="$TMPDIR/trd.csv"

  # RaceChrono CSV
  cat > "$TMPDIR/rc.csv" << 'CSV'
Time (s),Speed (km/h),Latitude,Longitude,Throttle pos (%),Brake pos (%)
0.0,98,33.52010,-86.62010,10,0
0.1,99,33.52015,-86.62015,12,5
0.2,97,33.52020,-86.62020,11,3
CSV
  RC="$TMPDIR/rc.csv"

  # MYLAPS sections
  cat > "$TMPDIR/mylaps.csv" << 'CSV'
Lap,IM1a_TIME,IM1_TIME,IM2a_TIME,IM2_TIME,IM3a_TIME,FL_TIME
1,12000,23000,34000,45000,56000,70000
2,11000,22000,33000,44000,55000,68000
CSV
  MY="$TMPDIR/mylaps.csv"

  # Weather (semicolon; seconds -> importer 會轉 ms)
  cat > "$TMPDIR/wx.csv" << 'CSV'
ts;temp_c;humidity_pct
0;25;60
1;25;61
CSV
  WX="$TMPDIR/wx.csv"
fi

for f in "$TRD" "$RC" "$MY" "$WX"; do
  [[ -s "$f" ]] || { echo "Missing sample file: $f"; exit 2; }
done

echo "Using samples:"
printf "  TRD: %s\n  RC:  %s\n  MY:  %s\n  WX:  %s\n" "$TRD" "$RC" "$MY" "$WX"

S1="acc-$(date +%s)-A"
S2="acc-$(date +%s)-B"

echo "== health"
curl -fsS "$BASE/health" >/dev/null

echo "== RC ingest & warning check"
RC_RES=$(curl -fsS -F "file=@$RC" "$BASE/ingest/racechrono?session_id=$S1")
echo "$RC_RES" | jq -e '.warnings[]? | contains("racechrono: brake_pos_pct")' >/dev/null \
  && echo "OK: RC warning present" || echo "NOTE: RC warning not found (file may not include brake col)"

echo "== Order A: TRD -> MY -> WX"
curl -fsS -F "file=@$TRD" "$BASE/ingest/trd-long?session_id=$S1" >/dev/null
curl -fsS -F "file=@$MY"  "$BASE/ingest/mylaps-sections?session_id=$S1" >/dev/null
curl -fsS -F "file=@$WX"  "$BASE/ingest/weather?session_id=$S1" >/dev/null
H1=$(curl -fsS "$BASE/session/$S1/bundle" | jqsort | md5hash)

echo "== Order B: RC -> TRD -> WX -> MY"
curl -fsS -F "file=@$RC" "$BASE/ingest/racechrono?session_id=$S2" >/dev/null
curl -fsS -F "file=@$TRD" "$BASE/ingest/trd-long?session_id=$S2" >/dev/null
curl -fsS -F "file=@$WX" "$BASE/ingest/weather?session_id=$S2" >/dev/null
curl -fsS -F "file=@$MY" "$BASE/ingest/mylaps-sections?session_id=$S2" >/dev/null
H2=$(curl -fsS "$BASE/session/$S2/bundle" | jqsort | md5hash)

echo "== Compare hashes"
[[ "$H1" == "$H2" ]] && echo "OK: deterministic bundle ($H1)" \
  || { echo "FAIL: bundle hash differs: $H1 vs $H2"; exit 1; }

echo "== Idempotency check on TRD"
BEFORE=$(curl -fsS "$BASE/session/$S1/bundle" | jq '.telemetry|length')
curl -fsS -F "file=@$TRD" "$BASE/ingest/trd-long?session_id=$S1" >/dev/null
AFTER=$(curl -fsS "$BASE/session/$S1/bundle" | jq '.telemetry|length')
[[ "$BEFORE" == "$AFTER" ]] && echo "OK: idempotent telemetry count ($BEFORE)" \
  || { echo "FAIL: telemetry count changed ($BEFORE -> $AFTER)"; exit 1; }

echo "ALL GREEN ✅"
