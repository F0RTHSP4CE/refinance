from decimal import Decimal

import pytest
from app.services.stripe import StripeService
from fastapi.testclient import TestClient


class _FakeCheckoutSession:
    def __init__(self, session_id: str, url: str):
        self.id = session_id
        self.url = url
        self.status = "open"
        self.payment_status = "unpaid"


@pytest.fixture
def patch_stripe_create(monkeypatch):
    def _fake_create_checkout_session(
        self,
        *,
        amount,
        currency,
        deposit_id,
        deposit_uuid,
        actor_entity_id,
        to_entity_id,
        success_url,
        cancel_url,
    ):
        return _FakeCheckoutSession(
            session_id=f"cs_test_{deposit_id}",
            url=f"https://checkout.stripe.test/session/{deposit_id}",
        )

    monkeypatch.setattr(
        StripeService,
        "create_checkout_session",
        _fake_create_checkout_session,
    )


class TestStripeDepositEndpoints:
    def test_create_stripe_deposit(
        self, test_app: TestClient, token, patch_stripe_create
    ):
        response = test_app.post(
            "/deposits/providers/stripe",
            params={"to_entity_id": 1, "amount": "12.34", "currency": "GEL"},
            headers={"x-token": token},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["provider"] == "stripe"
        assert data["status"] == "pending"
        assert Decimal(data["amount"]) == Decimal("12.34")
        assert data["details"]["stripe"]["checkout_session_id"].startswith("cs_test_")
        assert data["details"]["stripe"]["payment_url"].startswith(
            "https://checkout.stripe.test/"
        )

    def test_stripe_webhook_completes_deposit(
        self, test_app: TestClient, token, patch_stripe_create, monkeypatch
    ):
        create = test_app.post(
            "/deposits/providers/stripe",
            params={"to_entity_id": 1, "amount": "10.00", "currency": "GEL"},
            headers={"x-token": token},
        )
        assert create.status_code == 200
        deposit_id = create.json()["id"]

        def _fake_construct_webhook_event(self, payload, signature):
            return {
                "id": "evt_test_1",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": f"cs_test_{deposit_id}",
                        "mode": "payment",
                        "payment_status": "paid",
                        "status": "complete",
                        "amount_total": 1000,
                        "currency": "gel",
                        "metadata": {"deposit_id": str(deposit_id)},
                    }
                },
            }

        monkeypatch.setattr(
            StripeService,
            "construct_webhook_event",
            _fake_construct_webhook_event,
        )

        callback = test_app.post(
            "/deposit-callbacks/stripe",
            data="{}",
            headers={"Stripe-Signature": "testsig"},
        )
        assert callback.status_code == 200

        deposit = test_app.get(f"/deposits/{deposit_id}", headers={"x-token": token})
        assert deposit.status_code == 200
        deposit_data = deposit.json()
        assert deposit_data["status"] == "completed"
        assert deposit_data["details"]["stripe"]["last_event_id"] == "evt_test_1"

    def test_stripe_poll_completes_deposit_without_webhook(
        self, test_app: TestClient, token, patch_stripe_create, monkeypatch
    ):
        create = test_app.post(
            "/deposits/providers/stripe",
            params={"to_entity_id": 1, "amount": "10.00", "currency": "GEL"},
            headers={"x-token": token},
        )
        assert create.status_code == 200
        deposit_id = create.json()["id"]

        def _fake_retrieve_checkout_session(self, session_id):
            return {
                "id": session_id,
                "mode": "payment",
                "payment_status": "paid",
                "status": "complete",
                "amount_total": 1000,
                "currency": "gel",
            }

        monkeypatch.setattr(
            StripeService,
            "retrieve_checkout_session",
            _fake_retrieve_checkout_session,
        )

        poll = test_app.post("/tasks/stripe-poll/run", headers={"x-token": token})
        assert poll.status_code == 200
        assert poll.json()["result"] >= 1

        deposit = test_app.get(f"/deposits/{deposit_id}", headers={"x-token": token})
        assert deposit.status_code == 200
        assert deposit.json()["status"] == "completed"

    def test_stripe_poll_marks_expired_deposit_cancelled(
        self, test_app: TestClient, token, patch_stripe_create, monkeypatch
    ):
        create = test_app.post(
            "/deposits/providers/stripe",
            params={"to_entity_id": 1, "amount": "10.00", "currency": "GEL"},
            headers={"x-token": token},
        )
        assert create.status_code == 200
        deposit_id = create.json()["id"]

        def _fake_retrieve_checkout_session(self, session_id):
            return {
                "id": session_id,
                "mode": "payment",
                "payment_status": "unpaid",
                "status": "expired",
                "amount_total": 1000,
                "currency": "gel",
            }

        monkeypatch.setattr(
            StripeService,
            "retrieve_checkout_session",
            _fake_retrieve_checkout_session,
        )

        poll = test_app.post("/tasks/stripe-poll/run", headers={"x-token": token})
        assert poll.status_code == 200
        assert poll.json()["result"] >= 1

        deposit = test_app.get(f"/deposits/{deposit_id}", headers={"x-token": token})
        assert deposit.status_code == 200
        assert deposit.json()["status"] == "cancelled"
