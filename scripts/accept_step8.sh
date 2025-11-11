#!/usr/bin/env bash
set -euo pipefail
# 1) regenerate demo export
bash demo/run_demo.sh
# 2) verify showcase files exist
test -s docs/index.html
test -s docs/app.js
test -s docs/styles.css
# 3) verify demo artifacts exist
test -s demo/export/summary.json
test -s demo/export/export_zh.zip
test -s demo/export/export_en.zip
echo "[accept_step8] OK"