"""Invoice service"""

import datetime
from decimal import Decimal

from app.dependencies.services import (
    get_balance_service,
    get_tag_service,
    get_transaction_service,
)
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
from app.models.entity import Entity
from app.models.invoice import Invoice, InvoiceStatus
from app.models.transaction import TransactionStatus
from app.schemas.invoice import (
    FeeInvoiceIssueReportSchema,
    InvoiceCreateSchema,
    InvoiceFiltersSchema,
    InvoiceUpdateSchema,
)
from app.schemas.transaction import TransactionCreateSchema
from app.seeding import f0_entity, fee_tag, member_tag, resident_tag
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session


class InvoiceService(TaggableServiceMixin[Invoice], BaseService[Invoice]):
    model = Invoice

    def __init__(
        self,
        db: Session = Depends(get_uow),
        tag_service: TagService = Depends(get_tag_service),
        balance_service: BalanceService = Depends(get_balance_service),
        transaction_service: TransactionService = Depends(get_transaction_service),
    ):
        self.db = db
        self._tag_service = tag_service
        self._balance_service = balance_service
        self._transaction_service = transaction_service

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
        if filters.billing_period is not None:
            query = query.filter(self.model.billing_period == filters.billing_period)
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def create(  # type: ignore[override]
        self, schema: InvoiceCreateSchema, overrides: dict = {}
    ) -> Invoice:
        data = schema.dump()
        tag_ids = data.pop("tag_ids", None)
        data["amounts"] = self._serialize_amounts(data.get("amounts", []))
        if "billing_period" in data:
            data["billing_period"] = self._normalize_billing_period(
                data.get("billing_period")
            )
        data = {**data, **overrides}
        new_obj = self.model(**data)
        self.db.add(new_obj)
        self.db.flush()
        if tag_ids is not None:
            self.set_tags(new_obj, tag_ids)
            self.db.flush()
        self._try_auto_pay(new_obj)
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
        if "billing_period" in data:
            data["billing_period"] = self._normalize_billing_period(
                data.get("billing_period")
            )
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

    @staticmethod
    def _balance_to_decimal(value: object) -> Decimal:
        from app.schemas.base import CurrencyDecimal

        if value is None:
            return Decimal("0")
        if isinstance(value, CurrencyDecimal):
            value = value.to_decimal()
        return value if isinstance(value, Decimal) else Decimal(str(value))

    def _try_auto_pay(self, invoice: Invoice) -> None:
        if invoice.transaction is not None:
            return
        if invoice.status != InvoiceStatus.PENDING:
            return

        balances = self._balance_service.get_balances(invoice.from_entity_id)
        completed_balances = balances.completed or {}

        selected_currency = None
        selected_amount = None
        selected_balance = None

        for entry in invoice.amounts or []:
            currency = str(entry.get("currency", "")).lower()
            if not currency:
                continue
            required_amount = Decimal(str(entry.get("amount", "0")))
            current_balance = self._balance_to_decimal(completed_balances.get(currency))
            if current_balance < required_amount:
                continue
            if selected_balance is None or current_balance < selected_balance:
                selected_balance = current_balance
                selected_currency = currency
                selected_amount = required_amount

        if selected_currency is None or selected_amount is None:
            return

        tx_schema = TransactionCreateSchema(
            to_entity_id=invoice.to_entity_id,
            from_entity_id=invoice.from_entity_id,
            amount=selected_amount,
            currency=selected_currency,
            status=TransactionStatus.COMPLETED,
            invoice_id=invoice.id,
            comment=invoice.comment,
            tag_ids=[],
        )

        self._transaction_service.create(
            tx_schema, overrides={"actor_entity_id": invoice.actor_entity_id}
        )

    @staticmethod
    def _normalize_billing_period(
        value: datetime.date | None,
    ) -> datetime.date | None:
        if value is None:
            return None
        return datetime.date(value.year, value.month, 1)

    def issue_fee_invoices(
        self,
        *,
        billing_period: datetime.date | None = None,
        actor_entity_id: int | None = None,
    ) -> FeeInvoiceIssueReportSchema:
        period = self._normalize_billing_period(billing_period or datetime.date.today())
        if period is None:
            period = datetime.date.today().replace(day=1)
        hackerspace = self.db.query(Entity).filter(Entity.id == f0_entity.id).first()
        if hackerspace is None:
            hackerspace = f0_entity

        resolved_actor_id = actor_entity_id or hackerspace.id

        targets = (
            self.db.query(Entity)
            .filter(
                or_(
                    Entity.tags.contains(resident_tag),
                    Entity.tags.contains(member_tag),
                )
            )
            .all()
        )

        existing = {
            (inv.from_entity_id, inv.billing_period)
            for inv in self.db.query(Invoice)
            .filter(
                Invoice.billing_period == period,
                Invoice.tags.contains(fee_tag),
            )
            .all()
        }

        invoice_ids: list[int] = []
        created_count = 0
        skipped_count = 0
        for resident in targets:
            if not resident.active:
                skipped_count += 1
                continue
            if (resident.id, period) in existing:
                skipped_count += 1
                continue

            tag_ids = {tag.id for tag in (resident.tags or [])}
            if resident_tag.id in tag_ids:
                usd_amount = Decimal("42")
                gel_amount = Decimal("115")
            elif member_tag.id in tag_ids:
                usd_amount = Decimal("25")
                gel_amount = Decimal("70")
            else:
                skipped_count += 1
                continue

            invoice = self.create(
                InvoiceCreateSchema(
                    from_entity_id=resident.id,
                    to_entity_id=hackerspace.id,
                    amounts=[
                        {"currency": "usd", "amount": usd_amount},
                        {"currency": "gel", "amount": gel_amount},
                    ],
                    billing_period=period,
                    tag_ids=[fee_tag.id],
                    comment=f"Monthly fee {period.year}-{period.month:02d}",
                ),
                overrides={"actor_entity_id": resolved_actor_id},
            )
            invoice_ids.append(invoice.id)
            created_count += 1

        return FeeInvoiceIssueReportSchema(
            billing_period=period,
            created_count=created_count,
            skipped_count=skipped_count,
            invoice_ids=invoice_ids,
        )

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
