"""Service for directed monthly fee invoices and allocations."""

import datetime
import json
import random
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from app.config import (
    DEFAULT_GENERAL_PURCHASE_FUND_ENTITY_ID,
    Config,
    get_config,
)
from app.dependencies.services import (
    get_invoice_service,
    get_notification_service,
    get_transaction_service,
)
from app.errors.fee import (
    FeeAllocationAlreadySettled,
    FeeAllocationNotFound,
    FeeAllocationSelectionForbidden,
    FeeAllocationTargetInvalid,
    FeePolicyForbidden,
    FeeRuleNotFound,
)
from app.models.entity import Entity
from app.models.fee import (
    FeeAllocation,
    FeePolicyOverride,
    FeePolicyOverrideKind,
    FeeTargetType,
)
from app.models.invoice import Invoice, InvoiceStatus
from app.models.split import Split
from app.models.tag import Tag
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.base import CurrencyDecimal
from app.schemas.fee import (
    FeeAllocationSchema,
    FeeAllocationSelectionSchema,
    FeeConfigSchema,
    FeeDirectedAllocationUpdateSchema,
    FeeInvoiceBulkCreateReportSchema,
    FeeInvoiceBulkCreateSchema,
    FeePolicyOverrideSchema,
    FeePolicyOverrideUpdateSchema,
    FeeRuleSchema,
    FeeTargetSchema,
)
from app.schemas.invoice import InvoiceAmountCreateSchema, InvoiceCreateSchema
from app.schemas.transaction import TransactionCreateSchema, TransactionUpdateSchema
from app.seeding import (
    automatic_tag,
    crowdfunding_target_tag,
    f0_entity,
    fee_allocation_tag,
    fee_budget_target_tag,
    fee_tag,
)
from app.services.notification import NotificationService
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

if TYPE_CHECKING:
    from app.services.invoice import InvoiceService


@dataclass(frozen=True, slots=True)
class FeeRule:
    membership_tag_id: int
    label: str
    invoice_amounts: dict[str, Decimal]
    legacy_invoice_amounts: dict[str, Decimal]
    directed_amounts: dict[str, Decimal]
    fixed_allocations: list[dict[str, object]]
    default_directed_target_entity_id: int


@dataclass(frozen=True, slots=True)
class FeeTarget:
    target_type: FeeTargetType
    id: int
    name: str
    currency: str | None = None

    def to_schema(self) -> FeeTargetSchema:
        return FeeTargetSchema(
            target_type=self.target_type,
            id=self.id,
            name=self.name,
            currency=self.currency,
        )


