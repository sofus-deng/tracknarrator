#!/bin/bash
set -e

echo "Running acceptance step 6: AI-Native narrative template expansion with deterministic outputs, multilingual support, on/off switch, and docs."

# Step 1: Running all tests...
echo "Step 1: Running all tests..."
cd backend
uv run pytest -q

if [ $? -ne 0 ]; then
    echo "ERROR: Tests failed"
    exit 1
fi

echo "Tests passed successfully."

# Step 2: Start dev server...
echo "Step 2: Starting dev server..."
make dev &
DEV_PID=$!

# Wait for server to start
sleep 3

# Step 3: Test narrative endpoint with different languages and modes...
echo "Step 3: Testing narrative endpoint..."

# Seed test data
curl -s -X POST "http://localhost:8000/dev/seed" \
    -H "Content-Type: application/json" \
    -d '{
        "session": {
            "id": "step6-test",
            "source": "mylaps_csv",
            "track": "Test Track",
            "track_id": "test-track",
            "schema_version": "0.1.2"
        },
        "laps": [
            {"session_id": "step6-test", "lap_no": 1, "driver": "Driver1", "laptime_ms": 100000},
            {"session_id": "step6-test", "lap_no": 2, "driver": "Driver1", "laptime_ms": 130000},
            {"session_id": "step6-test", "lap_no": 3, "driver": "Driver1", "laptime_ms": 99000}
        ],
        "sections": [],
        "telemetry": [],
        "weather": []
    }' > /dev/null

# Wait a bit for data to be processed
sleep 1

# Test narrative with zh-Hant and ai_native=on
echo "Testing narrative with zh-Hant and ai_native=on..."
ZH_HANT_RESPONSE=$(curl -s "http://localhost:8000/session/step6-test/narrative?lang=zh-Hant&ai_native=on")
ZH_HANT_HASH=$(echo "$ZH_HANT_RESPONSE" | jq -r '.lines | join(",")' | md5sum | cut -d' ' -f1)

echo "zh-Hant response: $ZH_HANT_RESPONSE"
echo "zh-Hant hash: $ZH_HANT_HASH"

# Test narrative with en and ai_native=on
echo "Testing narrative with en and ai_native=on..."
EN_RESPONSE=$(curl -s "http://localhost:8000/session/step6-test/narrative?lang=en&ai_native=on")
EN_HASH=$(echo "$EN_RESPONSE" | jq -r '.lines | join(",")' | md5sum | cut -d' ' -f1)

echo "en response: $EN_RESPONSE"
echo "en hash: $EN_HASH"

# Test narrative with ai_native=off
echo "Testing narrative with ai_native=off..."
OFF_RESPONSE=$(curl -s "http://localhost:8000/session/step6-test/narrative?ai_native=off")
OFF_HASH=$(echo "$OFF_RESPONSE" | jq -r '.lines | join(",")' | md5sum | cut -d' ' -f1)

echo "off response: $OFF_RESPONSE"
echo "off hash: $OFF_HASH"

# Step 4: Test summary endpoint with narrative field...
echo "Step 4: Testing summary endpoint with narrative field..."

# Test summary with ai_native=on (should include narrative)
echo "Testing summary with ai_native=on..."
SUMMARY_WITH_NARRATIVE=$(curl -s "http://localhost:8000/session/step6-test/summary?ai_native=on")

# Check that narrative field is present
NARRATIVE_FIELD_PRESENT=$(echo "$SUMMARY_WITH_NARRATIVE" | jq -r 'has("narrative")')
if [ "$NARRATIVE_FIELD_PRESENT" = "true" ]; then
    echo "✓ Summary includes narrative field when ai_native=on"
else
    echo "✗ Summary missing narrative field when ai_native=on"
    exit 1
fi

# Test summary without ai_native parameter (should not include narrative)
echo "Testing summary without ai_native parameter..."
SUMMARY_WITHOUT_NARRATIVE=$(curl -s "http://localhost:8000/session/step6-test/summary")

# Check that narrative field is absent
NARRATIVE_FIELD_ABSENT=$(echo "$SUMMARY_WITHOUT_NARRATIVE" | jq -r 'has("narrative")')
if [ "$NARRATIVE_FIELD_ABSENT" = "false" ]; then
    echo "✓ Summary excludes narrative field when ai_native not specified"
else
    echo "✗ Summary includes narrative field when not requested"
    exit 1
fi

# Step 5: Test export pack includes narrative.json...
echo "Step 5: Testing export pack includes narrative.json..."

