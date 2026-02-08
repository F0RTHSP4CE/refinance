from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="class")
def entity_one(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "Treasury Test Entity One"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="class")
def entity_two(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "Treasury Test Entity Two"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="class")
def treasury_one(test_app: TestClient, token):
    response = test_app.post(
        "/treasuries",
        json={"name": "Test Treasury 1"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="class")
def treasury_two(test_app: TestClient, token):
    response = test_app.post(
        "/treasuries",
        json={"name": "Test Treasury 2"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()


class TestTreasuryEndpoints:
    def test_create_treasury(self, test_app: TestClient, token):
        response = test_app.post(
            "/treasuries",
            json={"name": "New Treasury"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Treasury"
        assert "balances" in data

    def test_get_treasury(self, test_app: TestClient, token, treasury_one):
        treasury_id = treasury_one["id"]
        response = test_app.get(
            f"/treasuries/{treasury_id}", headers={"x-token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == treasury_id
        assert "balances" in data
        assert "completed" in data["balances"]
        assert "draft" in data["balances"]

    def test_get_all_treasuries(
        self, test_app: TestClient, token, treasury_one, treasury_two
    ):
        response = test_app.get("/treasuries", headers={"x-token": token})
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 2
        for item in data["items"]:
            assert "balances" in item

    def test_update_treasury(self, test_app: TestClient, token):
        # Create a treasury to be updated
        response = test_app.post(
            "/treasuries",
            json={"name": "Updatable Treasury"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        treasury_one = response.json()
        treasury_id = treasury_one["id"]
        response = test_app.patch(
            f"/treasuries/{treasury_id}",
            json={"name": "Updated Treasury Name"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Treasury Name"

    def test_delete_treasury(self, test_app: TestClient, token):
        # Create a treasury to be deleted
        response = test_app.post(
            "/treasuries",
            json={"name": "To Be Deleted"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        treasury_id = response.json()["id"]

        # Delete the treasury
        delete_response = test_app.delete(
            f"/treasuries/{treasury_id}", headers={"x-token": token}
        )
        assert delete_response.status_code == 200

        # Verify it's gone
        get_response = test_app.get(
            f"/treasuries/{treasury_id}", headers={"x-token": token}
        )
        assert get_response.status_code == 418

    def test_delete_treasury_in_use_fails(
        self, test_app: TestClient, token, entity_one, entity_two
    ):
        # Create a treasury to be used
        response = test_app.post(
            "/treasuries",
            json={"name": "In-Use Treasury"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        treasury_one = response.json()
        # Create a transaction using the treasury
        test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one["id"],
                "to_entity_id": entity_two["id"],
                "from_treasury_id": treasury_one["id"],
                "amount": "10.00",
                "currency": "USD",
            },
            headers={"x-token": token},
        )

        # Attempt to delete the treasury
        delete_response = test_app.delete(
            f"/treasuries/{treasury_one['id']}", headers={"x-token": token}
        )
        assert delete_response.status_code == 418  # TreasuryDeletionError

    def test_transaction_overdraft_prevention(
        self, test_app: TestClient, token, entity_one, entity_two
    ):
        # Create a treasury for the overdraft test
        response = test_app.post(
            "/treasuries",
            json={"name": "Overdraft Test Treasury"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        treasury_one = response.json()
        # Treasury has 0 balance. Create a draft transaction.
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one["id"],
                "to_entity_id": entity_two["id"],
                "from_treasury_id": treasury_one["id"],
                "amount": "100.00",
                "currency": "USD",
                "status": "draft",
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200
        tx_id = tx_response.json()["id"]

        # Attempt to complete the transaction, which should fail due to overdraft
        update_response = test_app.patch(
            f"/transactions/{tx_id}",
            json={"status": "completed"},
            headers={"x-token": token},
        )
        assert update_response.status_code == 418  # TransactionWillOverdraftTreasury

    def test_completed_transaction_overdraft_prevention_on_create(
        self, test_app: TestClient, token, entity_one, entity_two
    ):
        response = test_app.post(
            "/treasuries",
            json={"name": "Overdraft Create Treasury"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        treasury_one = response.json()

        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one["id"],
                "to_entity_id": entity_two["id"],
                "from_treasury_id": treasury_one["id"],
                "amount": "100.00",
                "currency": "USD",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 418  # TransactionWillOverdraftTreasury

    def test_treasury_balances_in_schema(
        self, test_app: TestClient, token, entity_one, entity_two
    ):
        # Create a new treasury for this test
        response = test_app.post(
            "/treasuries",
            json={"name": "Balance Test Treasury"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        treasury_one = response.json()
        treasury_id = treasury_one["id"]
        # 1. Initial balance check
        response = test_app.get(
            f"/treasuries/{treasury_id}", headers={"x-token": token}
        )
        assert response.status_code == 200
        balances = response.json()["balances"]
        assert balances["completed"] == {}
        assert balances["draft"] == {}

        # 2. Add a completed transaction
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one["id"],
                "to_entity_id": entity_two["id"],
                "to_treasury_id": treasury_id,
                "amount": "100.00",
                "currency": "USD",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200

        # 3. Add a draft transaction
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_one["id"],
                "to_entity_id": entity_two["id"],
                "to_treasury_id": treasury_id,
                "amount": "50.00",
                "currency": "USD",
                "status": "draft",
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200

        # 4. Final balance check
        response = test_app.get(
            f"/treasuries/{treasury_id}", headers={"x-token": token}
        )
        assert response.status_code == 200
        balances = response.json()["balances"]
        assert Decimal(balances["completed"]["usd"]) == Decimal("100.00")
        assert Decimal(balances["draft"]["usd"]) == Decimal("50.00")
