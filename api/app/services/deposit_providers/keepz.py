"""Keepz deposit provider service."""

import random
import string
from decimal import Decimal
from typing import Any

from app.config import Config, get_config
from app.dependencies.services import get_deposit_service, get_keepz_service
from app.models.deposit import Deposit, DepositStatus
from app.models.entity import Entity
from app.schemas.deposit import (
    DepositCreateSchema,
    DepositFiltersSchema,
    DepositUpdateSchema,
)
from app.schemas.deposit_providers.keepz import KeepzDepositCreateSchema
from app.seeding import keepz_deposit_provider, keepz_treasury
from app.services.base import BaseService
from app.services.deposit import DepositService
from app.services.keepz import KeepzService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


class KeepzDepositProviderService(BaseService[Entity]):
    def __init__(
        self,
        db: Session = Depends(get_uow),
        deposit_service: DepositService = Depends(get_deposit_service),
        keepz_service: KeepzService = Depends(get_keepz_service),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.deposit_service = deposit_service
        self.keepz_service = keepz_service
        self.config = config

    def create_deposit(
        self, schema: KeepzDepositCreateSchema, actor_entity: Entity
    ) -> Deposit:
        note = (schema.note or "").strip()
        if not note:
            note = self._generate_unique_note()
        details = {
            "keepz": {
                "note": note,
                "currency": schema.currency,
                "amount_requested": str(schema.amount),
            }
        }
        payload = self.keepz_service.create_payment_link(
            amount=float(schema.amount),
            currency=schema.currency,
            commission_type=schema.commission_type,
            note=note,
        )
        short_url = None
        if isinstance(payload, str):
            short_url = payload
        elif isinstance(payload, dict):
            short_url = (
                payload.get("shortUrl")
                or payload.get("short_url")
                or payload.get("url")
            )
        if short_url:
            details["keepz"]["payment_short_url"] = short_url
            try:
                details["keepz"]["payment_url"] = (
                    self.keepz_service.resolve_payment_url(short_url)
                )
            except Exception:
                details["keepz"]["payment_url"] = short_url
        if isinstance(payload, dict):
            details["keepz"]["create_response"] = payload

        return self.deposit_service.create(
            DepositCreateSchema(
                from_entity_id=keepz_deposit_provider.id,
                to_entity_id=schema.to_entity_id,
                amount=schema.amount,
                currency=schema.currency,
                provider="keepz",
                details=details,
                to_treasury_id=keepz_treasury.id,
            ),
            overrides={"actor_entity_id": actor_entity.id},
        )

    def poll_pending_deposits(self) -> int:
        pending = self._list_pending_deposits()
        if not pending:
            return 0

        transactions_payload = self.keepz_service.list_transactions()
        transactions_by_note = self._index_transactions_by_note(transactions_payload)

        processed = 0
        for deposit in pending:
            note = (deposit.details or {}).get("keepz", {}).get("note")
            if not note:
                continue
            tx = transactions_by_note.get(note)
            if tx is None:
                continue
            if self._apply_transaction_to_deposit(deposit, tx):
                processed += 1
        return processed

    def _list_pending_deposits(self) -> list[Deposit]:
        filters = DepositFiltersSchema(
            provider="keepz", status=DepositStatus.PENDING, tags_ids=[]
        )
        page = self.deposit_service.get_all(filters, skip=0, limit=200)
        return list(page.items)

    def _generate_unique_note(self, attempts: int = 10) -> str:
        pending = self._list_pending_deposits()
        existing_notes = {
            (d.details or {}).get("keepz", {}).get("note") for d in pending
        }
        existing_notes.discard(None)
        for _ in range(attempts):
            length = random.randint(2, 5)
            pool = (
                string.digits
                if random.choice([True, False])
                else string.ascii_lowercase
            )
            note = "".join(random.choice(pool) for _ in range(length))
            if note not in existing_notes:
                return note
        pool = string.digits if random.choice([True, False]) else string.ascii_lowercase
        return "".join(random.choice(pool) for _ in range(5))

    def _index_transactions_by_note(self, payload: Any) -> dict[str, Any]:
        page = payload.transactionsPage
        items = page.content or []
        return {tx.note: tx for tx in items if tx.note}

    def _apply_transaction_to_deposit(self, deposit: Deposit, tx: Any) -> bool:
        tx_dict = tx.model_dump()
        status = str(tx.status or "").upper()
        amount_value = tx.amount or tx.initialAmount
        currency = tx.currencyCode
        details = deposit.details or {}
        keepz_details = details.get("keepz") or {}
        keepz_details.update(
            {
                "transaction_id": tx.id,
                "status": tx.status,
                "currency": currency or keepz_details.get("currency"),
                "amount_received": (
                    str(amount_value) if amount_value is not None else None
                ),
                "transaction": tx_dict,
            }
        )
        details["keepz"] = keepz_details

        self.deposit_service.update(deposit.id, DepositUpdateSchema(details=details))

        success_statuses = {"SUCCESS", "COMPLETED", "APPROVED", "DONE", "PAID"}
        failed_statuses = {"FAILED", "CANCELLED", "REJECTED", "DECLINED"}

        if status in success_statuses:
            if amount_value is not None:
                amount = Decimal(str(amount_value)).quantize(Decimal("0.01"))
                self.deposit_service.update(
                    deposit.id, DepositUpdateSchema(amount=amount)
                )
            self.deposit_service.complete(deposit.id)
            return True
        if status in failed_statuses:
            self.deposit_service.update(
                deposit.id, DepositUpdateSchema(status=DepositStatus.FAILED)
            )
            return True
        return False
