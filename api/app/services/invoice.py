"""Invoice service"""

import datetime
from datetime import date
from decimal import Decimal

from app.config import Config, get_config
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
    InvoiceInsufficientBalance,
    InvoiceIsMultiItem,
    InvoiceIsNotMultiItem,
    InvoiceItemAlreadyPaid,
    InvoiceItemAmountInsufficient,
    InvoiceItemCurrencyNotAllowed,
    InvoiceItemEntityRequired,
    InvoiceItemInvalidEntityTag,
    InvoiceItemNotFound,
    InvoiceNotEditable,
    InvoicePayItemsMismatch,
    InvoiceRecipientRotationInvalid,
    InvoiceTransactionAlreadyAttached,
)
from app.models.entity import Entity
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.transaction import TransactionStatus
from app.schemas.invoice import (
    InvoiceBulkCreateReportSchema,
    InvoiceBulkCreateSchema,
    InvoiceCreateSchema,
    InvoiceFiltersSchema,
    InvoiceUpdateSchema,
)
from app.schemas.invoice_item import InvoiceItemCreateSchema, InvoicePayItemsSchema
from app.schemas.transaction import TransactionCreateSchema
from app.seeding import automatic_tag, fee_tag
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
        config: Config = Depends(get_config),
    ):
        self.db = db
        self._tag_service = tag_service
        self._balance_service = balance_service
        self._transaction_service = transaction_service
        self._config = config

    def _rotated_recipient_id(self, tag_id: int, billing_period: date) -> int | None:
        for rotation in self._config.invoice_recipient_rotations:
            if rotation["tag_id"] != tag_id:
                continue
            anchor_year, anchor_month = map(
                int, rotation["anchor_period"].split("-", 1)
            )
            month_offset = (billing_period.year - anchor_year) * 12 + (
                billing_period.month - anchor_month
            )
            entity_ids = rotation["entity_ids"]
            recipient_id = entity_ids[month_offset % len(entity_ids)]
            recipient = self.db.query(Entity).filter(Entity.id == recipient_id).first()
            if recipient is None or not recipient.active:
                raise InvoiceRecipientRotationInvalid(
                    f"entity {recipient_id} for tag {tag_id} is missing or inactive"
                )
            if tag_id not in {tag.id for tag in recipient.tags}:
                raise InvoiceRecipientRotationInvalid(
                    f"entity {recipient_id} does not have tag {tag_id}"
                )
            return recipient_id
        return None

    def _apply_recipient_rotations(
        self,
        items: list[InvoiceItemCreateSchema],
        billing_period: date,
        *,
        require_configured_recipient: bool,
    ) -> list[InvoiceItemCreateSchema]:
        resolved: list[InvoiceItemCreateSchema] = []
        for original in items:
            item = original.model_copy(deep=True)
            if item.to_entity_id is None and item.to_tag_id is not None:
                item.to_entity_id = self._rotated_recipient_id(
                    item.to_tag_id, billing_period
                )
                if item.to_entity_id is None and require_configured_recipient:
                    raise InvoiceRecipientRotationInvalid(
                        f"no rotation configured for tag {item.to_tag_id}"
                    )
            resolved.append(item)
        return resolved

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
        items_data = data.pop("items", None)
        if items_data:
            # Multi-recipient invoice: no single to_entity or amounts
            data["to_entity_id"] = None
            data["amounts"] = []
        else:
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
        if items_data:
            for item_schema_dict in items_data:
                item_schema = InvoiceItemCreateSchema(**item_schema_dict)
                self._create_invoice_item(new_obj.id, item_schema)
        self.db.flush()
        self.db.refresh(new_obj)
        return new_obj

    def _create_invoice_item(
        self, invoice_id: int, schema: InvoiceItemCreateSchema
    ) -> InvoiceItem:
        amounts = self._serialize_amounts(
            [{"currency": a.currency, "amount": a.amount} for a in schema.amounts]
        )
        item = InvoiceItem(
            invoice_id=invoice_id,
            to_entity_id=schema.to_entity_id,
            to_tag_id=schema.to_tag_id,
            amounts=amounts,
            comment=schema.comment,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update(  # type: ignore[override]
        self, obj_id: int, schema: InvoiceUpdateSchema, overrides: dict = {}
    ) -> Invoice:
        db_obj = self.get(obj_id)
        if db_obj.status != InvoiceStatus.PENDING or db_obj.transaction is not None:
            raise InvoiceNotEditable
        # For multi-item invoices, also reject if any item already has a transaction
        if db_obj.items and any(item.transaction is not None for item in db_obj.items):
            raise InvoiceNotEditable
        data = schema.dump()
        tag_ids = data.pop("tag_ids", None)
        new_items_data = data.pop("items", None)
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
        if new_items_data is not None:
            # Replace all items
            for old_item in list(db_obj.items):
                self.db.delete(old_item)
            self.db.flush()
            for item_schema_dict in new_items_data:
                item_schema = InvoiceItemCreateSchema(**item_schema_dict)
                self._create_invoice_item(db_obj.id, item_schema)
        setattr(db_obj, "modified_at", datetime.datetime.now())
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, obj_id: int) -> int:  # type: ignore[override]
        db_obj = self.get(obj_id)
        if db_obj.status != InvoiceStatus.PENDING or db_obj.transaction is not None:
            raise InvoiceNotEditable
        if db_obj.items and any(item.transaction is not None for item in db_obj.items):
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

    def select_best_currency(
        self, from_entity_id: int, available_currencies: set[str]
    ) -> str | None:
        """Select the best currency based on entity balance. Prefers highest positive balance."""
        balances = self._balance_service.get_balances(from_entity_id)
        completed_balances = balances.completed or {}

        best_currency = None
        best_balance = Decimal("-999999")

        for curr in available_currencies:
            curr_lower = curr.lower()
            bal = self._balance_to_decimal(completed_balances.get(curr_lower))
            if bal > best_balance:
                best_balance = bal
                best_currency = curr_lower

        # Only return if balance is positive
        if best_currency and best_balance > Decimal("0"):
            return best_currency

        return None

    def _select_auto_pay_amount(
        self, invoice: Invoice, balances: dict[str, Decimal]
    ) -> tuple[str, Decimal] | None:
        selected_currency = None
        selected_amount = None
        selected_balance = None

        for entry in invoice.amounts or []:
            currency = str(entry.get("currency", "")).lower()
            if not currency:
                continue
            required_amount = Decimal(str(entry.get("amount", "0")))
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

    def auto_pay_oldest_invoices(self) -> int:
        grace_days = max(self._config.invoice_auto_pay_grace_days, 0)
        eligible_before = datetime.datetime.now() - datetime.timedelta(days=grace_days)
        # ── simple invoices (no items) ──────────────────────────────────────
        simple_pending_filter = [
            self.model.status == InvoiceStatus.PENDING,
            self.model.created_at <= eligible_before,
            ~self.model.transaction.has(),
            ~self.model.items.any(),
        ]
        entity_ids = (
            self.db.query(self.model.from_entity_id)
            .filter(*simple_pending_filter)
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
                .filter(*simple_pending_filter)
                .filter(self.model.from_entity_id == entity_id)
                .order_by(self.model.created_at.asc(), self.model.id.asc())
                .all()
            )

            for invoice in invoices:
                selection = self._select_auto_pay_amount(invoice, available_balances)
                if selection is None:
                    continue
                currency, amount = selection

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

        # ── multi-item invoices (only when every item has to_entity_id set) ─
        multi_pending_filter = [
            self.model.status == InvoiceStatus.PENDING,
            self.model.created_at <= eligible_before,
            self.model.items.any(),
        ]
        multi_entity_ids = (
            self.db.query(self.model.from_entity_id)
            .filter(*multi_pending_filter)
            .distinct()
            .all()
        )

        for (entity_id,) in multi_entity_ids:
            balances = self._balance_service.get_balances(entity_id)
            completed_balances = balances.completed or {}
            available_balances = {
                currency.lower(): self._balance_to_decimal(amount)
                for currency, amount in completed_balances.items()
            }

            invoices = (
                self.db.query(self.model)
                .filter(*multi_pending_filter)
                .filter(self.model.from_entity_id == entity_id)
                .order_by(self.model.created_at.asc(), self.model.id.asc())
                .all()
            )

            for invoice in invoices:
                # Skip if any item has no entity or is already paid
                if any(
                    item.to_entity_id is None or item.transaction is not None
                    for item in invoice.items
                ):
                    continue

                # Pre-select amounts for all items; skip invoice if any can't be paid
                selections: list[tuple[InvoiceItem, str, Decimal]] = []
                temp_balances = dict(available_balances)
                payable = True
                for item in invoice.items:
                    sel = self._select_auto_pay_amount(
                        item,  # type: ignore[arg-type]
                        temp_balances,
                    )
                    if sel is None:
                        payable = False
                        break
                    currency, amount = sel
                    temp_balances[currency] = temp_balances[currency] - amount
                    selections.append((item, currency, amount))

                if not payable:
                    continue

                for item, currency, amount in selections:
                    tx_schema = TransactionCreateSchema(
                        to_entity_id=item.to_entity_id,
                        from_entity_id=invoice.from_entity_id,
                        amount=amount,
                        currency=currency,
                        status=TransactionStatus.COMPLETED,
                        invoice_item_id=item.id,
                        comment=item.comment or invoice.comment,
                        tag_ids=[automatic_tag.id],
                    )
                    self._transaction_service.create(
                        tx_schema,
                        overrides={"actor_entity_id": invoice.actor_entity_id},
                    )

                available_balances = temp_balances
                invoice.status = InvoiceStatus.PAID
                invoice.modified_at = datetime.datetime.now()
                self.db.flush()
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
        if invoice.items:
            raise InvoiceIsMultiItem
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
        balances = self._balance_service.get_balances(from_entity_id)
        completed_balances = balances.completed or {}
        available = self._balance_to_decimal(completed_balances.get(currency.lower()))
        if available < amount:
            raise InvoiceInsufficientBalance
        if (
            status == TransactionStatus.COMPLETED
            and invoice.status != InvoiceStatus.PAID
        ):
            invoice.status = InvoiceStatus.PAID
            invoice.modified_at = datetime.datetime.now()
            self.db.flush()

    def pay_items(
        self,
        invoice_id: int,
        schema: InvoicePayItemsSchema,
        actor_entity_id: int,
    ) -> Invoice:
        """Atomically pay all items of a multi-recipient invoice."""
        invoice = self.get(invoice_id)
        if not invoice.items:
            raise InvoiceIsNotMultiItem
        if invoice.status == InvoiceStatus.CANCELLED:
            raise InvoiceCancelledNotPayable
        if invoice.status == InvoiceStatus.PAID:
            raise InvoiceAlreadyPaid

        # Validate that submitted item_ids exactly match invoice items
        invoice_item_ids = {item.id for item in invoice.items}
        submitted_item_ids = {p.item_id for p in schema.items}
        if invoice_item_ids != submitted_item_ids:
            raise InvoicePayItemsMismatch

        # Build item lookup
        item_by_id = {item.id: item for item in invoice.items}

        # If currency not specified in request, auto-select best currency
        # Collect all available currencies from invoice items
        available_currencies = set()
        for item in invoice.items:
            if item.amounts:
                for amount_obj in item.amounts:
                    # Handle both dict and object formats
                    currency = (
                        amount_obj.get("currency")
                        if isinstance(amount_obj, dict)
                        else amount_obj.currency
                    )
                    available_currencies.add(currency.lower())

        # Use service method to find best currency
        auto_selected_currency = self.select_best_currency(
            invoice.from_entity_id, available_currencies
        )

        # Get running balances for validation
        balances = self._balance_service.get_balances(invoice.from_entity_id)
        completed_balances = balances.completed or {}
        running_balances: dict[str, Decimal] = {}
        for currency, value in completed_balances.items():
            running_balances[currency.lower()] = self._balance_to_decimal(value)

        for payment in schema.items:
            item = item_by_id[payment.item_id]
            if item.transaction is not None:
                raise InvoiceItemAlreadyPaid
            if not payment.to_entity_id:
                raise InvoiceItemEntityRequired
            # Validate entity-tag constraint if present
            if item.to_tag_id is not None:
                entity = (
                    self.db.query(Entity)
                    .filter(Entity.id == payment.to_entity_id)
                    .first()
                )
                if entity is None or not entity.active:
                    raise InvoiceItemEntityRequired
                tag_ids = {tag.id for tag in entity.tags}
                if item.to_tag_id not in tag_ids:
                    raise InvoiceItemInvalidEntityTag

            # Determine currency to use for this payment
            currency = payment.currency or auto_selected_currency
            if not currency:
                raise InvoiceCurrencyNotAllowed

            currency = currency.lower()

            # Validate currency allowed for this item
            required_amount = self._required_amount_for_currency(
                item,  # type: ignore[arg-type]
                currency,
            )
            if required_amount is None:
                raise InvoiceItemCurrencyNotAllowed
            # Use required amount from invoice item if not specified in payment
            effective_amount = (
                payment.amount if payment.amount is not None else required_amount
            )
            if effective_amount < required_amount:
                raise InvoiceItemAmountInsufficient
            # Deduct from running balance check
            current = running_balances.get(currency, Decimal("0"))
            if current < effective_amount:
                raise InvoiceInsufficientBalance
            running_balances[currency] = current - effective_amount

        # All validated — create transactions
        for payment in schema.items:
            item = item_by_id[payment.item_id]

            # Determine currency for this payment
            currency = (payment.currency or auto_selected_currency or "").lower()
            if not currency:
                raise InvoiceCurrencyNotAllowed

            # Use required amount from invoice item if not specified
            tx_amount = payment.amount if payment.amount is not None else self._required_amount_for_currency(item, currency)  # type: ignore[arg-type]

            tx_schema = TransactionCreateSchema(
                to_entity_id=payment.to_entity_id,
                from_entity_id=invoice.from_entity_id,
                amount=tx_amount,
                currency=currency,
                status=TransactionStatus.COMPLETED,
                invoice_id=invoice.id,
                invoice_item_id=item.id,
                comment=item.comment or invoice.comment,
                tag_ids=list({tag.id for tag in invoice.tags}),
            )
            self._transaction_service.create(
                tx_schema, overrides={"actor_entity_id": actor_entity_id}
            )

        invoice.status = InvoiceStatus.PAID
        invoice.modified_at = datetime.datetime.now()
        self.db.flush()
        self.db.refresh(invoice)
        return invoice

    def validate_transaction_for_invoice_item(
        self,
        *,
        item_id: int,
        tx_id: int | None,
        from_entity_id: int,
        to_entity_id: int,
        amount: Decimal,
        currency: str,
        status: TransactionStatus,
    ) -> None:
        """Validate a transaction that targets an individual invoice item."""
        item = self.db.query(InvoiceItem).filter(InvoiceItem.id == item_id).first()
        if item is None:
            raise InvoiceItemNotFound
        invoice = item.invoice
        if invoice.status == InvoiceStatus.CANCELLED:
            raise InvoiceCancelledNotPayable
        if item.transaction is not None and item.transaction.id != tx_id:
            raise InvoiceItemAlreadyPaid
        if invoice.from_entity_id != from_entity_id:
            raise InvoiceEntitiesMismatch
        currency_lower = currency.lower()
        required_amount = self._required_amount_for_currency(
            item,  # type: ignore[arg-type]
            currency_lower,
        )
        if required_amount is None:
            raise InvoiceItemCurrencyNotAllowed
        if amount < required_amount:
            raise InvoiceItemAmountInsufficient
        balances = self._balance_service.get_balances(from_entity_id)
        completed_balances = balances.completed or {}
        available = self._balance_to_decimal(completed_balances.get(currency_lower))
        if available < amount:
            raise InvoiceInsufficientBalance
        if status == TransactionStatus.COMPLETED and item.transaction is None:
            # Check if this is the last unpaid item -> mark invoice PAID
            all_paid = all(
                (i.transaction is not None and i.id != item_id) or i.id == item_id
                for i in invoice.items
            )
            if all_paid and invoice.status != InvoiceStatus.PAID:
                invoice.status = InvoiceStatus.PAID
                invoice.modified_at = datetime.datetime.now()
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

        resolved_items = self._apply_recipient_rotations(
            schema.items,
            billing_period,
            require_configured_recipient=(
                bool(schema.items) and fee_tag.id in schema.tag_ids
            ),
        )

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

            if resolved_items:
                # Multi-item invoice mode
                invoice = self.create(
                    InvoiceCreateSchema(
                        from_entity_id=entity_id,
                        to_entity_id=None,
                        amounts=[],
                        billing_period=billing_period,
                        tag_ids=schema.tag_ids,
                        comment=schema.comment,
                        items=resolved_items,
                    ),
                    overrides={"actor_entity_id": actor_entity_id},
                )
            else:
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

    def reconcile_recipient_rotations(self, *, apply: bool = False) -> list[dict]:
        """Find and optionally fill missing rotated recipients on pending fees."""
        rotation_tag_ids = {
            rotation["tag_id"] for rotation in self._config.invoice_recipient_rotations
        }
        invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.billing_period.isnot(None),
                Invoice.items.any(),
                Invoice.tags.contains(fee_tag),
            )
            .order_by(Invoice.id)
            .all()
        )
        changes: list[dict] = []
        for invoice in invoices:
            if invoice.billing_period is None:
                continue
            unresolved_items = [
                item
                for item in invoice.items
                if item.to_entity_id is None and item.to_tag_id is not None
            ]
            for item in unresolved_items:
                previous_tag_id = item.to_tag_id
                target_tag_id = previous_tag_id
                if target_tag_id not in rotation_tag_ids:
                    if len(rotation_tag_ids) != 1 or len(unresolved_items) != 1:
                        raise InvoiceRecipientRotationInvalid(
                            f"cannot infer rotation tag for invoice {invoice.id} "
                            f"item {item.id} constrained to tag {previous_tag_id}"
                        )
                    target_tag_id = next(iter(rotation_tag_ids))
                recipient_id = self._rotated_recipient_id(
                    target_tag_id, invoice.billing_period
                )
                if recipient_id is None:
                    raise InvoiceRecipientRotationInvalid(
                        f"no rotation configured for tag {target_tag_id}"
                    )
                changes.append(
                    {
                        "invoice_id": invoice.id,
                        "item_id": item.id,
                        "billing_period": invoice.billing_period.isoformat(),
                        "previous_to_tag_id": previous_tag_id,
                        "to_tag_id": target_tag_id,
                        "to_entity_id": recipient_id,
                    }
                )
                if apply:
                    item.to_tag_id = target_tag_id
                    item.to_entity_id = recipient_id
                    item.modified_at = datetime.datetime.now()
        if apply and changes:
            self.db.flush()
        return changes
