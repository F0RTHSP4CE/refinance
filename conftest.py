"""Test configuration and shared fixtures"""

import os

import pytest
from fastapi.testclient import TestClient

from refinance.app import app
from refinance.config import Config, get_config


# each test class have it's own empty database
@pytest.fixture(scope="class")
def test_app():
    test_config = Config(
        # overwrite application name so it will use another database file
        app_name="refinance-test",
        # pass a list of valid test tokens
        api_tokens=["valid-token-000"],
    )
    app.dependency_overrides = {get_config: lambda: test_config}
    # pass valid token for all requests
    client = TestClient(app, headers={"x-token": "valid-token-000"})
    yield client
    # clean up test database file after tests
    if os.path.exists(test_config.database_path):
        os.remove(test_config.database_path)
