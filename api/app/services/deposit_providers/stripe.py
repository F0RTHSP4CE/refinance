"""Stripe deposit provider service."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.config import Config, get_config
from app.dependencies.services import get_deposit_service, get_stripe_service
from app.errors.deposit import DepositAlreadyCompleted
from app.models.deposit import Deposit, DepositStatus
from app.schemas.deposit import (
    DepositCreateSchema,
    DepositFiltersSchema,
    DepositUpdateSchema,
)
from app.schemas.deposit_providers.stripe import StripeDepositCreateSchema
from app.seeding import stripe_deposit_provider, stripe_treasury
from app.services.deposit import DepositService
from app.services.stripe import StripeService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


class StripeDepositProviderService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        deposit_service: DepositService = Depends(get_deposit_service),
        stripe_service: StripeService = Depends(get_stripe_service),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.deposit_service = deposit_service
        self.stripe_service = stripe_service
        self.config = config

    def create_deposit(
        self, schema: StripeDepositCreateSchema, actor_entity: Entity
    ) -> Deposit:
        amount = Decimal(schema.amount).quantize(Decimal("0.01"))
        deposit = self.deposit_service.create(
            DepositCreateSchema(
                from_entity_id=stripe_deposit_provider.id,
                to_entity_id=schema.to_entity_id,
                amount=amount,
                currency=schema.currency,
                provider="stripe",
                details={"stripe": {"mode": "payment"}},
                to_treasury_id=stripe_treasury.id,
            ),
            overrides={"actor_entity_id": actor_entity.id},
        )

        success_url = self._resolve_success_url(schema.success_url, deposit.id)
        cancel_url = self._resolve_cancel_url(schema.cancel_url, deposit.id)

        session = self.stripe_service.create_checkout_session(
            amount=amount,
            currency=schema.currency,
            deposit_id=deposit.id,
            deposit_uuid=str(deposit.uuid),
            actor_entity_id=actor_entity.id,
            to_entity_id=schema.to_entity_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        details = dict(deposit.details or {})
        details["stripe"] = {
            "mode": "payment",
            "checkout_session_id": session.id,
            "payment_url": session.url,
            "status": session.status,
            "payment_status": session.payment_status,
        }
        return self.deposit_service.update(
            deposit.id,
            DepositUpdateSchema(details=details),
        )

    def handle_webhook_event(self, event: dict) -> None:
        event_type = str(event.get("type") or "")
        data_object = (event.get("data") or {}).get("object") or {}

        if event_type != "checkout.session.completed":
            return

        if str(data_object.get("mode") or "") != "payment":
            return

        metadata = data_object.get("metadata") or {}
        deposit_id_raw = metadata.get("deposit_id")
        if not deposit_id_raw:
            return

        deposit = self.deposit_service.get(int(deposit_id_raw))
        self._apply_checkout_session_to_deposit(
            deposit,
            session_obj=data_object,
            last_event_id=event.get("id"),
        )

    def poll_pending_deposits(self) -> int:
        pending = self._list_pending_deposits()
        if not pending:
            return 0

        processed = 0
        for deposit in pending:
            stripe_details = (deposit.details or {}).get("stripe") or {}
            session_id = stripe_details.get("checkout_session_id")
            if not session_id:
                continue

            session = self.stripe_service.retrieve_checkout_session(session_id)
            session_obj = self._session_to_dict(session)
            if self._apply_checkout_session_to_deposit(
                deposit,
                session_obj=session_obj,
                last_event_id=f"poll:{session_id}",
            ):
                processed += 1

        return processed

    def _list_pending_deposits(self) -> list[Deposit]:
        filters = DepositFiltersSchema(
            provider="stripe",
            status=DepositStatus.PENDING,
            tags_ids=[],
        )
        page = self.deposit_service.get_all(filters, skip=0, limit=200)
        return list(page.items)

    @staticmethod
    def _session_to_dict(session: Any) -> dict[str, Any]:
        if isinstance(session, dict):
            return session
        if hasattr(session, "to_dict_recursive"):
            return session.to_dict_recursive()
        return {
            "id": getattr(session, "id", None),
            "status": getattr(session, "status", None),
            "payment_status": getattr(session, "payment_status", None),
            "amount_total": getattr(session, "amount_total", None),
            "currency": getattr(session, "currency", None),
            "metadata": getattr(session, "metadata", None) or {},
        }

    def _apply_checkout_session_to_deposit(
        self,
        deposit: Deposit,
        *,
        session_obj: dict[str, Any],
        last_event_id: str | None,
    ) -> bool:
        details = dict(deposit.details or {})
        stripe_details = dict(details.get("stripe") or {})
        previous_status = stripe_details.get("status")
        previous_payment_status = stripe_details.get("payment_status")

        stripe_details.update(
            {
                "last_event_id": last_event_id,
                "checkout_session_id": session_obj.get("id"),
                "payment_status": session_obj.get("payment_status"),
                "status": session_obj.get("status"),
            }
        )
        details["stripe"] = stripe_details
        self.deposit_service.update(
            deposit.id,
            DepositUpdateSchema(details=details),
        )

        if deposit.status != DepositStatus.PENDING:
            return False

        payment_status = str(session_obj.get("payment_status") or "").lower()
        status = str(session_obj.get("status") or "").lower()

        if payment_status == "paid":
            amount_total = session_obj.get("amount_total")
            if amount_total is not None:
                amount = (Decimal(str(amount_total)) / Decimal("100")).quantize(
                    Decimal("0.01")
                )
                self.deposit_service.update(
                    deposit.id,
                    DepositUpdateSchema(amount=amount),
                )

            try:
                self.deposit_service.complete(deposit.id)
            except DepositAlreadyCompleted:
                pass
            return True

        if status == "expired":
            self.deposit_service.update(
                deposit.id,
                DepositUpdateSchema(status=DepositStatus.CANCELLED),
            )
            return True

        return previous_status != stripe_details.get(
            "status"
        ) or previous_payment_status != stripe_details.get("payment_status")

    def _resolve_success_url(self, override: str | None, deposit_id: int) -> str:
        if override:
            return override
        if self.config.stripe_success_url:
            return self.config.stripe_success_url
        base = (self.config.ui_url or "").rstrip("/")
        return f"{base}/deposits/{deposit_id}" if base else "https://example.com"

    def _resolve_cancel_url(self, override: str | None, deposit_id: int) -> str:
        if override:
            return override
        if self.config.stripe_cancel_url:
            return self.config.stripe_cancel_url
        base = (self.config.ui_url or "").rstrip("/")
        return f"{base}/deposits/{deposit_id}" if base else "https://example.com"
