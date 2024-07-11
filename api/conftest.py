"""Test configuration and shared fixtures"""

import os

import pytest
from app.app import app
from app.config import Config, get_config
from app.services.token import TokenService
from fastapi import Depends
from fastapi.testclient import TestClient


# each test class have it's own empty database
@pytest.fixture(scope="class")
def test_app():
    test_config = Config(
        # overwrite application name so it will use another database file
        app_name="refinance-test"
    )
    app.dependency_overrides = {get_config: lambda: test_config}

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
    """Create a very first Entity and return its token"""
    t = test_app.post("/entities/first", json={"name": "test"})
    assert t.status_code == 200
    return token_factory(1)
