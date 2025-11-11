#!/usr/bin/env bash
set -euo pipefail
cd backend && uv run pytest -q && cd ..
./scripts/accept_step7.sh
./scripts/accept_step8.sh
./scripts/make_submission_zip.sh
# verify zip exists and is non-empty
ls -1 TrackNarrator_submission_v*.zip | head -n1 | xargs -r test -s
echo "[accept_step9] OK"