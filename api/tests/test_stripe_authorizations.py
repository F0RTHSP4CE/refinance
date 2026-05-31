from decimal import Decimal

import pytest
from app.services.stripe import StripeInvoiceData, StripeService
from fastapi.testclient import TestClient


class _FakeCheckoutSession:
    def __init__(self, session_id: str, url: str):
        self.id = session_id
        self.url = url


class _FakePaymentIntent:
    def __init__(self, intent_id: str, status: str = "succeeded"):
        self.id = intent_id
        self.status = status

    def to_dict(self):
        return {"id": self.id, "status": self.status}


@pytest.fixture
def patch_setup_session(monkeypatch):
    def _fake_create_subscription_checkout_session(
        self,
        *,
        entity_id,
        amount,
        currency,
        donation_comment=None,
        success_url,
        cancel_url,
    ):
        return _FakeCheckoutSession(
            session_id=f"cs_setup_{entity_id}_guest_static",
            url=f"https://checkout.stripe.test/setup/{entity_id}",
        )

    monkeypatch.setattr(
        StripeService,
        "create_subscription_checkout_session",
        _fake_create_subscription_checkout_session,
    )


class TestStripeAuthorizationEndpoints:
    def test_create_setup_session(
        self, test_app: TestClient, token, patch_setup_session
    ):
        response = test_app.post(
            "/deposits/providers/stripe/authorizations/setup-session",
            params={
                "mode": "guest_static",
                "entity_id": 14,
                "static_amount": "10.00",
                "static_currency": "GEL",
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["checkout_session_id"].startswith("cs_setup_")
        assert payload["checkout_session_url"].startswith(
            "https://checkout.stripe.test/"
        )

    def test_setup_webhook_creates_authorization(
        self, test_app: TestClient, token, monkeypatch
    ):
        def _fake_construct_webhook_event(self, payload, signature):
            return {
                "id": "evt_setup_1",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_setup_1",
                        "mode": "setup",
                        "setup_intent": "si_test_1",
                        "metadata": {
                            "entity_id": "1",
                            "mode": "entity_dynamic",
                            "static_amount": "0.00",
                            "static_currency": "",
                        },
                    }
                },
            }

        def _fake_retrieve_setup_intent(self, setup_intent_id):
            return {
                "id": setup_intent_id,
                "payment_method": "pm_test_1",
                "customer": "cus_test_1",
            }

        def _fake_retrieve_payment_method(self, payment_method_id):
            return {
                "id": payment_method_id,
                "card": {
                    "brand": "visa",
                    "last4": "4242",
                    "exp_month": 12,
                    "exp_year": 2035,
                },
            }

        monkeypatch.setattr(
            StripeService, "construct_webhook_event", _fake_construct_webhook_event
        )
        monkeypatch.setattr(
            StripeService, "retrieve_setup_intent", _fake_retrieve_setup_intent
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )

        callback = test_app.post(
            "/deposit-callbacks/stripe",
            data="{}",
            headers={"Stripe-Signature": "testsig"},
        )
        assert callback.status_code == 200

        listing = test_app.get(
            "/deposits/providers/stripe/authorizations",
            params={"entity_id": 1},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert len(items) >= 1
        auth = items[0]
        assert auth["stripe_payment_method_id"] == "pm_test_1"
        assert auth["active"] is True
        assert auth["card_last4"] == "4242"

    def test_sync_session_creates_authorization_without_webhook(
        self, test_app: TestClient, token, monkeypatch
    ):
        def _fake_retrieve_checkout_session(
            self, session_id, expand_setup_intent=False
        ):
            return {
                "id": session_id,
                "mode": "setup",
                "setup_intent": "si_sync_1",
                "metadata": {
                    "entity_id": "1",
                    "mode": "entity_dynamic",
                    "static_amount": "0.00",
                    "static_currency": "",
                },
            }

        def _fake_retrieve_setup_intent(self, setup_intent_id):
            return {
                "id": setup_intent_id,
                "payment_method": "pm_sync_1",
                "customer": "cus_sync_1",
            }

        def _fake_retrieve_payment_method(self, payment_method_id):
            return {
                "id": payment_method_id,
                "card": {
                    "brand": "mastercard",
                    "last4": "4444",
                    "exp_month": 10,
                    "exp_year": 2034,
                },
            }

        monkeypatch.setattr(
            StripeService,
            "retrieve_checkout_session",
            _fake_retrieve_checkout_session,
        )
        monkeypatch.setattr(
            StripeService, "retrieve_setup_intent", _fake_retrieve_setup_intent
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )

        sync = test_app.post(
            "/deposits/providers/stripe/authorizations/sync-session",
            params={"checkout_session_id": "cs_setup_sync_1"},
            headers={"x-token": token},
        )
        assert sync.status_code == 200
        assert sync.json()["stripe_payment_method_id"] == "pm_sync_1"

        listing = test_app.get(
            "/deposits/providers/stripe/authorizations",
            params={"entity_id": 1},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        sync_auth = next(
            x for x in items if x["stripe_payment_method_id"] == "pm_sync_1"
        )
        assert sync_auth["card_last4"] == "4444"

    def test_sync_session_handles_checkout_object_with_to_dict(
        self, test_app: TestClient, token, monkeypatch
    ):
        class _CheckoutObject:
            def to_dict(self):
                return {
                    "id": "cs_setup_sync_obj",
                    "mode": "setup",
                    "setup_intent": "si_sync_obj",
                    "metadata": {
                        "entity_id": "1",
                        "mode": "entity_dynamic",
                        "static_amount": "0.00",
                        "static_currency": "",
                    },
                }

        def _fake_retrieve_checkout_session(
            self, session_id, expand_setup_intent=False
        ):
            return _CheckoutObject()

        def _fake_retrieve_setup_intent(self, setup_intent_id):
            return {
                "id": setup_intent_id,
                "payment_method": "pm_sync_obj",
                "customer": "cus_sync_obj",
            }

        def _fake_retrieve_payment_method(self, payment_method_id):
            return {
                "id": payment_method_id,
                "card": {
                    "brand": "visa",
                    "last4": "1111",
                    "exp_month": 1,
                    "exp_year": 2036,
                },
            }

        monkeypatch.setattr(
            StripeService,
            "retrieve_checkout_session",
            _fake_retrieve_checkout_session,
        )
        monkeypatch.setattr(
            StripeService, "retrieve_setup_intent", _fake_retrieve_setup_intent
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )

        sync = test_app.post(
            "/deposits/providers/stripe/authorizations/sync-session",
            params={"checkout_session_id": "cs_setup_sync_obj"},
            headers={"x-token": token},
        )
        assert sync.status_code == 200
        assert sync.json()["stripe_payment_method_id"] == "pm_sync_obj"

    def test_sync_session_uses_setup_intent_metadata_when_session_metadata_missing(
        self, test_app: TestClient, token, monkeypatch
    ):
        def _fake_retrieve_checkout_session(
            self, session_id, expand_setup_intent=False
        ):
            assert expand_setup_intent is True
            return {
                "id": session_id,
                "mode": "setup",
                "setup_intent": "si_sync_meta_fallback",
                "metadata": {},
            }

        def _fake_retrieve_setup_intent(self, setup_intent_id):
            return {
                "id": setup_intent_id,
                "payment_method": "pm_sync_meta_fallback",
                "customer": "cus_sync_meta_fallback",
                "metadata": {
                    "entity_id": "1",
                    "mode": "entity_dynamic",
                    "static_amount": "0.00",
                    "static_currency": "",
                },
            }

        def _fake_retrieve_payment_method(self, payment_method_id):
            return {
                "id": payment_method_id,
                "card": {
                    "brand": "visa",
                    "last4": "1234",
                    "exp_month": 5,
                    "exp_year": 2038,
                },
            }

        monkeypatch.setattr(
            StripeService,
            "retrieve_checkout_session",
            _fake_retrieve_checkout_session,
        )
        monkeypatch.setattr(
            StripeService, "retrieve_setup_intent", _fake_retrieve_setup_intent
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )

        sync = test_app.post(
            "/deposits/providers/stripe/authorizations/sync-session",
            params={"checkout_session_id": "cs_sync_meta_fallback", "entity_id": 1},
            headers={"x-token": token},
        )
        assert sync.status_code == 200
        assert sync.json()["stripe_payment_method_id"] == "pm_sync_meta_fallback"


class TestStripeAuthorizationChargeFallback:
    def test_stripe_entity_charge_debug_endpoint_reports_reason(
        self,
        test_app: TestClient,
        token,
    ):
        resident_resp = test_app.post(
            "/entities",
            json={"name": "resident_debug", "tag_ids": [2], "auth": {}},
            headers={"x-token": token},
        )
        assert resident_resp.status_code == 200
        resident_id = resident_resp.json()["id"]

        debug_resp = test_app.get(
            "/tasks/stripe-entity-charge/debug",
            params={"entity_id": resident_id},
            headers={"x-token": token},
        )
        assert debug_resp.status_code == 200
        payload = debug_resp.json()
        assert payload["entity_id"] == resident_id
        assert payload["has_active_authorization"] is False
        assert payload["will_charge"] is False
        assert "No active" in payload["reason"]

    def test_weekly_dynamic_charge_processes_negative_balance_without_invoices(
        self,
        test_app: TestClient,
        token,
        token_factory,
        monkeypatch,
    ):
        resident_resp = test_app.post(
            "/entities",
            json={"name": "resident_negative_balance", "tag_ids": [2], "auth": {}},
            headers={"x-token": token},
        )
        assert resident_resp.status_code == 200
        resident_id = resident_resp.json()["id"]

        def _fake_construct_webhook_event(self, payload, signature):
            return {
                "id": "evt_setup_negative",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_setup_negative",
                        "mode": "setup",
                        "setup_intent": "si_negative_balance",
                        "metadata": {
                            "entity_id": str(resident_id),
                            "mode": "entity_dynamic",
                            "static_amount": "0.00",
                            "static_currency": "",
                        },
                    }
                },
            }

        def _fake_retrieve_setup_intent(self, setup_intent_id):
            return {
                "id": setup_intent_id,
                "payment_method": "pm_negative_balance",
                "customer": "cus_negative_balance",
            }

        def _fake_retrieve_payment_method(self, payment_method_id):
            return {
                "id": payment_method_id,
                "card": {
                    "brand": "visa",
                    "last4": "9191",
                    "exp_month": 11,
                    "exp_year": 2037,
                },
            }

        def _fake_create_payment_intent(
            self,
            *,
            amount,
            currency,
            customer_id,
            payment_method_id,
            idempotency_key,
            metadata,
        ):
            assert amount == Decimal("10.00")
            assert currency == "usd"
            return _FakePaymentIntent(intent_id="pi_negative_balance")

        monkeypatch.setattr(
            StripeService, "construct_webhook_event", _fake_construct_webhook_event
        )
        monkeypatch.setattr(
            StripeService, "retrieve_setup_intent", _fake_retrieve_setup_intent
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )
        monkeypatch.setattr(
            StripeService,
            "create_off_session_payment_intent",
            _fake_create_payment_intent,
        )

        callback = test_app.post(
            "/deposit-callbacks/stripe",
            data="{}",
            headers={"Stripe-Signature": "testsig"},
        )
        assert callback.status_code == 200

        tx_resp = test_app.post(
            "/transactions/",
            json={
                "from_entity_id": resident_id,
                "to_entity_id": 1,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token_factory(resident_id)},
        )
        assert tx_resp.status_code == 200

        run = test_app.post(
            "/tasks/stripe-entity-charge/run", headers={"x-token": token}
        )
        assert run.status_code == 200
        assert run.json()["result"] >= 1

        listing = test_app.get(
            "/deposits",
            params={"provider": "stripe", "to_entity_id": resident_id, "limit": 20},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert len(items) >= 1
        charge_deposit = items[0]
        assert charge_deposit["status"] == "completed"
        assert Decimal(charge_deposit["amount"]) == Decimal("10.00")
        assert any(
            str(tag.get("name") or "").lower() == "automatic"
            for tag in (charge_deposit.get("tags") or [])
        )

    def test_weekly_dynamic_charge_dry_run_returns_plan_without_creating_deposit(
        self,
        test_app: TestClient,
        token,
        token_factory,
        monkeypatch,
    ):
        resident_resp = test_app.post(
            "/entities",
            json={"name": "resident_dry_run", "tag_ids": [2], "auth": {}},
            headers={"x-token": token},
        )
        assert resident_resp.status_code == 200
        resident_id = resident_resp.json()["id"]

        def _fake_construct_webhook_event(self, payload, signature):
            return {
                "id": "evt_setup_dry_run",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_setup_dry_run",
                        "mode": "setup",
                        "setup_intent": "si_dry_run",
                        "metadata": {
                            "entity_id": str(resident_id),
                            "mode": "entity_dynamic",
                            "static_amount": "0.00",
                            "static_currency": "",
                        },
                    }
                },
            }

        def _fake_retrieve_setup_intent(self, setup_intent_id):
            return {
                "id": setup_intent_id,
                "payment_method": "pm_dry_run",
                "customer": "cus_dry_run",
            }

        def _fake_retrieve_payment_method(self, payment_method_id):
            return {
                "id": payment_method_id,
                "card": {
                    "brand": "visa",
                    "last4": "9898",
                    "exp_month": 9,
                    "exp_year": 2038,
                },
            }

        monkeypatch.setattr(
            StripeService, "construct_webhook_event", _fake_construct_webhook_event
        )
        monkeypatch.setattr(
            StripeService, "retrieve_setup_intent", _fake_retrieve_setup_intent
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )

        callback = test_app.post(
            "/deposit-callbacks/stripe",
            data="{}",
            headers={"Stripe-Signature": "testsig"},
        )
        assert callback.status_code == 200

        tx_resp = test_app.post(
            "/transactions/",
            json={
                "from_entity_id": resident_id,
                "to_entity_id": 1,
                "amount": "12.00",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token_factory(resident_id)},
        )
        assert tx_resp.status_code == 200

        run = test_app.post(
            "/tasks/stripe-entity-charge/run",
            params={"dry_run": True},
            headers={"x-token": token},
        )
        assert run.status_code == 200
        payload = run.json()
        assert payload["task"] == "stripe-entity-charge"
        assert payload["result"] >= 1
        assert (payload.get("details") or {}).get("dry_run") is True
        plans = (payload.get("details") or {}).get("plans") or []
        planned = next((x for x in plans if x.get("entity_id") == resident_id), None)
        assert planned is not None
        assert planned["will_charge"] is True
        assert planned["minimum_topup_currency"] == "usd"

        listing = test_app.get(
            "/deposits",
            params={"provider": "stripe", "to_entity_id": resident_id, "limit": 20},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert len(items) == 0

    def test_weekly_dynamic_charge_fallback_to_second_authorization(
        self,
        test_app: TestClient,
        token,
        monkeypatch,
    ):
        resident_resp = test_app.post(
            "/entities",
            json={"name": "resident_card_fallback", "tag_ids": [2], "auth": {}},
            headers={"x-token": token},
        )
        assert resident_resp.status_code == 200
        resident_id = resident_resp.json()["id"]

        # Create a pending invoice for this resident.
        inv_resp = test_app.post(
            "/invoices",
            json={
                "from_entity_id": resident_id,
                "to_entity_id": 1,
                "amounts": [{"currency": "usd", "amount": "15.00"}],
                "tag_ids": [3],
            },
            headers={"x-token": token},
        )
        assert inv_resp.status_code == 200

        setup_state = {"idx": 0}

        def _fake_construct_webhook_event(self, payload, signature):
            setup_state["idx"] += 1
            idx = setup_state["idx"]
            return {
                "id": f"evt_setup_{idx}",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": f"cs_setup_{idx}",
                        "mode": "setup",
                        "setup_intent": f"si_test_{idx}",
                        "metadata": {
                            "entity_id": str(resident_id),
                            "mode": "entity_dynamic",
                            "static_amount": "0.00",
                            "static_currency": "",
                        },
                    }
                },
            }

        def _fake_retrieve_setup_intent(self, setup_intent_id):
            if setup_intent_id.endswith("1"):
                payment_method = "pm_fail"
            else:
                payment_method = "pm_ok"
            return {
                "id": setup_intent_id,
                "payment_method": payment_method,
                "customer": "cus_resident",
            }

        def _fake_retrieve_payment_method(self, payment_method_id):
            last4 = "0002" if payment_method_id == "pm_fail" else "4242"
            return {
                "id": payment_method_id,
                "card": {
                    "brand": "visa",
                    "last4": last4,
                    "exp_month": 12,
                    "exp_year": 2035,
                },
            }

        def _fake_create_payment_intent(
            self,
            *,
            amount,
            currency,
            customer_id,
            payment_method_id,
            idempotency_key,
            metadata,
        ):
            if payment_method_id == "pm_fail":
                raise Exception("card declined")
            return _FakePaymentIntent(intent_id="pi_success")

        monkeypatch.setattr(
            StripeService, "construct_webhook_event", _fake_construct_webhook_event
        )
        monkeypatch.setattr(
            StripeService, "retrieve_setup_intent", _fake_retrieve_setup_intent
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )
        monkeypatch.setattr(
            StripeService,
            "create_off_session_payment_intent",
            _fake_create_payment_intent,
        )

        # Register two setup authorizations for same entity.
        for _ in range(2):
            callback = test_app.post(
                "/deposit-callbacks/stripe",
                data="{}",
                headers={"Stripe-Signature": "testsig"},
            )
            assert callback.status_code == 200

        run = test_app.post(
            "/tasks/stripe-entity-charge/run", headers={"x-token": token}
        )
        assert run.status_code == 200
        assert run.json()["result"] >= 1

        listing = test_app.get(
            "/deposits",
            params={"provider": "stripe", "to_entity_id": resident_id, "limit": 20},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert len(items) >= 1
        charge_deposit = items[0]
        assert charge_deposit["status"] == "completed"
        assert any(
            str(tag.get("name") or "").lower() == "automatic"
            for tag in (charge_deposit.get("tags") or [])
        )

        attempts = ((charge_deposit.get("details") or {}).get("stripe") or {}).get(
            "attempts"
        ) or []
        assert len(attempts) >= 2
        assert attempts[0]["result"] == "failed"
        assert attempts[1]["result"] == "success"

        auths = test_app.get(
            "/deposits/providers/stripe/authorizations",
            params={"entity_id": resident_id},
            headers={"x-token": token},
        )
        assert auths.status_code == 200
        auth_items = auths.json()["items"]
        fail_auth = next(
            x for x in auth_items if x["stripe_payment_method_id"] == "pm_fail"
        )
        ok_auth = next(
            x for x in auth_items if x["stripe_payment_method_id"] == "pm_ok"
        )
        assert fail_auth["consecutive_error_count"] >= 1
        assert ok_auth["consecutive_error_count"] == 0


class TestStripeSubscriptionInvoicePaid:
    """Test that invoice.paid webhooks from Stripe subscriptions create deposits."""

    def _register_subscription_auth(
        self, test_app: TestClient, token, monkeypatch, *, entity_id: int
    ) -> str:
        """Register a GUEST_STATIC subscription authorization via webhook and return the subscription_id."""
        subscription_id = f"sub_test_{entity_id}"

        def _fake_construct_webhook_event(self, payload, signature):
            return {
                "id": f"evt_sub_setup_{entity_id}",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": f"cs_sub_{entity_id}",
                        "mode": "subscription",
                        "subscription": subscription_id,
                        "customer": f"cus_sub_{entity_id}",
                        "metadata": {
                            "entity_id": str(entity_id),
                            "mode": "guest_static",
                            "static_amount": "10.00",
                            "static_currency": "usd",
                        },
                    }
                },
            }

        def _fake_retrieve_subscription(self, sub_id):
            return {
                "id": sub_id,
                "default_payment_method": f"pm_sub_{entity_id}",
            }

        def _fake_retrieve_payment_method(self, pm_id):
            return {
                "id": pm_id,
                "card": {
                    "brand": "visa",
                    "last4": "4242",
                    "exp_month": 12,
                    "exp_year": 2035,
                },
            }

        monkeypatch.setattr(
            StripeService, "construct_webhook_event", _fake_construct_webhook_event
        )
        monkeypatch.setattr(
            StripeService, "retrieve_subscription", _fake_retrieve_subscription
        )
        monkeypatch.setattr(
            StripeService, "retrieve_payment_method", _fake_retrieve_payment_method
        )

        callback = test_app.post(
            "/deposit-callbacks/stripe",
            data="{}",
            headers={"Stripe-Signature": "testsig"},
        )
        assert callback.status_code == 200
        return subscription_id

    def test_invoice_paid_webhook_creates_completed_deposit(
        self, test_app: TestClient, token, monkeypatch
    ):
        entity_resp = test_app.post(
            "/entities",
            json={"name": "guest_subscriber", "tag_ids": [], "auth": {}},
            headers={"x-token": token},
        )
        assert entity_resp.status_code == 200
        entity_id = entity_resp.json()["id"]

        subscription_id = self._register_subscription_auth(
            test_app, token, monkeypatch, entity_id=entity_id
        )

        def _fake_construct_invoice_event(self, payload, signature):
            return {
                "id": "evt_invoice_paid_1",
                "type": "invoice.paid",
                "data": {
                    "object": {
                        "id": "in_test_001",
                        "parent": {
                            "type": "subscription_details",
                            "subscription_details": {"subscription": subscription_id},
                        },
                        "amount_paid": 1000,  # $10.00 in cents
                        "currency": "usd",
                        "billing_reason": "subscription_cycle",
                    }
                },
            }

        monkeypatch.setattr(
            StripeService, "construct_webhook_event", _fake_construct_invoice_event
        )

        callback = test_app.post(
            "/deposit-callbacks/stripe",
            data="{}",
            headers={"Stripe-Signature": "testsig"},
        )
        assert callback.status_code == 200

        listing = test_app.get(
            "/deposits",
            params={"provider": "stripe", "to_entity_id": entity_id, "limit": 20},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert len(items) == 1
        deposit = items[0]
        assert deposit["status"] == "completed"
        from decimal import Decimal

        assert Decimal(deposit["amount"]) == Decimal("10.00")
        assert deposit["currency"] == "usd"
        stripe_details = (deposit.get("details") or {}).get("stripe") or {}
        assert stripe_details.get("mode") == "subscription_invoice"
        assert stripe_details.get("invoice_id") == "in_test_001"

    def test_invoice_paid_webhook_is_idempotent(
        self, test_app: TestClient, token, monkeypatch
    ):
        entity_resp = test_app.post(
            "/entities",
            json={"name": "guest_subscriber_idem", "tag_ids": [], "auth": {}},
            headers={"x-token": token},
        )
        assert entity_resp.status_code == 200
        entity_id = entity_resp.json()["id"]

        subscription_id = self._register_subscription_auth(
            test_app, token, monkeypatch, entity_id=entity_id
        )

        def _fake_construct_invoice_event(self, payload, signature):
            return {
                "id": "evt_invoice_idem",
                "type": "invoice.paid",
                "data": {
                    "object": {
                        "id": "in_idem_001",
                        "parent": {
                            "type": "subscription_details",
                            "subscription_details": {"subscription": subscription_id},
                        },
                        "amount_paid": 500,
                        "currency": "gel",
                        "billing_reason": "subscription_cycle",
                    }
                },
            }

        monkeypatch.setattr(
            StripeService, "construct_webhook_event", _fake_construct_invoice_event
        )

        # Send the same invoice.paid event twice
        for _ in range(2):
            callback = test_app.post(
                "/deposit-callbacks/stripe",
                data="{}",
                headers={"Stripe-Signature": "testsig"},
            )
            assert callback.status_code == 200

        listing = test_app.get(
            "/deposits",
            params={"provider": "stripe", "to_entity_id": entity_id, "limit": 20},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert len(items) == 1  # only one deposit despite two webhook deliveries

    def test_stripe_poll_recovers_missed_subscription_invoice(
        self, test_app: TestClient, token, monkeypatch
    ):
        """Verify /tasks/stripe-poll/run creates a deposit for a paid invoice not seen via webhook."""
        entity_resp = test_app.post(
            "/entities",
            json={"name": "guest_subscriber_poll", "tag_ids": [], "auth": {}},
            headers={"x-token": token},
        )
        assert entity_resp.status_code == 200
        entity_id = entity_resp.json()["id"]

        subscription_id = self._register_subscription_auth(
            test_app, token, monkeypatch, entity_id=entity_id
        )

        def _fake_list_invoices(self, sub_id, *, limit=5):
            if sub_id != subscription_id:
                return []
            return [
                StripeInvoiceData(
                    id="in_poll_001",
                    subscription_id=sub_id,
                    amount_paid=2000,  # $20.00
                    currency="usd",
                    billing_reason="subscription_cycle",
                )
            ]

        monkeypatch.setattr(
            StripeService, "list_invoices_for_subscription", _fake_list_invoices
        )

        run = test_app.post("/tasks/stripe-poll/run", headers={"x-token": token})
        assert run.status_code == 200
        assert run.json()["result"] >= 1

        listing = test_app.get(
            "/deposits",
            params={"provider": "stripe", "to_entity_id": entity_id, "limit": 20},
            headers={"x-token": token},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert len(items) == 1
        deposit = items[0]
        assert deposit["status"] == "completed"
        from decimal import Decimal

        assert Decimal(deposit["amount"]) == Decimal("20.00")
