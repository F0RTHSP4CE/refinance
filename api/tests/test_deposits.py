import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.models.deposit import DepositStatus


class TestDepositEndpoints:
    """Test API endpoints for deposits"""

    def test_create_deposit(self, test_app: TestClient, token):
        response = test_app.post(
            "/deposits",
            json={
                "from_entity_id": 2,
                "to_entity_id": 1,
                "amount": "100.00",
                "currency": "usd",
                "provider": "test_provider",
                "details": {"info": "test deposit"},
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["from_entity_id"] == 2
        assert data["to_entity_id"] == 1
        assert Decimal(data["amount"]) == Decimal("100.00")
        assert data["currency"] == "usd"
        assert data["provider"] == "test_provider"
        assert data["status"] == DepositStatus.PENDING.value

    def test_read_deposit(self, test_app: TestClient, token):
        create_response = test_app.post(
            "/deposits",
            json={
                "from_entity_id": 2,
                "to_entity_id": 1,
                "amount": "50.00",
                "currency": "usd",
                "provider": "test_provider",
                "details": {"info": "test deposit"},
            },
            headers={"x-token": token},
        )
        deposit_id = create_response.json()["id"]
        response = test_app.get(f"/deposits/{deposit_id}", headers={"x-token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == deposit_id

    def test_update_deposit(self, test_app: TestClient, token):
        create_response = test_app.post(
            "/deposits",
            json={
                "from_entity_id": 2,
                "to_entity_id": 1,
                "amount": "75.00",
                "currency": "usd",
                "provider": "test_provider",
                "details": {"info": "test deposit"},
            },
            headers={"x-token": token},
        )
        deposit_id = create_response.json()["id"]
        update_response = test_app.patch(
            f"/deposits/{deposit_id}",
            json={"details": {"info": "updated deposit"}},
            headers={"x-token": token},
        )
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["details"]["info"] == "updated deposit"

    @pytest.mark.xfail(reason="Delete operation is not implemented")
    def test_delete_deposit(self, test_app: TestClient, token):
        create_response = test_app.post(
            "/deposits",
            json={
                "from_entity_id": 2,
                "to_entity_id": 1,
                "amount": "30.00",
                "currency": "usd",
                "provider": "test_provider",
                "details": {"info": "test deposit"},
            },
            headers={"x-token": token},
        )
        deposit_id = create_response.json()["id"]
        delete_response = test_app.delete(f"/deposits/{deposit_id}", headers={"x-token": token})
        assert delete_response.status_code == 200
