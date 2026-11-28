from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.errors.common import NotFoundError
from app.errors.stripe import StripeRequestError
from app.routes.deposits import stripe_charge_authorization
from app.schemas.stripe_authorization import StripeAuthorizationChargeSchema
from app.services.stripe_authorization import StripeAuthorizationService
from fastapi import HTTPException


def test_selected_inactive_card_is_enabled_after_successful_charge():
    service = StripeAuthorizationService.__new__(StripeAuthorizationService)
    card = SimpleNamespace(
        id=7,
        entity_id=2,
        active=False,
        stripe_customer_id="cus_2",
        stripe_payment_method_id="pm_7",
    )
    service.get = Mock(return_value=card)
    service._list_active_authorizations = Mock()
    service._create_pending_charge_deposit = Mock(return_value=SimpleNamespace(id=99))
    service.stripe_service = SimpleNamespace(
        create_off_session_payment_intent=Mock(
            return_value={"id": "pi_1", "status": "succeeded"}
        ),
        normalize_payment_intent=Mock(
            return_value=SimpleNamespace(id="pi_1", status="succeeded")
        ),
    )
    service.db = Mock()
    service._update_deposit_details = Mock()
    service.deposit_service = SimpleNamespace(
        complete=Mock(), get=Mock(return_value={"id": 99})
    )

    assert service.charge_on_demand(2, Decimal("10"), "USD", authorization_id=7) == {
        "id": 99
    }
    assert (
        service.stripe_service.create_off_session_payment_intent.call_args.kwargs[
            "payment_method_id"
        ]
        == "pm_7"
    )
    assert card.active
    service._list_active_authorizations.assert_not_called()
    with pytest.raises(NotFoundError):
        service.charge_on_demand(3, Decimal("10"), "USD", authorization_id=7)


def test_failed_charge_does_not_enable_inactive_card():
    service = StripeAuthorizationService.__new__(StripeAuthorizationService)
    card = SimpleNamespace(
        id=7,
        entity_id=2,
        active=False,
        consecutive_error_count=0,
        stripe_customer_id="cus_2",
        stripe_payment_method_id="pm_7",
    )
    service.get = Mock(return_value=card)
    service._create_pending_charge_deposit = Mock(return_value=SimpleNamespace(id=99))
    service.stripe_service = SimpleNamespace(
        create_off_session_payment_intent=Mock(side_effect=RuntimeError("declined")),
    )
    service.db = Mock()
    service.config = SimpleNamespace(stripe_authorization_max_consecutive_errors=3)
    service._update_deposit_details = Mock()
    service.deposit_service = SimpleNamespace(update=Mock())

    with pytest.raises(StripeRequestError):
        service.charge_on_demand(2, Decimal("10"), "USD", authorization_id=7)
    assert not card.active


def test_selected_card_cannot_be_charged_for_another_entity():
    schema = StripeAuthorizationChargeSchema(
        entity_id=2, authorization_id=7, amount=Decimal("10"), currency="USD"
    )
    service = SimpleNamespace(charge_on_demand=Mock())
    with pytest.raises(HTTPException) as exc:
        stripe_charge_authorization(schema, service, SimpleNamespace(id=1))
    assert exc.value.status_code == 403
    service.charge_on_demand.assert_not_called()


def test_card_setup_can_disable_automatic_charges():
    from app.services.stripe import StripeCheckoutSessionData

    service = StripeAuthorizationService.__new__(StripeAuthorizationService)
    service.db = Mock()
    service.db.query.return_value.filter.return_value.first.return_value = None
    service._next_priority = Mock(return_value=1)
    service.stripe_service = SimpleNamespace(
        retrieve_setup_intent=Mock(return_value={}),
        normalize_setup_intent=Mock(
            return_value=SimpleNamespace(
                payment_method_id="pm_7", customer_id="cus_2", metadata={}
            )
        ),
        retrieve_payment_method=Mock(return_value={}),
        normalize_payment_method=Mock(
            return_value=SimpleNamespace(
                customer_id="cus_2",
                card_brand="visa",
                card_last4="4242",
                card_exp_month=12,
                card_exp_year=2035,
            )
        ),
    )
    session = StripeCheckoutSessionData(
        id="cs_1",
        mode="setup",
        setup_intent_id="si_1",
        subscription_id=None,
        customer_id="cus_2",
        metadata={"entity_id": "2", "automatic_charges": "false"},
    )
    card = service.handle_setup_session_completed(session)
    assert card.active is False
    assert card.entity_id == 2


def test_card_setup_session_marks_automatic_charges_disabled(monkeypatch):
    from contextlib import nullcontext

    import stripe
    from app.services.stripe import StripeService

    service = StripeService.__new__(StripeService)
    service._stripe_call = Mock(return_value=nullcontext())
    create = Mock(return_value={"id": "cs_1"})
    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    service.create_setup_session(
        entity_id=2,
        mode="entity_dynamic",
        static_amount=Decimal("0"),
        static_currency=None,
        success_url="https://example.test/success",
        cancel_url="https://example.test/cancel",
        automatic_charges=False,
    )
    assert create.call_args.kwargs["metadata"]["automatic_charges"] == "false"
    assert (
        create.call_args.kwargs["setup_intent_data"]["metadata"]["automatic_charges"]
        == "false"
    )
