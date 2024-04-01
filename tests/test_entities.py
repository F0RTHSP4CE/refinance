"""Tests for Entity"""

import pytest
from fastapi import status

from refinance.repository.entity import EntityRepository
from refinance.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntityUpdateSchema,
)
from refinance.services.entity import EntityService


class TestEntityEndpoints:
    """Test API endpoints"""

    def test_create_entity(self, test_app):
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

    def test_get_entity(self, test_app):
        # get entity, check all create details match
        response = test_app.get("/entities/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Resident One"
        assert data["comment"] == "resident"
        assert data["active"] is True

    def test_patch_entity(self, test_app):
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

    def test_delete_entity_error(self, test_app):
        # try to delete, receive an error
        response = test_app.delete("/entities/1")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_get_non_existent_entity_error(self, test_app):
        # try to get, receive an error
        response = test_app.get("/entities/1111")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error_code"] == 4040
        assert "not found" in data["error"].lower()


class TestEntityFilters:
    """Test filter logic"""

    @pytest.fixture
    def entity_service(self, db_session):
        return EntityService(repo=EntityRepository(db=db_session), db=db_session)

    @pytest.fixture
    def entity_ordinary(self, entity_service):
        return entity_service.create(
            EntityCreateSchema(name="Resident Ordinary", comment="resident")
        )

    @pytest.fixture
    def entity_inactive(self, entity_service):
        e = entity_service.create(
            EntityCreateSchema(name="Resident Inactive", comment="resident (inactive)")
        )
        return entity_service.update(e.id, EntityUpdateSchema(active=False))

    def test_entity_filters(
        self, test_app, entity_service: EntityService, entity_ordinary, entity_inactive
    ):
        assert (
            entity_service.get_all(filters=EntityFiltersSchema(active=True)).total == 1
        )
        assert (
            entity_service.get_all(filters=EntityFiltersSchema(active=False)).total == 1
        )

        assert entity_service.get_all().total == 2
