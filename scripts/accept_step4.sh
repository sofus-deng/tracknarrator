#!/bin/bash

set -euo pipefail

echo "Running acceptance step 4: events optimization + summary API check"

# Run all tests
echo "Step 1: Running all tests..."
cd backend
if ! uv run pytest -q; then
    echo "Tests failed"
    exit 1
fi

echo "Step 2: Running Step 3 acceptance (weather)..."
if ! ./scripts/accept_step3.sh; then
    echo "Step 3 acceptance failed"
    exit 1
fi

# Test the new summary API endpoint
echo "Step 3: Testing summary API endpoint..."

# Start the dev server in background
make dev &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Test summary endpoint
echo "Testing /session/{id}/summary endpoint..."

# Create a simple test session
response=$(curl -s -X POST "http://localhost:8000/dev/seed" \
  -H "Content-Type: application/json" \
  -d '{
    "session": {
      "id": "summary-test",
      "source": "mylaps_csv",
      "track": "Test Track",
      "track_id": "test-track",
      "schema_version": "0.1.2"
    },
    "laps": [
      {"session_id": "summary-test", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000, "position": 5},
      {"session_id": "summary-test", "lap_no": 2, "driver": "Driver1", "laptime_ms": 130000, "position": 3},
      {"session_id": "summary-test", "lap_no": 3, "driver": "Driver1", "laptime_ms": 101000, "position": 1}
    ],
    "sections": [],
    "telemetry": [],
    "weather": []
  }')

if [ $? -ne 0 ]; then
    echo "Failed to seed test session"
    kill $SERVER_PID
    exit 1
fi

# Test the summary endpoint
summary_response=$(curl -s "http://localhost:8000/dev/session/summary-test/summary")
if [ $? -ne 0 ]; then
    echo "Failed to get summary"
    kill $SERVER_PID
    exit 1
fi

# Check that response contains expected keys
if ! echo "$summary_response" | grep -q '"events"'; then
    echo "Summary response missing 'events' key"
    kill $SERVER_PID
    exit 1
fi

if ! echo "$summary_response" | grep -q '"cards"'; then
    echo "Summary response missing 'cards' key"
    kill $SERVER_PID
    exit 1
fi

if ! echo "$summary_response" | grep -q '"sparklines"'; then
    echo "Summary response missing 'sparklines' key"
    kill $SERVER_PID
    exit 1
fi

echo "Summary API test passed"

# Clean up
kill $SERVER_PID

echo "All acceptance checks passed!"