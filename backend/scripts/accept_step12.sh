#!/usr/bin/env bash
set -euo pipefail
# start server
(make dev > /dev/null 2>&1 &) ; DEV_PID=$!
cleanup(){ kill "$DEV_PID" >/dev/null 2>&1 || true; wait "$DEV_PID" 2>/dev/null || true; }
trap cleanup EXIT
for i in {1..60}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 0.5; done
# seed
curl -sS -X POST http://127.0.0.1:8000/dev/seed -H 'Content-Type: application/json' --data-binary @backend/fixtures/bundle_sample_barber.json >/dev/null
# viz endpoint contract
curl -sS http://127.0.0.1:8000/session/barber/viz | grep -E '"lap_delta_series"|"section_box"' >/dev/null
echo "[accept_step12] OK"