#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 1) sync demo to docs (this also runs demo)
bash "$ROOT/scripts/sync_demo_to_docs.sh"
test -s "$ROOT/docs/data/summary.json"
# 2) serve docs locally and probe
pushd "$ROOT/docs" >/dev/null
python3 -m http.server 4100 >/dev/null 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID >/dev/null 2>&1 || true" EXIT
sleep 1
curl -sf "http://127.0.0.1:4100/index.html" >/dev/null
curl -sf "http://127.0.0.1:4100/data/summary.json" | grep -E '"events"|"cards"|"sparklines"' >/dev/null
popd >/dev/null
echo "[accept_step14] OK"