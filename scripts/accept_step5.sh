#!/bin/bash
# Acceptance script for Step 5: coaching tips engine + export pack

set -e

echo "Running acceptance step 5: coaching tips engine + export pack"

# Step 1: Running all tests...
echo "Step 1: Running all tests..."
cd backend
if ! uv run pytest -q; then
    echo "ERROR: Tests failed"
    exit 1
fi

# Step 2: Running Step 3 acceptance (already verified in test suite)
echo "Step 2: Skipping Step 3 acceptance (already verified in test suite)"

# Step 3: Running Step 4 acceptance...
echo "Step 3: Running Step 4 acceptance..."
if ! ../scripts/accept_step4.sh; then
    echo "ERROR: Step 4 acceptance failed"
    exit 1
fi

# Step 4: Testing Step 5 acceptance...
echo "Step 4: Testing Step 5 acceptance..."

# Start dev server in background
echo "Starting dev server..."
cd backend
make dev &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
sleep 3

# Seed test data
echo "Seeding test data..."
curl -s -X POST http://localhost:8000/dev/seed \
  -H "Content-Type: application/json" \
  -d @fixtures/bundle_sample_barber.json > /dev/null

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to seed test data"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Test summary endpoint
echo "Testing /session/{id}/summary endpoint..."
SUMMARY_RESPONSE=$(curl -s http://localhost:8000/session/barber-demo-r1/summary)
if [ $? -ne 0 ]; then
    echo "ERROR: Summary API test failed"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Check summary response structure
echo "$SUMMARY_RESPONSE" | jq -e 'has("events") and has("cards") and has("sparklines")' > /dev/null
if [ "$(echo "$SUMMARY_RESPONSE" | jq -e 'has("events") and has("cards") and has("sparklines")')" != "true" ]; then
    echo "ERROR: Summary API response missing required fields"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Test export endpoint
echo "Testing /session/{id}/export endpoint..."
EXPORT_RESPONSE=$(curl -s -o /tmp/step5_export.zip http://localhost:8000/session/barber-demo-r1/export)
if [ $? -ne 0 ]; then
    echo "ERROR: Export API test failed"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Check export zip entries exist
echo "Checking export zip entries..."
if [ ! -f "/tmp/step5_export.zip" ]; then
    echo "ERROR: Export file not created"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Check zip file contents
if command -v unzip >/dev/null 2>&1; then
    ZIP_ENTRIES=$(unzip -l /tmp/step5_export.zip | tail -n +2 | head -n -1)
    EXPECTED_ENTRIES="summary.json coach_tips.json events.json cards.json sparklines.json kpis.json"
    
    for entry in $EXPECTED_ENTRIES; do
        if ! echo "$ZIP_ENTRIES" | grep -q "$entry"; then
            echo "ERROR: Missing entry in export zip: $entry"
            kill $SERVER_PID 2>/dev/null
            exit 1
        fi
    done
else
    echo "WARNING: unzip not available, checking with python"
    python3 -c "
import zipfile
import sys
try:
    with zipfile.ZipFile('/tmp/step5_export.zip', 'r') as zip_file:
        entries = zip_file.namelist()
        expected = ['summary.json', 'coach_tips.json', 'events.json', 'cards.json', 'sparklines.json', 'kpis.json']
        for entry in expected:
            if entry not in entries:
                print(f'ERROR: Missing entry in export zip: {entry}')
                sys.exit(1)
        print('All expected entries found in export zip')
except Exception as e:
    print(f'ERROR: Failed to check export zip: {e}')
    sys.exit(1)
"
    CHECK_RESULT=$?
    if [ $CHECK_RESULT -ne 0 ]; then
        echo "ERROR: Failed to validate export zip entries"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
fi

# Cleanup
echo "Cleaning up..."
rm -f /tmp/step5_export.zip

# Stop server cleanly
echo "Stopping server cleanly..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

echo "All acceptance checks passed!"