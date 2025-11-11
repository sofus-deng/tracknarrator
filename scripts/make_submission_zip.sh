#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT"

# 1) Generate demo artifacts
bash demo/run_demo.sh

# 2) Prepare bundle directory
OUTDIR="submission"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"/{demo-export,docs,submit}

cp -r demo/export "$OUTDIR/demo-export"
cp -f docs/index.html docs/styles.css docs/app.js "$OUTDIR/docs" 2>/dev/null || true
cp -f docs/api_quickref.md docs/demo_script.md "$OUTDIR/docs" 2>/dev/null || true
cp -r docs/submit "$OUTDIR/submit"

cp -f CHANGELOG.md "$OUTDIR/" 2>/dev/null || true
test -f VERSION && cp -f VERSION "$OUTDIR/" || true
test -f backend/pyproject.toml && cp -f backend/pyproject.toml "$OUTDIR/" || true

# 3) Zip
VER="$( (test -f VERSION && cat VERSION) || (grep -m1 '^version *= *' backend/pyproject.toml 2>/dev/null | sed -E 's/.*"(.*)".*/\1/') || echo '0.0.0' )"
ZIP="TrackNarrator_submission_v${VER}.zip"
rm -f "$ZIP"
( cd "$OUTDIR" && zip -qr "../$ZIP" . )
echo "Built $ZIP"