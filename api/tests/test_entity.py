"""Tests for Entity"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestEntityEndpoints:
    """Test API endpoints for entities, accounting for a preloaded entity with id=1"""

    def test_create_entity(self, test_app: TestClient, token):
        # Create a new entity ("Resident One"); it should receive id 100 since
        # the predefined entity (id=1) is already in the DB and the autoincrement is bumped.
        response = test_app.post(
            "/entities",
            json={"name": "Resident One", "comment": "resident"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 100
        assert data["name"] == "Resident One"
        assert data["comment"] == "resident"
        assert data["active"] is True

    def test_get_entity(self, test_app: TestClient, token):
        # Retrieve the newly created entity (id=100)
        response = test_app.get("/entities/100", headers={"x-token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 100
        assert data["name"] == "Resident One"
        assert data["comment"] == "resident"
        assert data["active"] is True

    def test_patch_entity(self, test_app: TestClient, token):
        # Modify data for entity with id=100
        new_attrs = {
            "name": "Resident One Modified",
            "comment": "resident-one-modified",
            "active": False,
        }
        response_1 = test_app.patch(
            "/entities/100", json=new_attrs, headers={"x-token": token}
        )
        assert response_1.status_code == 200
        # Verify that the modified data is now returned
        response_2 = test_app.get("/entities/100", headers={"x-token": token})
        data = response_2.json()
        for k, new_value in new_attrs.items():
            assert data[k] == new_value

    def test_delete_entity_error(self, test_app: TestClient, token):
        # Attempting to delete the entity should return an error
        response = test_app.delete("/entities/100", headers={"x-token": token})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_get_non_existent_entity_error(self, test_app: TestClient, token):
        # Trying to retrieve a non-existent entity should return an error
        response = test_app.get("/entities/1111", headers={"x-token": token})
        assert response.status_code == 418
        data = response.json()
        assert data["error_code"] == 1404
        assert "not found" in data["error"].lower()


class TestEntityFilters:
    """Test filter logic for entities, accounting for the preloaded entity"""

    @pytest.fixture
    def entity_ordinary(self, test_app: TestClient, token):
        # Create an active entity; it will receive id=100 if this test runs in isolation
        test_app.post(
            "/entities",
            json=dict(name="Resident Ordinary", comment="resident"),
            headers={"x-token": token},
        )

    @pytest.fixture
    def entity_inactive(self, test_app: TestClient, token):
        # Create an entity and then mark it inactive; it will receive id=101 if run after the ordinary entity
        r = test_app.post(
            "/entities",
            json=dict(name="Resident Inactive", comment="resident"),
            headers={"x-token": token},
        )
        data = r.json()
        test_app.patch(
            f"/entities/{data['id']}",
            json=dict(active=False),
            headers={"x-token": token},
        )

    def test_entity_filters(
        self, test_app: TestClient, entity_ordinary, entity_inactive, token
    ):
        # The DB already contains 1 predefined entity (active) plus 2 created here.
        # Expecting:
        #   active=False: 1 (from entity_inactive)
        #   active=True: 1 (predefined) + 1 (entity_ordinary) = 2
        #   total: 1 (predefined) + 2 = 3
        response_inactive = test_app.get(
            "/entities", params=dict(active=False), headers={"x-token": token}
        ).json()
        response_active = test_app.get(
            "/entities", params=dict(active=True), headers={"x-token": token}
        ).json()
        response_total = test_app.get("/entities", headers={"x-token": token}).json()

        assert response_inactive["total"] == 1
        assert response_active["total"] == 2
        assert response_total["total"] == 3
