"""Test configuration and shared fixtures"""

import os
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient

from refinance.app import app_factory
from refinance.config import Config


# each test class have it's own empty database
@pytest.fixture(scope="class")
def test_app() -> Generator[TestClient, Any, None]:
    # overwrite application name so it will use another database file
    test_config = Config(app_name="refinance-test")
    app = app_factory(config=test_config)
    client = TestClient(app)
    yield client
    # clean up test database file after tests
    if os.path.exists(test_config.database_path):
        os.remove(test_config.database_path)
