import time

from fastapi import status
from fastapi.testclient import TestClient


class TestBalanceServiceCache:
    """Test cache functionality in BalanceService"""

    def test_cache_functionality(self, test_app: TestClient, token_factory, token):
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

        response = test_app.post(
            "/entities", json={"name": "Entity C"}, headers={"x-token": token}
        )
        entity_c_id = response.json()["id"]
        token_c = token_factory(entity_c_id)

        # Create transactions between entities
        transactions = [
            {
                "from_entity_id": entity_a_id,
                "to_entity_id": entity_b_id,
                "amount": "100.00",
                "currency": "usd",
            },
            {
                "from_entity_id": entity_a_id,
                "to_entity_id": entity_c_id,
                "amount": "200.00",
                "currency": "usd",
            },
            {
                "from_entity_id": entity_b_id,
                "to_entity_id": entity_c_id,
                "amount": "150.00",
                "currency": "usd",
            },
        ]

        for transaction_data in transactions:
            response = test_app.post(
                "/transactions/",
                json=transaction_data,
                headers={"x-token": token_factory(transaction_data["from_entity_id"])},
            )
            assert response.status_code == status.HTTP_200_OK
            transaction_id = response.json()["id"]

            # Confirm the transaction
            response = test_app.patch(
                f"/transactions/{transaction_id}",
                json={"confirmed": True},
                headers={"x-token": token_factory(transaction_data["from_entity_id"])},
            )
            assert response.status_code == status.HTTP_200_OK

        # Get initial balances using the cached method
        response = test_app.get(
            f"/balances/{entity_a_id}", headers={"x-token": token_a}
        )
        cached_balance_a = response.json()
        response = test_app.get(
            f"/balances/{entity_b_id}", headers={"x-token": token_b}
        )
        cached_balance_b = response.json()
        response = test_app.get(
            f"/balances/{entity_c_id}", headers={"x-token": token_c}
        )
        cached_balance_c = response.json()

        # Expected balances after transactions
        expected_balance_a = {"confirmed": {"usd": "-300.00"}, "non_confirmed": {}}
        expected_balance_b = {"confirmed": {"usd": "-50.00"}, "non_confirmed": {}}
        expected_balance_c = {"confirmed": {"usd": "350.00"}, "non_confirmed": {}}

        assert cached_balance_a == expected_balance_a
        assert cached_balance_b == expected_balance_b
        assert cached_balance_c == expected_balance_c

        # Wait to simulate cache usage and check balances again
        time.sleep(1)
        response = test_app.get(
            f"/balances/{entity_a_id}", headers={"x-token": token_a}
        )
        cached_balance_a_again = response.json()
        response = test_app.get(
            f"/balances/{entity_b_id}", headers={"x-token": token_b}
        )
        cached_balance_b_again = response.json()
        response = test_app.get(
            f"/balances/{entity_c_id}", headers={"x-token": token_c}
        )
        cached_balance_c_again = response.json()

        assert cached_balance_a_again == cached_balance_a
        assert cached_balance_b_again == cached_balance_b
        assert cached_balance_c_again == cached_balance_c

        # Invalidate the cache and check balances again
        test_app.get(
            f"/balances/{entity_a_id}/invalidate", headers={"x-token": token_a}
        )
        test_app.get(
            f"/balances/{entity_b_id}/invalidate", headers={"x-token": token_b}
        )
        test_app.get(
            f"/balances/{entity_c_id}/invalidate", headers={"x-token": token_c}
        )

        response = test_app.get(
            f"/balances/{entity_a_id}", headers={"x-token": token_a}
        )
        uncached_balance_a = response.json()
        response = test_app.get(
            f"/balances/{entity_b_id}", headers={"x-token": token_b}
        )
        uncached_balance_b = response.json()
        response = test_app.get(
            f"/balances/{entity_c_id}", headers={"x-token": token_c}
        )
        uncached_balance_c = response.json()

        assert uncached_balance_a == expected_balance_a
        assert uncached_balance_b == expected_balance_b
        assert uncached_balance_c == expected_balance_c
