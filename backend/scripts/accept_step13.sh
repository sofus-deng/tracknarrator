#!/usr/bin/env bash
set -euo pipefail

echo "Running acceptance step 13: Share governance - list & revoke share tokens"

# Start server in background
(make dev > /dev/null 2>&1 &) ; DEV_PID=$!
cleanup(){ 
    kill "$DEV_PID" >/dev/null 2>&1 || true; 
    wait "$DEV_PID" 2>/dev/null || true; 
}
trap cleanup EXIT

# Wait for server to start
for i in {1..60}; do 
    curl -sf http://127.0.0.1:8000/docs >/dev/null && break; 
    sleep 0.5; 
done

# Seed test data
SID=$(curl -sS -X POST http://127.0.0.1:8000/dev/seed \
    -H 'Content-Type: application/json' \
    --data-binary @backend/fixtures/bundle_sample_barber.json | \
    python -c "
import sys,json,re
s=sys.stdin.read()
try:
    print(json.loads(s).get('session_id','barber'))
except:
    m=re.search(r'\"session_id\":\"([^\"]+)\"',s)
    print(m.group(1) if m else 'barber')
")

echo "Using session ID: $SID"

# Create share with label
CREATE=$(curl -sS "http://127.0.0.1:8000/share/${SID}?ttl_s=3600&label=accept13")
TOK=$(python -c "
import json,sys
data=json.loads(sys.argv[1])
print(data['token'])
" "$CREATE")
)

echo "Created share token: $TOK"

# List shares and verify our share appears
echo "Checking share appears in list..."
LIST_RESULT=$(curl -sS "http://127.0.0.1:8000/shares?session_id=${SID}")
if echo "$LIST_RESULT" | grep -q "${SID}"; then
    echo "✓ Share appears in list"
else
    echo "✗ Share not found in list"
    exit 1
fi

if echo "$LIST_RESULT" | grep -q "accept13"; then
    echo "✓ Share label is correct"
else
    echo "✗ Share label not found"
    exit 1
fi

# Verify we can access shared summary
echo "Testing shared summary access..."
SUMMARY_RESULT=$(curl -sS "http://127.0.0.1:8000/shared/${TOK}/summary")
if echo "$SUMMARY_RESULT" | jq -e .events >/dev/null 2>&1; then
    echo "✓ Can access shared summary"
else
    echo "✗ Cannot access shared summary"
    exit 1
fi

# Revoke the share
echo "Revoking share..."
REVOKE_RESULT=$(curl -sS -X DELETE "http://127.0.0.1:8000/share/${TOK}" -o /dev/null -w "%{http_code}")
if [ "$REVOKE_RESULT" = "204" ]; then
    echo "✓ Share revoked successfully"
else
    echo "✗ Failed to revoke share (HTTP $REVOKE_RESULT)"
    exit 1
fi

# Verify access is denied after revocation
echo "Testing access after revocation..."
ACCESS_RESULT=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/shared/${TOK}/summary")
if [ "$ACCESS_RESULT" = "401" ] || [ "$ACCESS_RESULT" = "410" ]; then
    echo "✓ Access properly denied after revocation (HTTP $ACCESS_RESULT)"
else
    echo "✗ Access not denied after revocation (HTTP $ACCESS_RESULT)"
    exit 1
fi

# Verify share no longer appears in list
echo "Checking share removed from list..."
LIST_AFTER_REVOKE=$(curl -sS "http://127.0.0.1:8000/shares?session_id=${SID}")
if echo "$LIST_AFTER_REVOKE" | grep -q "accept13"; then
    echo "✗ Revoked share still appears in list"
    exit 1
else
    echo "✓ Revoked share removed from list"
fi

echo "[accept_step13] OK"
echo ""
echo "Step 13 Summary:"
echo "  ✓ Share creation with label works"
echo "  ✓ Share listing works"
echo "  ✓ Shared summary access works"
echo "  ✓ Share revocation works"
echo "  ✓ Access denied after revocation"
echo "  ✓ Revoked shares excluded from list"