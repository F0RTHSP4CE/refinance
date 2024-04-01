"""Test configuration and shared fixtures"""

import os

import pytest
from fastapi.testclient import TestClient

from refinance.app import app
from refinance.config import config
from refinance.db import get_db


@pytest.fixture(scope="class", autouse=True)
def db_session():
    # change app name so it will use another database file
    config.app_name = "refinance-test"
    # connect to the database
    yield get_db().__next__()
    # delete the database file
    if os.path.exists(config.database_path):
        os.remove(config.database_path)


@pytest.fixture(scope="module")
def test_app():
    app.dependency_overrides = {}
    client = TestClient(app)
    yield client
