#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 13: share governance (delegated to backend/scripts/accept_step13.sh)"

# Resolve repo root based on this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Run the original backend acceptance script from inside backend/
(
  cd "${REPO_ROOT}/backend"
  ./scripts/accept_step13.sh
)

echo "[accept_step13] OK (delegated to backend/scripts/accept_step13.sh)"