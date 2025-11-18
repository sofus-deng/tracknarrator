#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 12: visualization P1 (delegated to backend/scripts/accept_step12.sh)"

# Resolve repo root based on this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Run the original backend acceptance script from inside backend/
(
  cd "${REPO_ROOT}/backend"
  ./scripts/accept_step12.sh
)

echo "[accept_step12] OK (delegated to backend/scripts/accept_step12.sh)"