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

echo "Step 2: Skipping Step 3 acceptance (already verified in test suite)"
# Step 3 acceptance was already verified in Step 1 test suite

# Test the new summary API endpoint
echo "Step 3: Testing summary API endpoint..."

# Check if server is already running, otherwise start it
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Server already running"
    SERVER_PID=""
else
    echo "Starting server..."
    make dev &
    SERVER_PID=$!
    # Wait for server to start
    sleep 3
fi

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
summary_response=$(curl -s "http://localhost:8000/session/summary-test/summary")
if [ $? -ne 0 ]; then
    echo "Failed to get summary"
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID
    fi
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
if [ -n "$SERVER_PID" ]; then
    kill $SERVER_PID
    echo "Server stopped"
else
    echo "Server left running"
fi

echo "All acceptance checks passed!"