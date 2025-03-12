from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="class")
def entity_one(test_app: TestClient, token):
    response = test_app.post(
        "/entities", json={"name": "User One 1"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    data = response.json()
    return data["id"]


@pytest.fixture(scope="class")
def entity_two(test_app: TestClient, token):
    response = test_app.post(
        "/entities", json={"name": "User Two 2"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    data = response.json()
    return data["id"]


@pytest.fixture
def create_transaction(test_app: TestClient, entity_one, entity_two, token):
    response = test_app.post(
        "/transactions",
        json={
            "from_entity_id": entity_one,
            "to_entity_id": entity_two,
            "amount": "150.00",
            "currency": "usd",
        },
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response


class TestTransactionEndpoints:
    """Test API endpoints for transactions"""

    def test_create_transaction(
        self, test_app: TestClient, entity_one, entity_two, token
    ):
        # Create a new transaction
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "200.00",
                "currency": "usd",
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["from_entity_id"] == entity_one
        assert data["to_entity_id"] == entity_two
        assert Decimal(data["amount"]) == Decimal("200.00")
        assert data["currency"] == "usd"

    def test_get_transaction(self, test_app: TestClient, create_transaction, token):
        # Get transaction, check all create details match
        transaction_id = create_transaction.json()["id"]
        response = test_app.get(
            f"/transactions/{transaction_id}", headers={"x-token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transaction_id

    def test_cannot_unconfirm_confirmed_transaction(
        self, test_app: TestClient, entity_one, entity_two, token
    ):
        """
        Existing test: ensure that once a transaction is confirmed,
        it cannot be updated to unconfirmed.
        """
        # First, create a transaction that is confirmed
        create_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "300.00",
                "currency": "usd",
                "confirmed": True,
            },
            headers={"x-token": token},
        )
        assert create_response.status_code == 200
        tx_data = create_response.json()
        tx_id = tx_data["id"]
        assert tx_data["confirmed"] is True

        # Try to unconfirm the transaction
        update_response = test_app.patch(
            f"/transactions/{tx_id}",
            json={"confirmed": False},
            headers={"x-token": token},
        )
        assert update_response.status_code == 418, "Expected 418"

        # Double-check the transaction is still confirmed
        get_response = test_app.get(
            f"/transactions/{tx_id}",
            headers={"x-token": token},
        )
        assert get_response.status_code == 200
        updated_data = get_response.json()
        assert (
            updated_data["confirmed"] is True
        ), "Transaction should still be confirmed"

    def test_cannot_edit_confirmed_transaction(
        self, test_app: TestClient, entity_one, entity_two, token
    ):
        """
        New test: ensure that once a transaction is confirmed,
        *no fields* can be updated (not just the 'confirmed' field).
        """
        # Create a confirmed transaction
        create_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one,
                "to_entity_id": entity_two,
                "amount": "500.00",
                "currency": "usd",
                "confirmed": True,
                "comment": "aaa",
            },
            headers={"x-token": token},
        )
        assert create_response.status_code == 200
        tx_data = create_response.json()
        tx_id = tx_data["id"]
        assert tx_data["confirmed"] is True

        # Attempt to update fields (e.g. amount, currency)
        update_response = test_app.patch(
            f"/transactions/{tx_id}",
            json={
                "amount": "9999.99",
                "currency": "eur",
                "comment": "bbb",
            },
            headers={"x-token": token},
        )
        assert update_response.status_code == 418, "Expected API error (HTTP 418)"

        # Double-check that the transaction is unchanged
        get_response = test_app.get(
            f"/transactions/{tx_id}",
            headers={"x-token": token},
        )
        assert get_response.status_code == 200
        updated_data = get_response.json()
        assert updated_data["amount"] == "500.00"
        assert updated_data["currency"] == "usd"
        assert updated_data["comment"] == "aaa"
        assert updated_data["confirmed"] is True


@pytest.fixture
def multiple_transactions(test_app: TestClient, entity_one, entity_two, token):
    """Create multiple transactions to test filtering."""
    transactions = [
        {
            "from_entity_id": entity_one,
            "to_entity_id": entity_two,
            "amount": "50.00",
            "currency": "usd",
            "confirmed": True,
        },
        {
            "from_entity_id": entity_two,
            "to_entity_id": entity_one,
            "amount": "75.00",
            "currency": "eur",
            "confirmed": False,
        },
        {
            "from_entity_id": entity_one,
            "to_entity_id": entity_two,
            "amount": "150.00",
            "currency": "usd",
            "confirmed": True,
        },
        {
            "from_entity_id": entity_two,
            "to_entity_id": entity_one,
            "amount": "200.00",
            "currency": "usd",
            "confirmed": False,
        },
    ]
    for transaction in transactions:
        response = test_app.post(
            "/transactions", json=transaction, headers={"x-token": token}
        )
        assert response.status_code == 200


class TestTransactionFiltering:
    """Test filtering logic for transaction endpoints"""

    def test_filter_by_currency(
        self, test_app: TestClient, multiple_transactions, token
    ):
        response = test_app.get(
            "/transactions", params={"currency": "usd"}, headers={"x-token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_filter_by_amount_range(
        self, test_app: TestClient, multiple_transactions, token
    ):
        response = test_app.get(
            "/transactions",
            params={"amount_min": "100", "amount_max": "300"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_filter_by_confirmation_status(
        self, test_app: TestClient, multiple_transactions, token
    ):
        response = test_app.get(
            "/transactions", params={"confirmed": True}, headers={"x-token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_filter_by_from_entity_id(
        self, test_app: TestClient, multiple_transactions, entity_one, token
    ):
        response = test_app.get(
            "/transactions",
            params={"from_entity_id": entity_one},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_filter_by_to_entity_id(
        self, test_app: TestClient, multiple_transactions, entity_two, token
    ):
        response = test_app.get(
            "/transactions",
            params={"to_entity_id": entity_two},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_filter_by_entity_id(
        self, test_app: TestClient, multiple_transactions, entity_one, entity_two, token
    ):
        response = test_app.get(
            "/transactions",
            params={"entity_id": entity_one},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
