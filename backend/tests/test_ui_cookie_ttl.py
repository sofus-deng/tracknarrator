from fastapi.testclient import TestClient
from .test_helpers import create_test_client_with_env

def test_cookie_ttl_env():
    # Create client with specific environment variables
    client = create_test_client_with_env({
        "TN_UI_KEY": "demo-key",
        "TN_UI_TTL_S": "120"
    })
    r = client.post("/ui/login", data={"key":"demo-key"}, follow_redirects=False)
    assert r.status_code in (302,307)
    assert r.cookies.get("tn_ui")