"""Tests for tag management in create/update operations"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="class")
def test_tag_one(test_app: TestClient, token):
    response = test_app.post(
        "/tags", json={"name": "Test Tag One"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def test_tag_two(test_app: TestClient, token):
    response = test_app.post(
        "/tags", json={"name": "Test Tag Two"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def entity_one(test_app: TestClient, token):
    response = test_app.post(
        "/entities", json={"name": "Entity One"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def entity_two(test_app: TestClient, token):
    response = test_app.post(
        "/entities", json={"name": "Entity Two"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


class TestTransactionTagManagement:
    """Test tag management for transactions"""

    def test_create_transaction_with_tags(
        self,
        test_app: TestClient,
        entity_one,
        entity_two,
        test_tag_one,
        test_tag_two,
        token,
    ):
        # Create transaction with tags
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "100.00",
                "currency": "usd",
                "tag_ids": [test_tag_one, test_tag_two],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["tags"]) == 2
        tag_ids = [tag["id"] for tag in data["tags"]]
        assert test_tag_one in tag_ids
        assert test_tag_two in tag_ids

    def test_create_transaction_without_tags(
        self, test_app: TestClient, entity_one, entity_two, token
    ):
        # Create transaction without tags
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "50.00",
                "currency": "usd",
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["tags"]) == 0

    def test_update_transaction_tags(
        self,
        test_app: TestClient,
        entity_one,
        entity_two,
        test_tag_one,
        test_tag_two,
        token,
    ):
        # Create transaction first
        create_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "75.00",
                "currency": "usd",
                "tag_ids": [test_tag_one],
            },
            headers={"x-token": token},
        )
        transaction_id = create_response.json()["id"]

        # Update with different tags
        update_response = test_app.patch(
            f"/transactions/{transaction_id}",
            json={"tag_ids": [test_tag_two]},
            headers={"x-token": token},
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["id"] == test_tag_two

    def test_update_transaction_clear_tags(
        self, test_app: TestClient, entity_one, entity_two, test_tag_one, token
    ):
        # Create transaction with tags
        create_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "25.00",
                "currency": "usd",
                "tag_ids": [test_tag_one],
            },
            headers={"x-token": token},
        )
        transaction_id = create_response.json()["id"]

        # Clear tags
        update_response = test_app.patch(
            f"/transactions/{transaction_id}",
            json={"tag_ids": []},
            headers={"x-token": token},
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert len(data["tags"]) == 0


class TestEntityTagManagement:
    """Test tag management for entities"""

    def test_create_entity_with_tags(
        self, test_app: TestClient, test_tag_one, test_tag_two, token
    ):
        # Create entity with tags
        response = test_app.post(
            "/entities",
            json={
                "name": "Tagged Entity",
                "tag_ids": [test_tag_one, test_tag_two],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["tags"]) == 2
        tag_ids = [tag["id"] for tag in data["tags"]]
        assert test_tag_one in tag_ids
        assert test_tag_two in tag_ids

    def test_update_entity_tags(
        self, test_app: TestClient, test_tag_one, test_tag_two, token
    ):
        # Create entity first
        create_response = test_app.post(
            "/entities",
            json={
                "name": "Entity to Update",
                "tag_ids": [test_tag_one],
            },
            headers={"x-token": token},
        )
        entity_id = create_response.json()["id"]

        # Update with different tags
        update_response = test_app.patch(
            f"/entities/{entity_id}",
            json={"tag_ids": [test_tag_two]},
            headers={"x-token": token},
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["id"] == test_tag_two


class TestTagFiltering:
    """Test filtering by tags"""

    def test_filter_transactions_by_tags(
        self,
        test_app: TestClient,
        entity_one,
        entity_two,
        test_tag_one,
        test_tag_two,
        token,
    ):
        # Create transactions with different tags
        test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "10.00",
                "currency": "usd",
                "tag_ids": [test_tag_one],
            },
            headers={"x-token": token},
        )

        test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "20.00",
                "currency": "usd",
                "tag_ids": [test_tag_two],
            },
            headers={"x-token": token},
        )

        # Filter by first tag
        response = test_app.get(
            "/transactions",
            params={"tags_ids": [test_tag_one]},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        # Should have at least one transaction with the tag
        assert len(data["items"]) >= 1
        for transaction in data["items"]:
            tag_ids = [tag["id"] for tag in transaction["tags"]]
            assert test_tag_one in tag_ids

    def test_filter_entities_by_tags(
        self, test_app: TestClient, test_tag_one, test_tag_two, token
    ):
        # Create entities with different tags
        test_app.post(
            "/entities",
            json={
                "name": "Entity with Tag One",
                "tag_ids": [test_tag_one],
            },
            headers={"x-token": token},
        )

        test_app.post(
            "/entities",
            json={
                "name": "Entity with Tag Two",
                "tag_ids": [test_tag_two],
            },
            headers={"x-token": token},
        )

        # Filter by first tag
        response = test_app.get(
            "/entities",
            params={"tags_ids": [test_tag_one]},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        # Should have at least one entity with the tag
        assert len(data["items"]) >= 1
        for entity in data["items"]:
            tag_ids = [tag["id"] for tag in entity["tags"]]
            assert test_tag_one in tag_ids
