"""Test helper functions."""
import os
import sys
from fastapi.testclient import TestClient

def create_test_client_with_env(env_vars):
    """Create a TestClient with specific environment variables set."""
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Clear module cache to force reimport with new env vars
    modules_to_clear = [
        'tracknarrator.main',
        'tracknarrator.api',
        'tracknarrator.config',
        'tracknarrator.ui_auth'
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    # Import app after setting environment variables
    from tracknarrator.main import app
    return TestClient(app)