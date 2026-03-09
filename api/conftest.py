"""Test configuration and shared fixtures"""

import os

# Disable CSRF for tests (TestClient does not send cookies)
os.environ["REFINANCE_CSRF_DISABLED"] = "1"
import sys
import traceback
import uuid
from contextlib import contextmanager

import pytest
from app.app import app
from app.config import Config, get_config
from app.db import DatabaseConnection
from app.services.token import TokenService
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

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


DEFAULT_TEST_DATABASE_URL = "postgresql://postgres@db:5432/refinance_test"


def _get_test_database_url() -> str:
    explicit_test_url = os.getenv("REFINANCE_TEST_DATABASE_URL")
    if explicit_test_url:
        return explicit_test_url

    runtime_database_url = os.getenv("REFINANCE_DATABASE_URL")
    if not runtime_database_url:
        return DEFAULT_TEST_DATABASE_URL

    # Reuse the runtime DB credentials so Docker-backed tests keep working
    # against existing local volumes that were initialized with password auth.
    url = make_url(runtime_database_url)
    database_name = url.database or "refinance"
    if not database_name.endswith("_test"):
        database_name = f"{database_name}_test"
    return url.set(database=database_name).render_as_string(hide_password=False)


def _quote_database(name: str) -> str:
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


@contextmanager
def _temporary_database(base_dsn: str):
    url = make_url(base_dsn)
    base_name = url.database or "refinance_test"
    unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}"
    admin_url = url.set(database="postgres").render_as_string(hide_password=False)
    database_url = url.set(database=unique_name)
    quoted_name = _quote_database(unique_name)
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {quoted_name}"))
        yield database_url.render_as_string(hide_password=False)
    finally:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :db"
                ),
                {"db": unique_name},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {quoted_name}"))
        engine.dispose()


# each test class has its own isolated database
@pytest.fixture(scope="class")
def test_app():
    base_dsn = _get_test_database_url()
    with _temporary_database(base_dsn) as database_url:
        test_config = Config(
            app_name="refinance-test",
            database_url_env=database_url,
            pos_secret="test-pos-secret",
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
        try:
            yield client
        finally:
            client.close()
            app.dependency_overrides.clear()
            db_conn.engine.dispose()
            # Clear in-memory caches so stale data from one test class
            # does not bleed into the next (each class uses its own DB).
            from app.services.balance import BalanceService

            BalanceService._cache.clear()
            BalanceService._treasury_cache.clear()


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
