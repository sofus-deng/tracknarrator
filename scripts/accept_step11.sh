#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 11: storage + upload smoke test (delegated to step 15)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Delegate to the already-stable upload/share acceptance script.
"${SCRIPT_DIR}/accept_step15.sh"

echo "[accept_step11] OK (delegated to accept_step15.sh)"