"""Stripe API wrapper service."""

from __future__ import annotations

from decimal import Decimal

import stripe
from app.config import Config, get_config
from app.errors.base import ApplicationError
from app.errors.stripe import StripeRequestError, StripeWebhookError
from fastapi import Depends


class StripeConfigMissing(ApplicationError):
    error_code = 7601
    error = "Stripe is not configured"


class StripeService:
    def __init__(self, config: Config = Depends(get_config)):
        self.config = config
        self._api_key = (self.config.stripe_secret_key or "").strip()

    def _ensure_configured(self) -> None:
        if not self._api_key:
            raise StripeConfigMissing

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
        self._ensure_configured()
        stripe.api_key = self._api_key

        unit_amount = int((amount * Decimal("100")).quantize(Decimal("1")))
        if unit_amount <= 0:
            raise ValueError("Amount must be positive")

        try:
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
        except stripe.error.StripeError as exc:
            message = getattr(exc, "user_message", None) or str(exc)
            raise StripeRequestError(message)

    def construct_webhook_event(self, payload: bytes, signature: str):
        self._ensure_configured()
        stripe.api_key = self._api_key
        secret = (self.config.stripe_webhook_secret or "").strip()
        if not secret:
            raise StripeConfigMissing("Stripe webhook secret is not configured")
        try:
            return stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=secret,
            )
        except stripe.error.StripeError as exc:
            message = getattr(exc, "user_message", None) or str(exc)
            raise StripeWebhookError(message)

    def retrieve_checkout_session(self, session_id: str):
        self._ensure_configured()
        stripe.api_key = self._api_key
        try:
            return stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as exc:
            message = getattr(exc, "user_message", None) or str(exc)
            raise StripeRequestError(message)
