#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# run demo to generate export artifacts
bash "$ROOT/demo/run_demo.sh"
# copy key demo outputs into docs/data for static viewer
mkdir -p "$ROOT/docs/data"
cp -f "$ROOT/demo/export/summary.json" "$ROOT/docs/data/summary.json"
# optional extras if present
for f in coach_tips.json events.json cards.json sparklines.json kpis.json; do
  if [[ -f "$ROOT/demo/export/$f" ]]; then
    cp -f "$ROOT/demo/export/$f" "$ROOT/docs/data/$f"
  fi
done
# if backend is running in demo script, try to read coach score from export dir if present; otherwise skip silently.
if [[ -f "$ROOT/demo/export/coach_score.json" ]]; then
  cp -f "$ROOT/demo/export/coach_score.json" "$ROOT/docs/data/coach_score.json"
fi
echo "[sync_demo_to_docs] OK"