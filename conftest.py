"""Test configuration and shared fixtures"""

import os

import pytest
from fastapi.testclient import TestClient

from refinance.app import app
from refinance.config import Config, get_config


# each test class have it's own empty database
@pytest.fixture(scope="class")
def test_app():
    # overwrite application name so it will use another database file
    test_config = Config(app_name="refinance-test")
    app.dependency_overrides = {get_config: lambda: test_config}
    client = TestClient(app)
    yield client
    # clean up test database file after tests
    if os.path.exists(test_config.database_path):
        os.remove(test_config.database_path)