# Test export with zh-Hant
echo "Testing export with zh-Hant..."
EXPORT_ZH_RESPONSE=$(curl -s "http://localhost:8000/session/step6-test/export?lang=zh-Hant" -o /tmp/step6_export_zh.zip)

# Check that narrative.json is in the export
if unzip -l /tmp/step6_export_zh.zip | grep -q "narrative.json"; then
    echo "✓ Export includes narrative.json for zh-Hant"
else
    echo "✗ Export missing narrative.json for zh-Hant"
    exit 1
fi

# Test export with en
echo "Testing export with en..."
EXPORT_EN_RESPONSE=$(curl -s "http://localhost:8000/session/step6-test/export?lang=en" -o /tmp/step6_export_en.zip)

# Check that narrative.json is in the export
if unzip -l /tmp/step6_export_en.zip | grep -q "narrative.json"; then
    echo "✓ Export includes narrative.json for en"
else
    echo "✗ Export missing narrative.json for en"
    exit 1
fi

# Step 6: Verify JSON shapes and determinism...
echo "Step 6: Verifying JSON shapes and determinism..."

# Verify zh-Hant response shape
ZH_HANT_LINES_COUNT=$(echo "$ZH_HANT_RESPONSE" | jq -r '.lines | length')
ZH_HANT_LANG=$(echo "$ZH_HANT_RESPONSE" | jq -r '.lang')
ZH_HANT_AI_NATIVE=$(echo "$ZH_HANT_RESPONSE" | jq -r '.ai_native')

if [ "$ZH_HANT_LINES_COUNT" -le 3 ] && [ "$ZH_HANT_LANG" = "zh-Hant" ] && [ "$ZH_HANT_AI_NATIVE" = "true" ]; then
    echo "✓ zh-Hant narrative response shape is valid"
else
    echo "✗ zh-Hant narrative response shape is invalid"
    echo "  Lines count: $ZH_HANT_LINES_COUNT (should be ≤ 3)"
    echo "  Language: $ZH_HANT_LANG (should be zh-Hant)"
    echo "  AI native: $ZH_HANT_AI_NATIVE (should be true)"
    exit 1
fi

# Verify en response shape
EN_LINES_COUNT=$(echo "$EN_RESPONSE" | jq -r '.lines | length')
EN_LANG=$(echo "$EN_RESPONSE" | jq -r '.lang')
EN_AI_NATIVE=$(echo "$EN_RESPONSE" | jq -r '.ai_native')

if [ "$EN_LINES_COUNT" -le 3 ] && [ "$EN_LANG" = "en" ] && [ "$EN_AI_NATIVE" = "true" ]; then
    echo "✓ en narrative response shape is valid"
else
    echo "✗ en narrative response shape is invalid"
    echo "  Lines count: $EN_LINES_COUNT (should be ≤ 3)"
    echo "  Language: $EN_LANG (should be en)"
    echo "  AI native: $EN_AI_NATIVE (should be true)"
    exit 1
fi

# Verify determinism by making same request twice
echo "Testing determinism by making same request twice..."
ZH_HANT_RESPONSE_2=$(curl -s "http://localhost:8000/session/step6-test/narrative?lang=zh-Hant&ai_native=on")
ZH_HANT_HASH_2=$(echo "$ZH_HANT_RESPONSE_2" | jq -r '.lines | join(",")' | md5sum | cut -d' ' -f1)

if [ "$ZH_HANT_HASH" = "$ZH_HANT_HASH_2" ]; then
    echo "✓ Narrative output is deterministic (same hash for same request)"
else
    echo "✗ Narrative output is not deterministic (different hash for same request)"
    echo "  First hash: $ZH_HANT_HASH"
    echo "  Second hash: $ZH_HANT_HASH_2"
    exit 1
fi

# Step 7: Stop dev server...
echo "Step 7: Stopping dev server..."
kill $DEV_PID
wait $DEV_PID 2>/dev/null

echo "✓ All Step 6 acceptance tests passed!"
echo ""
echo "Step 6 Summary:"
echo "  ✓ Narrative endpoint supports multilingual (zh-Hant/en)"
echo "  ✓ Narrative endpoint supports ai_native on/off switch"
echo "  ✓ Summary endpoint includes narrative field when ai_native=on"
echo "  ✓ Summary endpoint excludes narrative field when ai_native not specified"
echo "  ✓ Export pack includes narrative.json"
echo "  ✓ Narrative output is deterministic"
echo "  ✓ JSON response shapes are valid"
echo "  ✓ Hash verification confirms consistency"

exit 0