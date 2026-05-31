"""Stripe API wrapper service."""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import stripe
from app.config import Config, get_config
from app.errors.stripe import (
    StripeConfigMissing,
    StripeRequestError,
    StripeWebhookError,
)
from fastapi import Depends


@dataclass(frozen=True)
class StripeCheckoutSessionData:
    id: str
    mode: str
    setup_intent_id: str | None
    subscription_id: str | None
    customer_id: str | None
    metadata: dict[str, str]


@dataclass(frozen=True)
class StripeSetupIntentData:
    id: str
    payment_method_id: str | None
    customer_id: str | None
    metadata: dict[str, str]


@dataclass(frozen=True)
class StripePaymentMethodData:
    id: str
    customer_id: str | None
    card_brand: str | None
    card_last4: str | None
    card_exp_month: int | None
    card_exp_year: int | None


@dataclass(frozen=True)
class StripePaymentIntentData:
    id: str | None
    status: str | None


class StripeService:
    def __init__(self, config: Config = Depends(get_config)):
        self.config = config
        self._api_key = (config.stripe_secret_key or "").strip()

    def _ensure_configured(self) -> None:
        if not self._api_key:
            raise StripeConfigMissing

    @contextlib.contextmanager
    def _stripe_call(self) -> Generator[None, None, None]:
        """Set API key and translate StripeError → StripeRequestError."""
        self._ensure_configured()
        stripe.api_key = self._api_key
        try:
            yield
        except stripe.error.StripeError as exc:
            raise StripeRequestError(
                getattr(exc, "user_message", None) or str(exc)
            ) from exc

    # ── Checkout Sessions ──────────────────────────────────────────────────

    def create_checkout_session(
        self,
        *,
        amount: Decimal,
        currency: str,
        deposit_id: int,
        deposit_uuid: str,
        actor_entity_id: int,
        to_entity_id: int,
        success_url: str,
        cancel_url: str,
    ) -> stripe.checkout.Session:
        unit_amount = int((amount * Decimal("100")).quantize(Decimal("1")))
        if unit_amount <= 0:
            raise ValueError("Amount must be positive")
        with self._stripe_call():
            return stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": currency.lower(),
                            "unit_amount": unit_amount,
                            "product_data": {
                                "name": f"Deposit #{deposit_id}",
                                "description": "refinance balance top-up",
                            },
                        },
                    }
                ],
                metadata={
                    "deposit_id": str(deposit_id),
                    "deposit_uuid": str(deposit_uuid),
                    "actor_entity_id": str(actor_entity_id),
                    "to_entity_id": str(to_entity_id),
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )

    def create_setup_session(
        self,
        *,
        entity_id: int,
        mode: str,
        static_amount: Decimal,
        static_currency: str | None,
        success_url: str,
        cancel_url: str,
        donation_comment: str | None = None,
    ) -> stripe.checkout.Session:
        metadata = {
            "entity_id": str(entity_id),
            "mode": mode,
            "static_amount": str(static_amount.quantize(Decimal("0.01"))),
            "static_currency": (static_currency or ""),
        }
        if donation_comment:
            metadata["donation_comment"] = donation_comment
        with self._stripe_call():
            return stripe.checkout.Session.create(
                mode="setup",
                payment_method_types=["card"],
                customer_creation="always",
                metadata=metadata,
                setup_intent_data={"metadata": metadata},
                success_url=success_url,
                cancel_url=cancel_url,
            )

    def retrieve_checkout_session(
        self, session_id: str, *, expand_setup_intent: bool = False
    ):
        with self._stripe_call():
            params = {"expand": ["setup_intent"]} if expand_setup_intent else {}
            return stripe.checkout.Session.retrieve(session_id, **params)

    def create_subscription_checkout_session(
        self,
        *,
        entity_id: int,
        amount: Decimal,
        currency: str,
        donation_comment: str | None = None,
        success_url: str,
        cancel_url: str,
    ) -> stripe.checkout.Session:
        unit_amount = int((amount * Decimal("100")).quantize(Decimal("1")))
        if unit_amount <= 0:
            raise ValueError("Amount must be positive")
        metadata: dict[str, str] = {
            "entity_id": str(entity_id),
            "mode": "guest_static",
            "static_amount": str(amount.quantize(Decimal("0.01"))),
            "static_currency": currency.upper(),
        }
        if donation_comment:
            metadata["donation_comment"] = donation_comment
        with self._stripe_call():
            return stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": currency.lower(),
                            "unit_amount": unit_amount,
                            "recurring": {"interval": "month"},
                            "product_data": {
                                "name": "Monthly donation — F0RTHSP4CE",
                            },
                        },
                    }
                ],
                metadata=metadata,
                subscription_data={"metadata": metadata},
                success_url=success_url,
                cancel_url=cancel_url,
            )

    def create_billing_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        with self._stripe_call():
            return stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )

    def retrieve_subscription(self, subscription_id: str):
        with self._stripe_call():
            return stripe.Subscription.retrieve(
                subscription_id,
                expand=["default_payment_method"],
            )

    def list_invoices_for_subscription(
        self, subscription_id: str, *, limit: int = 5
    ) -> list[dict]:
        with self._stripe_call():
            result = stripe.Invoice.list(
                subscription=subscription_id,
                status="paid",
                limit=limit,
            )
            invoices = []
            for inv in result.data:
                if hasattr(inv, "to_dict_recursive"):
                    d = inv.to_dict_recursive()
                elif hasattr(inv, "to_dict"):
                    d = inv.to_dict()
                else:
                    d = dict(inv)
                if isinstance(d, dict):
                    invoices.append(d)
            return invoices

    # ── Webhooks ───────────────────────────────────────────────────────────

    def construct_webhook_event(self, payload: bytes, signature: str):
        self._ensure_configured()
        stripe.api_key = self._api_key
        secret = (self.config.stripe_webhook_secret or "").strip()
        if not secret:
            raise StripeConfigMissing("Stripe webhook secret is not configured")
        try:
            return stripe.Webhook.construct_event(
                payload=payload, sig_header=signature, secret=secret
            )
        except stripe.error.StripeError as exc:
            raise StripeWebhookError(
                getattr(exc, "user_message", None) or str(exc)
            ) from exc

    # ── Setup Intents & Payment Methods ───────────────────────────────────

    def retrieve_setup_intent(self, setup_intent_id: str):
        with self._stripe_call():
            return stripe.SetupIntent.retrieve(setup_intent_id)

    def retrieve_payment_method(self, payment_method_id: str):
        with self._stripe_call():
            return stripe.PaymentMethod.retrieve(payment_method_id)

    def detach_payment_method(self, payment_method_id: str):
        with self._stripe_call():
            return stripe.PaymentMethod.detach(payment_method_id)

    # ── Payment Intents ────────────────────────────────────────────────────

    def create_off_session_payment_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method_id: str,
        idempotency_key: str,
        metadata: dict[str, str] | None = None,
    ):
        unit_amount = int((amount * Decimal("100")).quantize(Decimal("1")))
        if unit_amount <= 0:
            raise ValueError("Amount must be positive")
        with self._stripe_call():
            return stripe.PaymentIntent.create(
                amount=unit_amount,
                currency=currency.lower(),
                customer=customer_id,
                payment_method=payment_method_id,
                off_session=True,
                confirm=True,
                metadata=metadata or {},
                idempotency_key=idempotency_key,
            )

    # ── Normalization ──────────────────────────────────────────────────────

    def normalize_checkout_session(self, value: Any) -> StripeCheckoutSessionData:
        payload = self._as_dict(value, "checkout session")
        return StripeCheckoutSessionData(
            id=self._require_str(payload.get("id"), "checkout session id"),
            mode=str(payload.get("mode") or ""),
            setup_intent_id=self._extract_object_id(payload.get("setup_intent")),
            subscription_id=self._extract_object_id(payload.get("subscription")),
            customer_id=self._extract_object_id(payload.get("customer")),
            metadata=self._normalize_str_dict(payload.get("metadata")),
        )

    def normalize_setup_intent(self, value: Any) -> StripeSetupIntentData:
        payload = self._as_dict(value, "setup intent")
        return StripeSetupIntentData(
            id=self._require_str(payload.get("id"), "setup intent id"),
            payment_method_id=self._extract_object_id(payload.get("payment_method")),
            customer_id=self._extract_object_id(payload.get("customer")),
            metadata=self._normalize_str_dict(payload.get("metadata")),
        )

    def normalize_payment_method(self, value: Any) -> StripePaymentMethodData:
        payload = self._as_dict(value, "payment method")
        card_obj = payload.get("card") or {}
        card = (
            card_obj if isinstance(card_obj, dict) else self._as_dict(card_obj, "card")
        )
        return StripePaymentMethodData(
            id=self._require_str(payload.get("id"), "payment method id"),
            customer_id=self._extract_object_id(payload.get("customer")),
            card_brand=self._to_opt_str(card.get("brand")),
            card_last4=self._to_opt_str(card.get("last4")),
            card_exp_month=self._to_opt_int(card.get("exp_month")),
            card_exp_year=self._to_opt_int(card.get("exp_year")),
        )

    def normalize_payment_intent(self, value: Any) -> StripePaymentIntentData:
        payload = self._as_dict(value, "payment intent")
        return StripePaymentIntentData(
            id=self._to_opt_str(payload.get("id")),
            status=self._to_opt_str(payload.get("status")),
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _as_dict(value: Any, object_name: str) -> dict:
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict_recursive"):
            converted = value.to_dict_recursive()
            if isinstance(converted, dict):
                return converted
        if hasattr(value, "to_dict"):
            converted = value.to_dict()
            if isinstance(converted, dict):
                return converted
        raise StripeRequestError(f"Unexpected Stripe {object_name} payload type")

    @staticmethod
    def _normalize_str_dict(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {
            str(k): str(v) for k, v in value.items() if k is not None and v is not None
        }

    @staticmethod
    def _extract_object_id(value: Any) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            result = value.get("id")
            return str(result) if result else None
        if hasattr(value, "id"):
            result = getattr(value, "id", None)
            return str(result) if result else None
        return None

    @staticmethod
    def _require_str(value: Any, field_name: str) -> str:
        result = StripeService._to_opt_str(value)
        if result is None:
            raise StripeRequestError(f"Missing Stripe {field_name}")
        return result

    @staticmethod
    def _to_opt_str(value: Any) -> str | None:
        if value is None:
            return None
        result = str(value).strip()
        return result if result else None

    @staticmethod
    def _to_opt_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
