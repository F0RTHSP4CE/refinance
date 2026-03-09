"""Tests for Keepz deposit provider cleanup behavior."""

from app.errors.keepz import KeepzAuthRequired
from app.services.keepz import KeepzService
from fastapi.testclient import TestClient


class TestKeepzDepositProvider:
    def test_keepz_create_deposit_requires_real_keepz_auth(
        self, test_app: TestClient, token: str, monkeypatch
    ):
        target_response = test_app.post(
            "/entities",
            json={"name": "Keepz Deposit Target"},
            headers={"x-token": token},
        )
        assert target_response.status_code == 200
        target_entity_id = target_response.json()["id"]

        def _raise_keepz_auth_required(self, *args, **kwargs):
            raise KeepzAuthRequired()

        monkeypatch.setattr(
            KeepzService,
            "create_payment_link",
            _raise_keepz_auth_required,
        )

        response = test_app.post(
            "/deposits/providers/keepz",
            params={
                "to_entity_id": target_entity_id,
                "amount": "25.00",
                "currency": "gel",
            },
            headers={"x-token": token},
        )

        assert response.status_code == 418
        data = response.json()
        assert data["error_code"] == 7401
        assert data["error"] == "Keepz authentication required"

    def test_keepz_dev_completion_route_is_removed(
        self, test_app: TestClient, token: str
    ):
        response = test_app.post(
            "/deposits/1/complete-dev",
            headers={"x-token": token},
        )
        assert response.status_code == 404
