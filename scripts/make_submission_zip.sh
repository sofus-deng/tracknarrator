#!/usr/bin/env bash
# TrackNarrator Hack the Track Submission ZIP Creator
# 
# This script creates a clean submission ZIP for the Hack the Track competition.
# It uses git archive to include only tracked files from the current HEAD commit.
# 
# Intentionally excluded:
# - Raw TRD datasets in data/ directory (ignored by .gitignore)
# - Virtual environments (.venv/, .uv/)
# - Python caches (__pycache__, *.pyc)
# - Local environment files (.env, *.log)
# - Build artifacts (dist/, build/, *.egg-info/)
# - Any other files listed in .gitignore
#
# Usage:
#   ./scripts/make_submission_zip.sh                    # Creates tracknarrator_hack-the-track_submission.zip
#   ./scripts/make_submission_zip.sh my_submission.zip   # Creates my_submission.zip

set -euo pipefail

# Get the repository root directory
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT"

# Set output filename (default or from first argument)
OUTPUT="${1:-tracknarrator_hack-the-track_submission.zip}"

# Create the ZIP using git archive from current HEAD
echo "Creating submission ZIP from tracked files at HEAD..."
git archive --format=zip --output="$OUTPUT" HEAD

echo "Created submission ZIP: $OUTPUT"
echo ""
echo "The ZIP contains only tracked files from the current HEAD commit."
echo "It excludes data/, .venv/, __pycache__, and other ignored files per .gitignore."