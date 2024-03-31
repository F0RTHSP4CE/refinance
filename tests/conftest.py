"""Test configuration and shared fixtures"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# enable project imports relative to the current directory
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


@pytest.fixture(scope="session", autouse=True)
def override_db_url():
    from refinance.config import config  # noqa: E402

    # replace database with the test one
    TEST_DATABASE_PATH = "./test.db"
    config.database_url = f"sqlite:///{TEST_DATABASE_PATH}"

    # return to the test session
    yield

    # delete the test database after tests
    if os.path.exists(TEST_DATABASE_PATH):
        os.remove(TEST_DATABASE_PATH)


@pytest.fixture(scope="module")
def test_app():
    from refinance.app import app  # noqa: E402

    app.dependency_overrides = {}
    client = TestClient(app)
    yield client
