"""Invoice service"""

import datetime
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

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
from app.models.fee import FeeAllocation, FeeTargetType
from app.models.invoice import Invoice, InvoiceStatus
from app.models.split import Split, SplitParticipant
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.invoice import (
    InvoiceBulkCreateReportSchema,
    InvoiceBulkCreateSchema,
    InvoiceCreateSchema,
    InvoiceFiltersSchema,
    InvoiceUpdateSchema,
)
from app.schemas.transaction import TransactionCreateSchema
from app.seeding import automatic_tag
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

if TYPE_CHECKING:
    from app.services.fee_allocation import FeeAllocationService


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
        self._fee_allocation_service: FeeAllocationService | None = None

    def set_fee_allocation_service(
        self, fee_allocation_service: "FeeAllocationService"
    ) -> None:
        self._fee_allocation_service = fee_allocation_service

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
        skip_auto_pay = bool(overrides.pop("_skip_auto_pay", False))
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
        if not skip_auto_pay:
            self._try_auto_pay(new_obj)
        self.db.refresh(new_obj)
        return new_obj

    def update(  # type: ignore[override]
        self, obj_id: int, schema: InvoiceUpdateSchema, overrides: dict = {}
    ) -> Invoice:
        db_obj = self.get(obj_id)
        if db_obj.status != InvoiceStatus.PENDING or db_obj.transactions:
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
        if db_obj.status != InvoiceStatus.PENDING or db_obj.transactions:
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

    def _select_auto_pay_amount(
        self, invoice: Invoice, balances: dict[str, Decimal]
    ) -> tuple[str, Decimal] | None:
        if self._has_unselected_directed_fee_allocation(invoice.id):
            return None
        selected_currency = None
        selected_amount = None
        selected_balance = None

        for entry in invoice.amounts or []:
            currency = str(entry.get("currency", "")).lower()
            if not currency:
                continue
            required_amount = Decimal(str(entry.get("amount", "0")))
            required_amount += self._requested_extra_fee_amount(invoice.id, currency)
            current_balance = balances.get(currency)
            if current_balance is None or current_balance < required_amount:
                continue
            if selected_balance is None or current_balance < selected_balance:
                selected_balance = current_balance
                selected_currency = currency
                selected_amount = required_amount

        if selected_currency is None or selected_amount is None:
            return None

        return selected_currency, selected_amount

    def _fee_allocations_for_invoice(self, invoice_id: int) -> list[FeeAllocation]:
        return (
            self.db.query(FeeAllocation)
            .filter(FeeAllocation.invoice_id == invoice_id)
            .order_by(FeeAllocation.id.asc())
            .all()
        )

    def _has_fee_allocations(self, invoice_id: int) -> bool:
        return bool(self._fee_allocations_for_invoice(invoice_id))

    def _has_unselected_directed_fee_allocation(self, invoice_id: int) -> bool:
        allocation = (
            self.db.query(FeeAllocation)
            .filter(
                FeeAllocation.invoice_id == invoice_id,
                FeeAllocation.component_key == "directed",
            )
            .first()
        )
        return allocation is not None and allocation.selected_at is None

    def _requested_extra_fee_amount(self, invoice_id: int, currency: str) -> Decimal:
        allocation = (
            self.db.query(FeeAllocation)
            .filter(
                FeeAllocation.invoice_id == invoice_id,
                FeeAllocation.component_key == "directed",
            )
            .first()
        )
        if allocation is None or not allocation.extra_amounts:
            return Decimal("0.00")
        amount = allocation.extra_amounts.get(currency.lower())
        if amount is None:
            return Decimal("0.00")
        return Decimal(str(amount)).quantize(Decimal("0.01"))

    def _try_auto_pay(self, invoice: Invoice) -> None:
        if invoice.status != InvoiceStatus.PENDING:
            return

        balances = self._balance_service.get_balances(invoice.from_entity_id)
        completed_balances = balances.completed or {}

        available_balances = {
            currency.lower(): self._balance_to_decimal(amount)
            for currency, amount in completed_balances.items()
        }
        selection = self._select_auto_pay_amount(invoice, available_balances)
        if selection is None:
            return
        selected_currency, selected_amount = selection
        if self._has_fee_allocations(invoice.id):
            if self._fee_allocation_service is None:
                return
            actor_entity = (
                self.db.query(Entity)
                .filter(Entity.id == invoice.actor_entity_id)
                .first()
            )
            if actor_entity is None:
                return
            self._fee_allocation_service.settle_fee_invoice(
                invoice.id,
                selected_currency,
                actor_entity,
                status=TransactionStatus.COMPLETED,
            )
            return

        if invoice.transactions:
            return

        tx_schema = TransactionCreateSchema(
            to_entity_id=invoice.to_entity_id,
            from_entity_id=invoice.from_entity_id,
            amount=selected_amount,
            currency=selected_currency,
            status=TransactionStatus.COMPLETED,
            invoice_id=invoice.id,
            comment=invoice.comment,
            tag_ids=[automatic_tag.id],
        )

        self._transaction_service.create(
            tx_schema, overrides={"actor_entity_id": invoice.actor_entity_id}
        )

    def auto_pay_oldest_invoices(self) -> int:
        pending_filter = [
            self.model.status == InvoiceStatus.PENDING,
        ]
        entity_ids = (
            self.db.query(self.model.from_entity_id)
            .filter(*pending_filter)
            .distinct()
            .all()
        )

        paid_count = 0

        for (entity_id,) in entity_ids:
            balances = self._balance_service.get_balances(entity_id)
            completed_balances = balances.completed or {}
            available_balances = {
                currency.lower(): self._balance_to_decimal(amount)
                for currency, amount in completed_balances.items()
            }

            invoices = (
                self.db.query(self.model)
                .filter(*pending_filter)
                .filter(self.model.from_entity_id == entity_id)
                .order_by(self.model.created_at.asc(), self.model.id.asc())
                .all()
            )

            for invoice in invoices:
                selection = self._select_auto_pay_amount(invoice, available_balances)
                if selection is None:
                    continue
                currency, amount = selection

                if self._has_fee_allocations(invoice.id):
                    if self._fee_allocation_service is None:
                        continue
                    actor_entity = (
                        self.db.query(Entity)
                        .filter(Entity.id == invoice.actor_entity_id)
                        .first()
                    )
                    if actor_entity is None:
                        continue
                    self._fee_allocation_service.settle_fee_invoice(
                        invoice.id,
                        currency,
                        actor_entity,
                        status=TransactionStatus.COMPLETED,
                    )
                    self.db.refresh(invoice)
                    if invoice.status == InvoiceStatus.PAID:
                        available_balances[currency] = (
                            available_balances[currency] - amount
                        )
                        paid_count += 1
                    continue

                if invoice.transactions:
                    continue

                tx_schema = TransactionCreateSchema(
                    to_entity_id=invoice.to_entity_id,
                    from_entity_id=invoice.from_entity_id,
                    amount=amount,
                    currency=currency,
                    status=TransactionStatus.COMPLETED,
                    invoice_id=invoice.id,
                    comment=invoice.comment,
                    tag_ids=[automatic_tag.id],
                )

                self._transaction_service.create(
                    tx_schema, overrides={"actor_entity_id": invoice.actor_entity_id}
                )
                available_balances[currency] = available_balances[currency] - amount
                paid_count += 1

        return paid_count

    @staticmethod
    def _normalize_billing_period(
        value: datetime.date | None,
    ) -> datetime.date | None:
        if value is None:
            return None
        return datetime.date(value.year, value.month, 1)

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
        fee_allocations = self._fee_allocations_for_invoice(invoice_id)
        if fee_allocations:
            self._validate_fee_settlement_transaction(
                invoice=invoice,
                allocations=fee_allocations,
                tx_id=tx_id,
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                amount=amount,
                currency=currency,
            )
            return

        invoice_transaction_ids = {
            transaction.id for transaction in invoice.transactions
        }
        if (
            invoice.status == InvoiceStatus.PAID
            and tx_id not in invoice_transaction_ids
        ):
            raise InvoiceAlreadyPaid
        if invoice_transaction_ids and tx_id not in invoice_transaction_ids:
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

    def _validate_fee_settlement_transaction(
        self,
        *,
        invoice: Invoice,
        allocations: list[FeeAllocation],
        tx_id: int | None,
        from_entity_id: int,
        to_entity_id: int,
        amount: Decimal,
        currency: str,
    ) -> None:
        if tx_id is None:
            raise InvoiceTransactionAlreadyAttached
        if invoice.status == InvoiceStatus.PAID and tx_id not in {
            allocation.allocation_transaction_id for allocation in allocations
        }:
            raise InvoiceAlreadyPaid
        allocation = next(
            (item for item in allocations if item.allocation_transaction_id == tx_id),
            None,
        )
        if allocation is None:
            raise InvoiceTransactionAlreadyAttached
        target_entity_id = self._resolve_fee_allocation_target_entity_id(allocation)
        if invoice.from_entity_id != from_entity_id or target_entity_id != to_entity_id:
            raise InvoiceEntitiesMismatch
        required_amount = self._fee_allocation_amount(allocation, currency)
        if required_amount is None:
            raise InvoiceCurrencyNotAllowed
        if amount.quantize(Decimal("0.01")) != required_amount:
            raise InvoiceAmountInsufficient

    def _fee_allocation_amount(
        self, allocation: FeeAllocation, currency: str
    ) -> Decimal | None:
        raw_amount = (allocation.amounts or {}).get(currency.lower())
        if raw_amount is None:
            return None
        amount = Decimal(str(raw_amount)).quantize(Decimal("0.01"))
        if allocation.component_key == "directed" and allocation.extra_amounts:
            extra = allocation.extra_amounts.get(currency.lower())
            if extra is not None:
                amount += Decimal(str(extra)).quantize(Decimal("0.01"))
        return amount

    def _resolve_fee_allocation_target_entity_id(
        self, allocation: FeeAllocation
    ) -> int | None:
        if allocation.target_type == FeeTargetType.ENTITY:
            return allocation.target_entity_id
        if (
            allocation.target_type == FeeTargetType.SPLIT
            and allocation.target_split_id is not None
        ):
            split = (
                self.db.query(Split)
                .filter(Split.id == allocation.target_split_id)
                .first()
            )
            return split.recipient_entity_id if split is not None else None
        return None

    def after_invoice_transaction_saved(self, tx: Transaction) -> None:
        if tx.invoice_id is None:
            return
        allocations = self._fee_allocations_for_invoice(tx.invoice_id)
        if not allocations:
            if tx.status == TransactionStatus.COMPLETED:
                invoice = self.get(tx.invoice_id)
                if invoice.status != InvoiceStatus.PAID:
                    invoice.status = InvoiceStatus.PAID
                    invoice.modified_at = datetime.datetime.now()
                    self.db.flush()
            return
        if tx.status == TransactionStatus.COMPLETED:
            self._record_fee_split_progress(tx, allocations)
            self.mark_fee_invoice_paid_if_settled(tx.invoice_id)

    def mark_fee_invoice_paid_if_settled(self, invoice_id: int) -> None:
        invoice = self.get(invoice_id)
        if invoice.status != InvoiceStatus.PENDING:
            return
        allocations = self._fee_allocations_for_invoice(invoice_id)
        if not allocations:
            return
        transaction_by_id = {
            transaction.id: transaction
            for transaction in self.db.query(Transaction)
            .filter(Transaction.invoice_id == invoice_id)
            .all()
        }
        for allocation in allocations:
            if allocation.allocation_transaction_id is None:
                return
            transaction = transaction_by_id.get(allocation.allocation_transaction_id)
            if transaction is None or transaction.status != TransactionStatus.COMPLETED:
                return
        invoice.status = InvoiceStatus.PAID
        invoice.modified_at = datetime.datetime.now()
        self.db.flush()

    def _record_fee_split_progress(
        self, tx: Transaction, allocations: list[FeeAllocation]
    ) -> None:
        allocation = next(
            (item for item in allocations if item.allocation_transaction_id == tx.id),
            None,
        )
        if (
            allocation is None
            or allocation.target_type != FeeTargetType.SPLIT
            or allocation.target_split_id is None
        ):
            return
        participant = (
            self.db.query(SplitParticipant)
            .filter(
                SplitParticipant.split_id == allocation.target_split_id,
                SplitParticipant.entity_id == tx.from_entity_id,
            )
            .first()
        )
        if participant is None:
            self.db.add(
                SplitParticipant(
                    split_id=allocation.target_split_id,
                    entity_id=tx.from_entity_id,
                    fixed_amount=tx.amount,
                )
            )
            self.db.flush()
            return
        participant.fixed_amount = (
            participant.fixed_amount or Decimal("0.00")
        ) + tx.amount
        self.db.flush()

    def bulk_create(
        self, schema: InvoiceBulkCreateSchema, actor_entity_id: int
    ) -> InvoiceBulkCreateReportSchema:
        from app.models.entity import Entity
        from app.models.tag import Tag

        billing_period = schema.billing_period
        if billing_period is None:
            today = date.today()
            billing_period = date(today.year, today.month, 1)
        else:
            billing_period = date(billing_period.year, billing_period.month, 1)

        entity_ids: set[int] = set(schema.from_entity_ids)

        if schema.from_tag_ids:
            tags = self.db.query(Tag).filter(Tag.id.in_(schema.from_tag_ids)).all()
            tag_filters = [Entity.tags.contains(tag) for tag in tags]
            if tag_filters:
                tag_entities = self.db.query(Entity).filter(or_(*tag_filters)).all()
                for e in tag_entities:
                    entity_ids.add(e.id)

        invoice_ids: list[int] = []
        created_count = 0
        skipped_count = 0

        for entity_id in sorted(entity_ids):
            entity = self.db.query(Entity).filter(Entity.id == entity_id).first()
            if entity is None or not entity.active:
                skipped_count += 1
                continue

            invoice = self.create(
                InvoiceCreateSchema(
                    from_entity_id=entity_id,
                    to_entity_id=schema.to_entity_id,
                    amounts=schema.amounts,
                    billing_period=billing_period,
                    tag_ids=schema.tag_ids,
                    comment=schema.comment,
                ),
                overrides={"actor_entity_id": actor_entity_id},
            )
            invoice_ids.append(invoice.id)
            created_count += 1

        return InvoiceBulkCreateReportSchema(
            billing_period=billing_period,
            created_count=created_count,
            skipped_count=skipped_count,
            invoice_ids=invoice_ids,
        )
