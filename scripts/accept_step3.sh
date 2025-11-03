#!/bin/bash

set -euo pipefail

echo "Running acceptance step 3: weather E2E check"

SID=$(uuidgen)

echo "Using session ID: $SID"

response=$(curl -s -X POST -F "file=@samples/weather_ok.csv" "http://localhost:8000/ingest/weather?session_id=$SID")

weather_added=$(echo "$response" | jq -r '.counts.weather_added // 0')
weather_updated=$(echo "$response" | jq -r '.counts.weather_updated // 0')

total=$((weather_added + weather_updated))

if [ "$total" -gt 0 ]; then
  echo "Weather data added or updated: $total"
else
  echo "No weather data added or updated"
  exit 1
fi
