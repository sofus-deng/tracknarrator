#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

TIMEOUT_PER_STEP="${TIMEOUT_PER_STEP:-240s}"  # 4 minutes per step default
STEPS=(
  "accept_step14.sh"
  "accept_step15.sh"
  "accept_step17.sh"
  "accept_step18.sh"
)

cleanup_ports() {
  # Kill uvicorn on :8000 if any; ignore errors
  if command -v lsof >/dev/null 2>&1; then
    PIDS="$(lsof -t -i:8000 || true)"
    [ -n "$PIDS" ] && kill $PIDS >/dev/null 2>&1 || true
  fi
  pkill -f "uvicorn .*8000" >/dev/null 2>&1 || true
  pkill -f "tracknarrator.main:app" >/dev/null 2>&1 || true
  rm -rf /tmp/tn_accept* || true
}

run_step() {
  local s="$1"
  echo "$s"
  if command -v timeout >/dev/null 2>&1; then
    timeout "$TIMEOUT_PER_STEP" bash -lc "./scripts/$s"
  else
    # Fallback without timeout
    bash -lc "./scripts/$s"
  fi
  cleanup_ports
}

for s in "${STEPS[@]}"; do
  run_step "$s"
done
echo "[accept_all] OK"