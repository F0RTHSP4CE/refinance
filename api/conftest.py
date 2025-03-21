"""Test configuration and shared fixtures"""

import logging
import os
import sys
import traceback

import pytest
from app.app import app
from app.config import Config, get_config
from app.db import DatabaseConnection
from app.services.token import TokenService
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

_original_request = TestClient.request


def logging_request(self, *args, **kwargs):
    try:
        response = _original_request(self, *args, **kwargs)
    except Exception as exc:
        # Print request details on exception
        print("\n=== Exception in TestClient.request ===")
        print("Request args:", args)
        print("Request kwargs:", kwargs)
        traceback.print_exc(file=sys.stdout)
        raise

    # Optionally, if the response indicates an error, log details
    if response.status_code >= 400:
        req = response.request
        print("\n=== HTTP Error Response Captured ===")
        print(f"Method: {req.method} URL: {req.url}")
        print("Request Content:", req.content)
        print("Response Status:", response.status_code)
        print("Response Body:", response.text)
    return response


# Patch TestClient.request globally
TestClient.request = logging_request


# each test class have it's own empty database
@pytest.fixture(scope="class")
def test_app():
    test_config = Config(
        # overwrite application name so it will use another database file
        app_name="refinance-test"
    )
    app.dependency_overrides = {get_config: lambda: test_config}

    # trigger table creation and bootstrapping
    db_conn = DatabaseConnection(config=test_config)
    db_conn.create_tables()
    db_conn.seed_bootstrap_data()

    # create private token generator route to be used only from tests
    @app.get("/tokens/{entity_id}", include_in_schema=False)
    def _generate_token(
        entity_id: int, token_service: TokenService = Depends()
    ) -> str | None:
        return token_service._generate_new_token(entity_id=entity_id)

    client = TestClient(app)
    yield client
    # clean up test database file after tests
    if os.path.exists(test_config.database_path):
        os.remove(test_config.database_path)


# general fixture to get the token of any entity
@pytest.fixture(scope="class")
def token_factory(test_app: TestClient):
    """Get token of any Entity by id"""

    def f(entity_id: int):
        r = test_app.get(f"/tokens/{entity_id}")
        assert r.status_code == 200
        return r.json()

    return f


@pytest.fixture(scope="class")
def token(test_app: TestClient, token_factory):
    """get token of the first (system) entity"""
    return token_factory(1)
