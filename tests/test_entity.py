"""Tests for Entity"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestEntityEndpoints:
    """Test API endpoints"""

    def test_create_entity(self, test_app: TestClient):
        # create a new entity, resident
        response = test_app.post(
            "/entities/",
            json={"name": "Resident One", "comment": "resident"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Resident One"
        assert data["comment"] == "resident"
        assert data["active"] is True

    def test_get_entity(self, test_app: TestClient):
        # get entity, check all create details match
        response = test_app.get("/entities/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Resident One"
        assert data["comment"] == "resident"
        assert data["active"] is True

    def test_patch_entity(self, test_app: TestClient):
        # modify data
        new_attrs = {
            "name": "Resident One Modified",
            "comment": "resident-one-modified",
            "active": False,
        }
        response_1 = test_app.patch("/entities/1", json=new_attrs)
        assert response_1.status_code == 200
        # check that modified data is returned now
        response_2 = test_app.get("/entities/1")
        data = response_2.json()
        for k, new_value in new_attrs.items():
            assert data[k] == new_value

    def test_delete_entity_error(self, test_app: TestClient):
        # try to delete, receive an error
        response = test_app.delete("/entities/1")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_get_non_existent_entity_error(self, test_app: TestClient):
        # try to get, receive an error
        response = test_app.get("/entities/1111")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error_code"] == 1404
        assert "not found" in data["error"].lower()


class TestEntityFilters:
    """Test filter logic"""

    @pytest.fixture
    def entity_ordinary(self, test_app: TestClient):
        test_app.post(
            "/entities/", json=dict(name="Resident Ordinary", comment="resident")
        )

    @pytest.fixture
    def entity_inactive(self, test_app: TestClient):
        r = test_app.post(
            "/entities/", json=dict(name="Resident Inactive", comment="resident")
        )
        data = r.json()
        test_app.patch(f"/entities/{data['id']}", json=dict(active=False))

    def test_entity_filters(
        self, test_app: TestClient, entity_ordinary, entity_inactive
    ):
        assert (
            test_app.get("/entities/", params=dict(active=False)).json()["total"] == 1
        )
        assert test_app.get("/entities/", params=dict(active=True)).json()["total"] == 1
        assert test_app.get("/entities/").json()["total"] == 2
