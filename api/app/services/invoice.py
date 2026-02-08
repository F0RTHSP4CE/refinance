"""Invoice service"""

import datetime
from decimal import Decimal

from app.errors.invoice import (
    InvoiceAlreadyPaid,
    InvoiceAmountInsufficient,
    InvoiceAmountInvalid,
    InvoiceAmountsRequired,
    InvoiceCancelledNotPayable,
    InvoiceCurrencyNotAllowed,
    InvoiceDuplicateCurrency,
    InvoiceEntitiesMismatch,
    InvoiceNotEditable,
    InvoiceTransactionAlreadyAttached,
)
from app.models.invoice import Invoice, InvoiceStatus
from app.models.transaction import TransactionStatus
from app.schemas.invoice import (
    InvoiceCreateSchema,
    InvoiceFiltersSchema,
    InvoiceUpdateSchema,
)
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session


class InvoiceService(TaggableServiceMixin[Invoice], BaseService[Invoice]):
    model = Invoice

    def __init__(
        self,
        db: Session = Depends(get_uow),
        tag_service: TagService = Depends(),
    ):
        self.db = db
        self._tag_service = tag_service

    def _apply_filters(  # type: ignore[override]
        self, query: Query[Invoice], filters: InvoiceFiltersSchema
    ) -> Query[Invoice]:
        if filters.entity_id is not None:
            query = query.filter(
                or_(
                    self.model.from_entity_id == filters.entity_id,
                    self.model.to_entity_id == filters.entity_id,
                    self.model.actor_entity_id == filters.entity_id,
                )
            )
        if filters.actor_entity_id is not None:
            query = query.filter(self.model.actor_entity_id == filters.actor_entity_id)
        if filters.from_entity_id is not None:
            query = query.filter(self.model.from_entity_id == filters.from_entity_id)
        if filters.to_entity_id is not None:
            query = query.filter(self.model.to_entity_id == filters.to_entity_id)
        if filters.status is not None:
            query = query.filter(self.model.status == filters.status)
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def create(  # type: ignore[override]
        self, schema: InvoiceCreateSchema, overrides: dict = {}
    ) -> Invoice:
        data = schema.dump()
        tag_ids = data.pop("tag_ids", None)
        data["amounts"] = self._serialize_amounts(data.get("amounts", []))
        data = {**data, **overrides}
        new_obj = self.model(**data)
        self.db.add(new_obj)
        self.db.flush()
        if tag_ids is not None:
            self.set_tags(new_obj, tag_ids)
            self.db.flush()
        self.db.refresh(new_obj)
        return new_obj

    def update(  # type: ignore[override]
        self, obj_id: int, schema: InvoiceUpdateSchema, overrides: dict = {}
    ) -> Invoice:
        db_obj = self.get(obj_id)
        if db_obj.status != InvoiceStatus.PENDING or db_obj.transaction is not None:
            raise InvoiceNotEditable
        data = schema.dump()
        tag_ids = data.pop("tag_ids", None)
        if "amounts" in data and data["amounts"] is not None:
            data["amounts"] = self._serialize_amounts(data["amounts"])
        data = {**data, **overrides}
        for key, value in data.items():
            setattr(db_obj, key, value)
        if tag_ids is not None:
            self.set_tags(db_obj, tag_ids)
        setattr(db_obj, "modified_at", datetime.datetime.now())
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, obj_id: int) -> int:  # type: ignore[override]
        db_obj = self.get(obj_id)
        if db_obj.status != InvoiceStatus.PENDING or db_obj.transaction is not None:
            raise InvoiceNotEditable
        return super().delete(obj_id)

    def _serialize_amounts(self, amounts: list[dict]) -> list[dict[str, str]]:
        if not amounts:
            raise InvoiceAmountsRequired
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in amounts:
            currency = str(item.get("currency", "")).lower()
            if not currency:
                raise InvoiceCurrencyNotAllowed
            if currency in seen:
                raise InvoiceDuplicateCurrency
            seen.add(currency)
            raw_amount = item.get("amount")
            if raw_amount is None:
                raise InvoiceAmountInvalid
            amount = Decimal(raw_amount)
            amount = amount.quantize(Decimal("0.01"))
            if amount <= 0:
                raise InvoiceAmountInvalid
            normalized.append({"currency": currency, "amount": format(amount, "f")})
        return normalized

    def _required_amount_for_currency(
        self, invoice: Invoice, currency: str
    ) -> Decimal | None:
        for entry in invoice.amounts or []:
            if str(entry.get("currency", "")).lower() == currency.lower():
                return Decimal(str(entry.get("amount")))
        return None

    def validate_transaction_for_invoice(
        self,
        *,
        invoice_id: int,
        tx_id: int | None,
        from_entity_id: int,
        to_entity_id: int,
        amount: Decimal,
        currency: str,
        status: TransactionStatus,
    ) -> None:
        invoice = self.get(invoice_id)
        if invoice.status == InvoiceStatus.CANCELLED:
            raise InvoiceCancelledNotPayable
        if invoice.status == InvoiceStatus.PAID and (
            invoice.transaction is None or invoice.transaction.id != tx_id
        ):
            raise InvoiceAlreadyPaid
        if invoice.transaction is not None and invoice.transaction.id != tx_id:
            raise InvoiceTransactionAlreadyAttached
        if (
            invoice.from_entity_id != from_entity_id
            or invoice.to_entity_id != to_entity_id
        ):
            raise InvoiceEntitiesMismatch
        required_amount = self._required_amount_for_currency(invoice, currency)
        if required_amount is None:
            raise InvoiceCurrencyNotAllowed
        if amount < required_amount:
            raise InvoiceAmountInsufficient
        if (
            status == TransactionStatus.COMPLETED
            and invoice.status != InvoiceStatus.PAID
        ):
            invoice.status = InvoiceStatus.PAID
            invoice.modified_at = datetime.datetime.now()
            self.db.flush()
