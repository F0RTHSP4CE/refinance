"""Tests for Balance API and Transaction confirmation"""

from decimal import Decimal

from fastapi import status
from fastapi.testclient import TestClient


class TestBalanceEndpoints:
    """Test API endpoints for Balance"""

    def test_entity_transactions_balance(
        self, test_app: TestClient, token_factory, token
    ):
        # Create entities
        response = test_app.post(
            "/entities", json={"name": "Entity A"}, headers={"x-token": token}
        )
        entity_a_id = response.json()["id"]
        token_a = token_factory(entity_a_id)

        response = test_app.post(
            "/entities", json={"name": "Entity B"}, headers={"x-token": token}
        )
        entity_b_id = response.json()["id"]
        token_b = token_factory(entity_b_id)

        # Create a transaction from Entity A to Entity B
        transaction_data = {
            "from_entity_id": entity_a_id,
            "to_entity_id": entity_b_id,
            "amount": "100.00",
            "currency": "usd",
        }
        response = test_app.post(
            "/transactions/", json=transaction_data, headers={"x-token": token_a}
        )
        transaction_id = response.json()["id"]

        # Check initial balance for Entity A and Entity B
        response = test_app.get(
            f"/balances/{entity_a_id}", headers={"x-token": token_a}
        )
        assert response.json()["completed"] == {}
        assert Decimal(response.json()["draft"]["usd"]) == Decimal("-100")
        response = test_app.get(
            f"/balances/{entity_b_id}", headers={"x-token": token_b}
        )
        assert response.json()["completed"] == {}
        assert Decimal(response.json()["draft"]["usd"]) == Decimal("100")

        # Confirm the transaction
        response = test_app.patch(
            f"/transactions/{transaction_id}",
            json={"status": "completed"},
            headers={"x-token": token_a},
        )
        assert response.status_code == status.HTTP_200_OK

        # Check balance after confirming the transaction
        response = test_app.get(
            f"/balances/{entity_a_id}", headers={"x-token": token_a}
        )
        balance_a = Decimal(response.json()["completed"]["usd"])
        assert balance_a == Decimal("-100")
        response = test_app.get(
            f"/balances/{entity_b_id}", headers={"x-token": token_b}
        )
        balance_b = Decimal(response.json()["completed"]["usd"])
        assert balance_b == Decimal("100")