class FeeAllocationService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        config: Config = Depends(get_config),
        transaction_service: TransactionService = Depends(get_transaction_service),
        invoice_service: "InvoiceService" = Depends(get_invoice_service),
        notification_service: NotificationService = Depends(get_notification_service),
    ):
        self.db = db
        self.config = config
        self._transaction_service = transaction_service
        self._invoice_service = invoice_service
        self._notification_service = notification_service

    @staticmethod
    def _decimal_map(raw_amounts: dict[str, object]) -> dict[str, Decimal]:
        normalized: dict[str, Decimal] = {}
        for currency, amount in raw_amounts.items():
            normalized[str(currency).lower()] = Decimal(str(amount)).quantize(
                Decimal("0.01")
            )
        return normalized

    @staticmethod
    def _serialize_amounts(amounts: dict[str, Decimal]) -> dict[str, str]:
        return {
            currency.lower(): format(amount.quantize(Decimal("0.01")), "f")
            for currency, amount in amounts.items()
        }

    @staticmethod
    def _amounts_to_invoice_payload(
        amounts: dict[str, Decimal],
    ) -> list[InvoiceAmountCreateSchema]:
        return [
            InvoiceAmountCreateSchema(currency=currency, amount=amount)
            for currency, amount in sorted(amounts.items())
        ]

    def _rules(self) -> list[FeeRule]:
        rules: list[FeeRule] = []
        for raw_rule in self.config.fee_rules:
            membership_tag_id = int(str(raw_rule["membership_tag_id"]))
            raw_invoice_amounts = raw_rule.get("invoice_amounts", {})
            raw_legacy_amounts = raw_rule.get("legacy_invoice_amounts", {})
            raw_directed_amounts = raw_rule.get("directed_amounts", {})
            raw_fixed_allocations = raw_rule.get("fixed_allocations", [])
            invoice_amounts = (
                self._decimal_map(raw_invoice_amounts)
                if isinstance(raw_invoice_amounts, dict)
                else {}
            )
            legacy_invoice_amounts = (
                self._decimal_map(raw_legacy_amounts)
                if isinstance(raw_legacy_amounts, dict)
                else {}
            )
            directed_amounts = (
                self._decimal_map(raw_directed_amounts)
                if isinstance(raw_directed_amounts, dict)
                else {}
            )
            fixed_allocations = (
                raw_fixed_allocations if isinstance(raw_fixed_allocations, list) else []
            )
            rules.append(
                FeeRule(
                    membership_tag_id=membership_tag_id,
                    label=str(raw_rule["label"]),
                    invoice_amounts=invoice_amounts,
                    legacy_invoice_amounts=legacy_invoice_amounts,
                    directed_amounts=directed_amounts,
                    fixed_allocations=fixed_allocations,
                    default_directed_target_entity_id=int(
                        str(
                            raw_rule.get(
                                "default_directed_target_entity_id",
                                DEFAULT_GENERAL_PURCHASE_FUND_ENTITY_ID,
                            )
                        )
                    ),
                )
            )
        return rules

    def _rule_for_tag_id(self, tag_id: int) -> FeeRule:
        for rule in self._rules():
            if rule.membership_tag_id == tag_id:
                return rule
        raise FeeRuleNotFound(tag_id)

    def _rule_for_entity(
        self, entity: Entity, allowed_tag_ids: set[int]
    ) -> FeeRule | None:
        entity_tag_ids = {tag.id for tag in entity.tags}
        for rule in self._rules():
            if (
                rule.membership_tag_id in allowed_tag_ids
                and rule.membership_tag_id in entity_tag_ids
            ):
                return rule
        return None

    def _is_finance_actor(self, actor_entity: Entity) -> bool:
        return (
            actor_entity.id == f0_entity.id
            or actor_entity.id in self.config.finance_entity_ids
        )

    def _assert_finance_actor(self, actor_entity: Entity) -> None:
        if not self._is_finance_actor(actor_entity):
            raise FeePolicyForbidden

    def _assert_selection_access(self, invoice: Invoice, actor_entity: Entity) -> None:
        if invoice.from_entity_id == actor_entity.id or self._is_finance_actor(
            actor_entity
        ):
            return
        raise FeeAllocationSelectionForbidden

    @staticmethod
    def _normalize_billing_period(value: datetime.date | None) -> datetime.date:
        if value is None:
            today = datetime.date.today()
            return datetime.date(today.year, today.month, 1)
        return datetime.date(value.year, value.month, 1)

    def _legacy_override_for_entity(self, entity_id: int) -> FeePolicyOverride | None:
        return (
            self.db.query(FeePolicyOverride)
            .filter(
                FeePolicyOverride.entity_id == entity_id,
                FeePolicyOverride.kind == FeePolicyOverrideKind.LEGACY,
                FeePolicyOverride.active.is_(True),
            )
            .first()
        )

    def get_config(self) -> FeeConfigSchema:
        return FeeConfigSchema(
            rules=[
                FeeRuleSchema(
                    membership_tag_id=rule.membership_tag_id,
                    label=rule.label,
                    invoice_amounts={
                        currency: CurrencyDecimal(amount)
                        for currency, amount in rule.invoice_amounts.items()
                    },
                    legacy_invoice_amounts={
                        currency: CurrencyDecimal(amount)
                        for currency, amount in rule.legacy_invoice_amounts.items()
                    },
                    directed_amounts={
                        currency: CurrencyDecimal(amount)
                        for currency, amount in rule.directed_amounts.items()
                    },
                )
                for rule in self._rules()
            ],
            budget_targets=[
                target.to_schema() for target in self.list_budget_targets()
            ],
            split_targets=[
                target.to_schema() for target in self.list_eligible_split_targets(None)
            ],
            selection_deadline_days=self.config.fee_selection_deadline_days,
        )

    def list_budget_targets(self) -> list[FeeTarget]:
        entities = (
            self.db.query(Entity)
            .join(Entity.tags)
            .filter(Tag.id == fee_budget_target_tag.id, Entity.active.is_(True))
            .order_by(Entity.name.asc())
            .all()
        )
        return [
            FeeTarget(target_type=FeeTargetType.ENTITY, id=entity.id, name=entity.name)
            for entity in entities
        ]

    def list_eligible_split_targets(self, currency: str | None) -> list[FeeTarget]:
        query = (
            self.db.query(Split)
            .join(Split.tags)
            .filter(Tag.id == crowdfunding_target_tag.id, Split.performed.is_(False))
        )
        if currency:
            query = query.filter(Split.currency == currency.lower())
        splits = query.order_by(Split.id.desc()).all()
        return [
            FeeTarget(
                target_type=FeeTargetType.SPLIT,
                id=split.id,
                name=split.comment or f"split #{split.id}",
                currency=split.currency,
            )
            for split in splits
        ]

    def _primary_invoice_currency(self, invoice: Invoice) -> str | None:
        if invoice.transactions:
            return invoice.transactions[0].currency.lower()
        for amount in invoice.amounts or []:
            currency = str(amount.get("currency", "")).lower()
            if currency:
                return currency
        return None

    def _selection_deadline(self, invoice: Invoice) -> datetime.datetime:
        created_at = invoice.created_at or datetime.datetime.now()
        return created_at + datetime.timedelta(
            days=self.config.fee_selection_deadline_days
        )

    def _base_amounts_for_rule(self, rule: FeeRule) -> dict[str, Decimal]:
        allocated: dict[str, Decimal] = {
            currency: Decimal("0.00") for currency in rule.invoice_amounts
        }
        for fixed in rule.fixed_allocations:
            raw_amounts = fixed.get("amounts", {})
            if not isinstance(raw_amounts, dict):
                continue
            for currency, amount in self._decimal_map(raw_amounts).items():
                allocated[currency] = allocated.get(currency, Decimal("0.00")) + amount
        for currency, amount in rule.directed_amounts.items():
            allocated[currency] = allocated.get(currency, Decimal("0.00")) + amount

        base_amounts: dict[str, Decimal] = {}
        for currency, invoice_amount in rule.invoice_amounts.items():
            amount = (
                invoice_amount - allocated.get(currency, Decimal("0.00"))
            ).quantize(Decimal("0.01"))
            if amount > Decimal("0.00"):
                base_amounts[currency] = amount
        return base_amounts

    def _create_allocations_for_invoice(self, invoice: Invoice, rule: FeeRule) -> None:
        deadline = self._selection_deadline(invoice)
        base_amounts = self._base_amounts_for_rule(rule)
        if base_amounts:
            self.db.add(
                FeeAllocation(
                    invoice_id=invoice.id,
                    component_key="base",
                    amounts=self._serialize_amounts(base_amounts),
                    target_type=FeeTargetType.ENTITY,
                    target_entity_id=f0_entity.id,
                    selected_at=invoice.created_at,
                    selection_deadline_at=deadline,
                )
            )
        for fixed in rule.fixed_allocations:
            raw_amounts = fixed.get("amounts", {})
            if not isinstance(raw_amounts, dict):
                continue
            amounts = self._decimal_map(raw_amounts)
            target_entity_id = int(str(fixed["target_entity_id"]))
            self.db.add(
                FeeAllocation(
                    invoice_id=invoice.id,
                    component_key=str(fixed["component_key"]),
                    amounts=self._serialize_amounts(amounts),
                    target_type=FeeTargetType.ENTITY,
                    target_entity_id=target_entity_id,
                    selected_at=invoice.created_at,
                    selection_deadline_at=deadline,
                )
            )
        if rule.directed_amounts:
            self.db.add(
                FeeAllocation(
                    invoice_id=invoice.id,
                    component_key="directed",
                    amounts=self._serialize_amounts(rule.directed_amounts),
                    target_type=None,
                    target_entity_id=None,
                    target_split_id=None,
                    selection_deadline_at=deadline,
                )
            )
        self.db.flush()

    def create_fee_invoices(
        self,
        schema: FeeInvoiceBulkCreateSchema,
        actor_entity: Entity,
    ) -> FeeInvoiceBulkCreateReportSchema:
        if not schema.from_tag_ids:
            raise FeeRuleNotFound("from_tag_ids")

        billing_period = self._normalize_billing_period(schema.billing_period)
        allowed_tag_ids = set(schema.from_tag_ids)
        tags = self.db.query(Tag).filter(Tag.id.in_(schema.from_tag_ids)).all()
        tag_filters = [Entity.tags.contains(tag) for tag in tags]
        entity_ids: set[int] = set()
        if tag_filters:
            entities = (
                self.db.query(Entity)
                .filter(or_(*tag_filters))
                .options(selectinload(Entity.tags))
                .all()
            )
            for entity in entities:
                entity_ids.add(entity.id)

        invoice_ids: list[int] = []
        created_count = 0
        skipped_count = 0
        legacy_count = 0
        notification_count = 0

        for entity_id in sorted(entity_ids):
            db_entity = (
                self.db.query(Entity)
                .filter(Entity.id == entity_id)
                .options(selectinload(Entity.tags))
                .first()
            )
            if db_entity is None or not db_entity.active:
                skipped_count += 1
                continue
            rule = self._rule_for_entity(db_entity, allowed_tag_ids)
            if rule is None:
                skipped_count += 1
                continue
            legacy = self._legacy_override_for_entity(db_entity.id) is not None
            amounts = rule.legacy_invoice_amounts if legacy else rule.invoice_amounts
            invoice = self._invoice_service.create(
                InvoiceCreateSchema(
                    from_entity_id=db_entity.id,
                    to_entity_id=f0_entity.id,
                    amounts=self._amounts_to_invoice_payload(amounts),
                    billing_period=billing_period,
                    tag_ids=[fee_tag.id],
                    comment=f"{rule.label} monthly fee",
                ),
                overrides={
                    "actor_entity_id": actor_entity.id,
                    "_skip_auto_pay": True,
                },
            )
            invoice_ids.append(invoice.id)
            created_count += 1
            if legacy:
                legacy_count += 1
                if schema.notify and self._notify_legacy_invoice(invoice, db_entity):
                    notification_count += 1
                continue
            self._create_allocations_for_invoice(invoice, rule)
            directed = self._directed_allocation(invoice.id)
            if (
                schema.notify
                and directed is not None
                and self._notify_fee_invoice(invoice, db_entity, directed)
            ):
                notification_count += 1

        return FeeInvoiceBulkCreateReportSchema(
            billing_period=billing_period,
            created_count=created_count,
            skipped_count=skipped_count,
            legacy_count=legacy_count,
            invoice_ids=invoice_ids,
            notification_count=notification_count,
        )

    def _allocations_for_invoice(self, invoice_id: int) -> list[FeeAllocation]:
        return (
            self.db.query(FeeAllocation)
            .filter(FeeAllocation.invoice_id == invoice_id)
            .order_by(FeeAllocation.id.asc())
            .all()
        )

    def _directed_allocation(self, invoice_id: int) -> FeeAllocation | None:
        return (
            self.db.query(FeeAllocation)
            .filter(
                FeeAllocation.invoice_id == invoice_id,
                FeeAllocation.component_key == "directed",
            )
            .first()
        )

    def _invoice_has_settlement(self, invoice_id: int) -> bool:
        return (
            self.db.query(FeeAllocation)
            .filter(
                FeeAllocation.invoice_id == invoice_id,
                FeeAllocation.allocation_transaction_id.isnot(None),
            )
            .first()
            is not None
        )

    def _allocation_to_schema(self, allocation: FeeAllocation) -> FeeAllocationSchema:
        return FeeAllocationSchema(
            id=allocation.id,
            invoice_id=allocation.invoice_id,
            component_key=allocation.component_key,
            amounts={
                currency: CurrencyDecimal(Decimal(str(amount)))
                for currency, amount in (allocation.amounts or {}).items()
            },
            extra_amounts=(
                {
                    currency: CurrencyDecimal(Decimal(str(amount)))
                    for currency, amount in allocation.extra_amounts.items()
                }
                if allocation.extra_amounts
                else None
            ),
            target_type=allocation.target_type,
            target_entity_id=allocation.target_entity_id,
            target_split_id=allocation.target_split_id,
            selected_by_entity_id=allocation.selected_by_entity_id,
            selected_at=allocation.selected_at,
            auto_selected=allocation.auto_selected,
            selection_deadline_at=allocation.selection_deadline_at,
            allocation_transaction_id=allocation.allocation_transaction_id,
        )

    def _target_name(self, allocation: FeeAllocation | None) -> str | None:
        if allocation is None or allocation.target_type is None:
            return None
        if (
            allocation.target_type == FeeTargetType.ENTITY
            and allocation.target_entity_id
        ):
            entity = (
                self.db.query(Entity)
                .filter(Entity.id == allocation.target_entity_id)
                .first()
            )
            return entity.name if entity else None
        if allocation.target_type == FeeTargetType.SPLIT and allocation.target_split_id:
            split = (
                self.db.query(Split)
                .filter(Split.id == allocation.target_split_id)
                .first()
            )
            if split is None:
                return None
            return split.comment or f"split #{split.id}"
        return None

    def get_selection(
        self,
        invoice_id: int,
        actor_entity: Entity,
    ) -> FeeAllocationSelectionSchema:
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice is None:
            raise FeeAllocationNotFound(invoice_id)
        self._assert_selection_access(invoice, actor_entity)
        allocations = self._allocations_for_invoice(invoice_id)
        directed = next(
            (
                allocation
                for allocation in allocations
                if allocation.component_key == "directed"
            ),
            None,
        )
        currency = self._primary_invoice_currency(invoice)
        return FeeAllocationSelectionSchema(
            has_allocation=directed is not None,
            invoice_id=invoice_id,
            directed_allocation=(
                self._allocation_to_schema(directed) if directed is not None else None
            ),
            fixed_allocations=[
                self._allocation_to_schema(allocation)
                for allocation in allocations
                if allocation.component_key != "directed"
            ],
            budget_targets=[
                target.to_schema() for target in self.list_budget_targets()
            ],
            split_targets=[
                target.to_schema()
                for target in self.list_eligible_split_targets(currency)
            ],
            selected_target_name=self._target_name(directed),
        )

    def _validate_target(
        self,
        schema: FeeDirectedAllocationUpdateSchema,
        currency: str | None,
    ) -> FeeTarget:
        if schema.target_type == FeeTargetType.ENTITY:
            if schema.target_entity_id is None:
                raise FeeAllocationTargetInvalid("target_entity_id")
            target = (
                self.db.query(Entity)
                .join(Entity.tags)
                .filter(
                    Entity.id == schema.target_entity_id,
                    Entity.active.is_(True),
                    Tag.id == fee_budget_target_tag.id,
                )
                .first()
            )
            if target is None:
                raise FeeAllocationTargetInvalid("entity")
            return FeeTarget(FeeTargetType.ENTITY, target.id, target.name)

        if schema.target_split_id is None:
            raise FeeAllocationTargetInvalid("target_split_id")
        split = (
            self.db.query(Split)
            .join(Split.tags)
            .filter(
                Split.id == schema.target_split_id,
                Split.performed.is_(False),
                Tag.id == crowdfunding_target_tag.id,
            )
            .first()
        )
        if split is None:
            raise FeeAllocationTargetInvalid("split")
        if currency is not None and split.currency.lower() != currency.lower():
            raise FeeAllocationTargetInvalid("currency")
        return FeeTarget(
            FeeTargetType.SPLIT,
            split.id,
            split.comment or f"split #{split.id}",
            split.currency,
        )

    def update_directed_allocation(
        self,
        invoice_id: int,
        schema: FeeDirectedAllocationUpdateSchema,
        actor_entity: Entity,
    ) -> FeeAllocationSelectionSchema:
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice is None:
            raise FeeAllocationNotFound(invoice_id)
        self._assert_selection_access(invoice, actor_entity)
        allocation = self._directed_allocation(invoice_id)
        if allocation is None:
            raise FeeAllocationNotFound(invoice_id)
        if self._invoice_has_settlement(invoice_id):
            raise FeeAllocationAlreadySettled

        currency = self._primary_invoice_currency(invoice)
        target = self._validate_target(schema, currency)
        allocation.target_type = target.target_type
        allocation.target_entity_id = (
            target.id if target.target_type == FeeTargetType.ENTITY else None
        )
        allocation.target_split_id = (
            target.id if target.target_type == FeeTargetType.SPLIT else None
        )
        allocation.selected_by_entity_id = actor_entity.id
        allocation.selected_at = datetime.datetime.now()
        allocation.auto_selected = False

        if schema.extra_amount is not None and schema.extra_amount > Decimal("0"):
            extra_currency = (schema.extra_currency or currency or "").lower()
            if not extra_currency:
                raise FeeAllocationTargetInvalid("extra_currency")
            allocation.extra_amounts = {
                extra_currency: format(
                    schema.extra_amount.quantize(Decimal("0.01")), "f"
                )
            }
        else:
            allocation.extra_amounts = None

        self.db.flush()
        self.db.refresh(allocation)
        return self.get_selection(invoice_id, actor_entity)

    @staticmethod
    def choose_random_target(invoice_id: int, targets: list[FeeTarget]) -> FeeTarget:
        rng = random.Random(f"fee-allocation:{invoice_id}")
        return rng.choice(
            sorted(targets, key=lambda item: (item.target_type.value, item.id))
        )

    def _eligible_random_targets(self, currency: str | None) -> list[FeeTarget]:
        budget_targets = self.list_budget_targets()
        split_targets = self.list_eligible_split_targets(currency)
        return budget_targets + split_targets

    def auto_select_expired_allocations(
        self,
        now: datetime.datetime | None = None,
    ) -> int:
        now = now or datetime.datetime.now()
        allocations = (
            self.db.query(FeeAllocation)
            .filter(
                FeeAllocation.component_key == "directed",
                FeeAllocation.selected_at.is_(None),
                FeeAllocation.selection_deadline_at <= now,
            )
            .all()
        )
        selected_count = 0
        for allocation in allocations:
            invoice = (
                self.db.query(Invoice)
                .filter(Invoice.id == allocation.invoice_id)
                .first()
            )
            if invoice is None:
                continue
            currency = self._primary_invoice_currency(invoice)
            targets = self._eligible_random_targets(currency)
            if not targets:
                continue
            target = self.choose_random_target(allocation.invoice_id, targets)
            allocation.target_type = target.target_type
            allocation.target_entity_id = (
                target.id if target.target_type == FeeTargetType.ENTITY else None
            )
            allocation.target_split_id = (
                target.id if target.target_type == FeeTargetType.SPLIT else None
            )
            allocation.selected_by_entity_id = None
            allocation.selected_at = now
            allocation.auto_selected = True
            self.db.flush()
            self._notify_auto_selection(invoice, allocation)
            selected_count += 1
        return selected_count

    def _required_invoice_amount(self, invoice: Invoice, currency: str) -> Decimal:
        for amount in invoice.amounts or []:
            if str(amount.get("currency", "")).lower() == currency.lower():
                return Decimal(str(amount.get("amount", "0"))).quantize(Decimal("0.01"))
        return Decimal("0.00")

    def requested_extra_amount(self, invoice_id: int, currency: str) -> Decimal:
        allocation = self._directed_allocation(invoice_id)
        if allocation is None or not allocation.extra_amounts:
            return Decimal("0.00")
        amount = allocation.extra_amounts.get(currency.lower())
        if amount is None:
            return Decimal("0.00")
        return Decimal(str(amount)).quantize(Decimal("0.01"))

    def invoice_has_unselected_directed_allocation(self, invoice_id: int) -> bool:
        allocation = self._directed_allocation(invoice_id)
        return allocation is not None and allocation.selected_at is None

    def settle_fee_invoice(
        self,
        invoice_id: int,
        currency: str,
        actor_entity: Entity,
        status: TransactionStatus = TransactionStatus.DRAFT,
    ) -> list[Transaction]:
        invoice = (
            self.db.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .options(selectinload(Invoice.transactions))
            .first()
        )
        if invoice is None:
            raise FeeAllocationNotFound(invoice_id)
        self._assert_selection_access(invoice, actor_entity)
        if invoice.status != InvoiceStatus.PENDING:
            raise FeeAllocationAlreadySettled
        allocations = self._allocations_for_invoice(invoice_id)
        if not allocations:
            raise FeeAllocationNotFound(invoice_id)
        allocations = self._ensure_base_allocation(invoice, allocations)

        normalized_currency = currency.lower()
        directed = self._directed_allocation(invoice_id)
        if directed is not None and directed.selected_at is None:
            raise FeeAllocationTargetInvalid("directed")

        component_rows = self._settlement_component_rows(
            invoice=invoice,
            allocations=allocations,
            currency=normalized_currency,
        )

        transactions: list[Transaction] = []
        for allocation, amount, target_entity_id in component_rows:
            existing = self._allocation_transaction(allocation)
            if existing is not None:
                if (
                    status == TransactionStatus.COMPLETED
                    and existing.status == TransactionStatus.DRAFT
                ):
                    existing = self._transaction_service.update(
                        existing.id,
                        TransactionUpdateSchema(status=TransactionStatus.COMPLETED),
                        overrides={"actor_entity_id": actor_entity.id},
                    )
                transactions.append(existing)
                continue

            tx = self._transaction_service.create(
                TransactionCreateSchema(
                    from_entity_id=invoice.from_entity_id,
                    to_entity_id=target_entity_id,
                    amount=amount,
                    currency=normalized_currency,
                    status=status,
                    invoice_id=invoice.id,
                    comment=(
                        f"Fee settlement for invoice #{invoice.id}: "
                        f"{allocation.component_key}"
                    ),
                    tag_ids=[fee_allocation_tag.id, automatic_tag.id],
                ),
                overrides={
                    "actor_entity_id": actor_entity.id,
                    "_skip_invoice_validation": True,
                },
            )
            allocation.allocation_transaction_id = tx.id
            self.db.flush()
            self._invoice_service.after_invoice_transaction_saved(tx)
            transactions.append(tx)

        self._invoice_service.mark_fee_invoice_paid_if_settled(invoice_id)
        return transactions

    def _ensure_base_allocation(
        self, invoice: Invoice, allocations: list[FeeAllocation]
    ) -> list[FeeAllocation]:
        if any(allocation.component_key == "base" for allocation in allocations):
            return allocations

        allocated: dict[str, Decimal] = {}
        for allocation in allocations:
            for currency, raw_amount in (allocation.amounts or {}).items():
                allocated[currency.lower()] = allocated.get(
                    currency.lower(), Decimal("0.00")
                ) + Decimal(str(raw_amount)).quantize(Decimal("0.01"))

        base_amounts: dict[str, Decimal] = {}
        for invoice_amount in invoice.amounts or []:
            currency = str(invoice_amount.get("currency", "")).lower()
            if not currency:
                continue
            base_amount = Decimal(str(invoice_amount.get("amount", "0"))).quantize(
                Decimal("0.01")
            ) - allocated.get(currency, Decimal("0.00"))
            if base_amount > Decimal("0.00"):
                base_amounts[currency] = base_amount
        if not base_amounts:
            return allocations

        base_allocation = FeeAllocation(
            invoice_id=invoice.id,
            component_key="base",
            amounts=self._serialize_amounts(base_amounts),
            target_type=FeeTargetType.ENTITY,
            target_entity_id=f0_entity.id,
            selected_at=invoice.created_at,
            selection_deadline_at=self._selection_deadline(invoice),
        )
        self.db.add(base_allocation)
        self.db.flush()
        return self._allocations_for_invoice(invoice.id)

    def _settlement_component_rows(
        self,
        *,
        invoice: Invoice,
        allocations: list[FeeAllocation],
        currency: str,
    ) -> list[tuple[FeeAllocation, Decimal, int]]:
        required_total = self._required_invoice_amount(invoice, currency)
        if required_total <= Decimal("0.00"):
            raise FeeAllocationTargetInvalid("currency")
        required_total += self.requested_extra_amount(invoice.id, currency)

        rows: list[tuple[FeeAllocation, Decimal, int]] = []
        settlement_total = Decimal("0.00")
        for allocation in allocations:
            if (
                allocation.component_key == "directed"
                and allocation.selected_at is None
            ):
                raise FeeAllocationTargetInvalid("directed")
            amount = self._settlement_amount(allocation, currency)
            if amount is None:
                raise FeeAllocationTargetInvalid("currency")
            if amount <= Decimal("0.00"):
                continue
            target_entity_id = self._resolve_allocation_target_entity_id(allocation)
            if target_entity_id is None:
                raise FeeAllocationTargetInvalid("target")
            rows.append((allocation, amount, target_entity_id))
            settlement_total += amount

        if settlement_total.quantize(Decimal("0.01")) != required_total.quantize(
            Decimal("0.01")
        ):
            raise FeeAllocationTargetInvalid("amounts")
        return rows

    def _settlement_amount(
        self, allocation: FeeAllocation, currency: str
    ) -> Decimal | None:
        raw_amount = (allocation.amounts or {}).get(currency.lower())
        if raw_amount is None:
            return None
        amount = Decimal(str(raw_amount)).quantize(Decimal("0.01"))
        if allocation.component_key == "directed":
            amount += self.requested_extra_amount(allocation.invoice_id, currency)
        return amount

    def _allocation_transaction(self, allocation: FeeAllocation) -> Transaction | None:
        if allocation.allocation_transaction_id is None:
            return None
        return (
            self.db.query(Transaction)
            .filter(Transaction.id == allocation.allocation_transaction_id)
            .first()
        )

    def _resolve_allocation_target_entity_id(
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
            return split.recipient_entity_id if split else None
        return None

    def _format_amounts(self, amounts: dict[str, str] | dict[str, Decimal]) -> str:
        return " / ".join(
            f"{Decimal(str(amount)):,.2f} {currency.upper()}"
            for currency, amount in sorted(amounts.items())
        )

    def _selection_url(self, invoice_id: int) -> str:
        path = f"/fee/invoices/{invoice_id}/selection"
        if not self.config.ui_url:
            return path
        return f"{self.config.ui_url.rstrip('/')}{path}"

    def _notify_fee_invoice(
        self,
        invoice: Invoice,
        entity: Entity,
        allocation: FeeAllocation,
    ) -> bool:
        deadline = allocation.selection_deadline_at.strftime("%Y-%m-%d")
        selection_url = self._selection_url(invoice.id)
        message = (
            f"Monthly fee invoice #{invoice.id} is ready.\n"
            f"Total to pay: <b>{self._format_amounts({item['currency']: item['amount'] for item in invoice.amounts})}</b>.\n"
            f"<b>{self._format_amounts(allocation.amounts)}</b> of it goes to a space budget you choose.\n"
            f"Pick a target by <b>{deadline}</b>; otherwise Refinance will choose one automatically.\n"
            "If the increased fee is difficult right now, contact the finance person privately."
        )
        reply_markup = json.dumps(
            {
                "inline_keyboard": [
                    [{"text": "Choose contribution target", "url": selection_url}]
                ]
            }
        )
        results = self._notification_service.send(
            entity,
            message,
            telegram_reply_markup=reply_markup,
        )
        return any(results.values())

    def _notify_legacy_invoice(self, invoice: Invoice, entity: Entity) -> bool:
        message = (
            f"Monthly fee invoice #{invoice.id} uses your legacy amount: "
            f"<b>{self._format_amounts({item['currency']: item['amount'] for item in invoice.amounts})}</b>.\n"
            "No monthly contribution target selection is required."
        )
        results = self._notification_service.send(entity, message)
        return any(results.values())

    def _notify_auto_selection(
        self, invoice: Invoice, allocation: FeeAllocation
    ) -> None:
        entity = (
            self.db.query(Entity).filter(Entity.id == invoice.from_entity_id).first()
        )
        if entity is None:
            return
        target_name = self._target_name(allocation) or "selected target"
        message = (
            f"Monthly fee invoice #{invoice.id}: no target was selected within 30 days.\n"
            f"Refinance selected <b>{target_name}</b> automatically."
        )
        self._notification_service.send(entity, message)

    def get_policy(
        self, entity_id: int, actor_entity: Entity
    ) -> FeePolicyOverrideSchema | None:
        self._assert_finance_actor(actor_entity)
        policy = (
            self.db.query(FeePolicyOverride)
            .filter(FeePolicyOverride.entity_id == entity_id)
            .first()
        )
        return FeePolicyOverrideSchema.model_validate(policy) if policy else None

    def upsert_policy(
        self,
        entity_id: int,
        schema: FeePolicyOverrideUpdateSchema,
        actor_entity: Entity,
    ) -> FeePolicyOverrideSchema:
        self._assert_finance_actor(actor_entity)
        policy = (
            self.db.query(FeePolicyOverride)
            .filter(FeePolicyOverride.entity_id == entity_id)
            .first()
        )
        if policy is None:
            policy = FeePolicyOverride(
                entity_id=entity_id,
                kind=schema.kind,
                active=schema.active,
            )
            self.db.add(policy)
        else:
            policy.kind = schema.kind
            policy.active = schema.active
            policy.modified_at = datetime.datetime.now()
        self.db.flush()
        self.db.refresh(policy)
        return FeePolicyOverrideSchema.model_validate(policy)

    def delete_policy(self, entity_id: int, actor_entity: Entity) -> int:
        self._assert_finance_actor(actor_entity)
        policy = (
            self.db.query(FeePolicyOverride)
            .filter(FeePolicyOverride.entity_id == entity_id)
            .first()
        )
        if policy is None:
            return entity_id
        policy.active = False
        policy.modified_at = datetime.datetime.now()
        self.db.flush()
        return entity_id
