#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; cd "$ROOT"
echo "[ci_local] pytest"
if command -v uv >/dev/null 2>&1; then (cd backend && uv run pytest -q); else (cd backend && python -m pytest -q); fi
echo "[ci_local] acceptance suite"; bash scripts/accept_all.sh
echo "[ci_local] pages sync"; bash scripts/sync_demo_to_docs.sh
echo "[ci_local] OK"