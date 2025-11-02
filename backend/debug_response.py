import io
import json
from fastapi.testclient import TestClient
from src.tracknarrator.api import app

client = TestClient(app)

# Create a CSV with only 3 recognized fields (<5 required)
csv_content = """ts_ms,name,value
0,speed,120.5
0,aps,75.2
0,gear,3"""

response = client.post(
    "/ingest/trd-long?session_id=test-session",
    files={"file": ("trd.csv", csv_content, "text/csv")}
)

print('Response status:', response.status_code)
print('Response JSON:', json.dumps(response.json(), indent=2))