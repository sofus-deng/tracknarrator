#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; cd "$ROOT"
shopt -s nullglob
STEPS=(scripts/accept_step*.sh)
if [ ${#STEPS[@]} -eq 0 ]; then echo "No acceptance scripts found"; exit 0; fi
for s in "${STEPS[@]}"; do echo "::group::$(basename "$s")"; bash "$s"; echo "::endgroup::"; done
echo "[accept_all] OK"