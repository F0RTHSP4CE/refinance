import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.deposit import DepositStatus


class TestCryptAPICallback:
    """Test CryptAPI callback functionality"""

    def test_successful_callback(self, test_app: TestClient, token):
        # Create a deposit
        create_response = test_app.post(
            "/deposits",
            json={
                "from_entity_id": 50,  # CryptAPI deposit provider
                "to_entity_id": 1,
                "amount": "100.00",
                "currency": "usd",
                "provider": "cryptapi",
                "details": {"info": "test deposit"},
            },
            headers={"x-token": token},
        )
        assert create_response.status_code == 200
        deposit_data = create_response.json()
        deposit_uuid = deposit_data["uuid"]

        # Simulate a successful callback from CryptAPI
        callback_response = test_app.get(
            f"/callbacks/cryptapi/{deposit_uuid}",
            params={
                "value_coin": "100.00",
                "confirmations": 1,
                "coin": "usd",
            },
        )
        assert callback_response.status_code == 200

        # Verify the deposit status is updated to COMPLETED
        get_response = test_app.get(f"/deposits/{deposit_data['id']}", headers={"x-token": token})
        assert get_response.status_code == 200
        updated_deposit = get_response.json()
        assert updated_deposit["status"] == DepositStatus.COMPLETED.value

        # Verify the transaction is created and completed
        transactions_response = test_app.get(
            "/transactions",
            params={"to_entity_id": 1, "amount_min": "100.00", "amount_max": "100.00"},
            headers={"x-token": token},
        )
        assert transactions_response.status_code == 200
        transactions = transactions_response.json()["items"]
        assert len(transactions) == 1
        assert Decimal(transactions[0]["amount"]) == Decimal("100.00")
        assert transactions[0]["status"] == "completed"
