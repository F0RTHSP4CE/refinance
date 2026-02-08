"""Fee service"""

import calendar
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from app.config import Config, get_config
from app.dependencies.services import (
    get_currency_exchange_service,
    get_entity_service,
    get_invoice_service,
)
from app.models.entity import Entity
from app.models.invoice import Invoice, InvoiceStatus
from app.models.tag import Tag
from app.models.transaction import TransactionStatus
from app.schemas.base import CurrencyDecimal
from app.schemas.entity import EntitySchema
from app.schemas.fee import (
    FeeAmountSchema,
    FeeFiltersSchema,
    FeeInvoiceIssueReportSchema,
    FeeSchema,
    MonthlyFeeSchema,
)
from app.schemas.invoice import InvoiceCreateSchema
from app.seeding import f0_entity, fee_tag, member_tag, resident_tag
from app.services.base import BaseService
from app.services.currency_exchange import CurrencyExchangeService
from app.services.entity import EntityService
from app.services.invoice import InvoiceService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload


@dataclass(slots=True)
class MonthlyFee:
    year: int
    month: int
    amounts: dict[str, Decimal]
    total_usd: float
    unpaid_invoice_id: int | None = None
    paid_invoice_id: int | None = None
    unpaid_invoice_amounts: dict[str, Decimal] | None = None

    def to_schema(self) -> MonthlyFeeSchema:
        return MonthlyFeeSchema(
            year=self.year,
            month=self.month,
            amounts={
                currency: CurrencyDecimal(amount)
                for currency, amount in self.amounts.items()
            },
            total_usd=self.total_usd,
            unpaid_invoice_id=self.unpaid_invoice_id,
            paid_invoice_id=self.paid_invoice_id,
            unpaid_invoice_amounts=(
                {
                    currency: CurrencyDecimal(amount)
                    for currency, amount in (self.unpaid_invoice_amounts or {}).items()
                }
                if self.unpaid_invoice_amounts
                else None
            ),
        )


@dataclass(slots=True)
class FeeRecord:
    entity: Entity
    fees: list[MonthlyFee]

    def to_schema(self) -> FeeSchema:
        return FeeSchema(
            entity=EntitySchema.model_validate(self.entity),
            fees=[fee.to_schema() for fee in self.fees],
        )


class FeeService(BaseService):
    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(get_entity_service),
        currency_exchange_service: CurrencyExchangeService = Depends(
            get_currency_exchange_service
        ),
        invoice_service: InvoiceService = Depends(get_invoice_service),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self._entity_service = entity_service
        self._currency_exchange_service = currency_exchange_service
        self._invoice_service = invoice_service
        self._config = config

    def _parse_comment_for_date(self, comment: str | None) -> tuple[int, int] | None:
        if not comment:
            return None

        # regex to find YYYY-MM or MM-YYYY
        match = re.search(r"(\d{4})-(\d{1,2})|(\d{1,2})-(\d{4})", comment)
        if match:
            if match.group(1):
                return int(match.group(1)), int(match.group(2))
            else:
                return int(match.group(4)), int(match.group(3))

        # regex to find month name and year
        # build mapping of full month names and abbreviations
        month_names = {
            name.lower(): idx for idx, name in enumerate(calendar.month_name) if name
        }
        month_names.update(
            {abbr.lower(): idx for idx, abbr in enumerate(calendar.month_abbr) if abbr}
        )
        # sort keys to match longer names first (e.g. 'march' before 'mar')
        month_pattern = "|".join(sorted(month_names.keys(), key=len, reverse=True))
        match = re.search(rf"({month_pattern})\s+(\d{{4}})", comment, re.IGNORECASE)
        if match:
            month_key = match.group(1).lower()
            year = int(match.group(2))
            return year, month_names[month_key]

        return None

    def _amount_to_usd(self, currency: str, amount: Decimal) -> Decimal:
        if amount is None:
            return Decimal("0")
        if currency.lower() == "usd":
            return amount

        try:
            _, usd_amount, _ = self._currency_exchange_service.calculate_conversion(
                source_amount=amount,
                target_amount=None,
                source_currency=currency,
                target_currency="usd",
            )
            return usd_amount
        except Exception:
            return Decimal("0")

    def _sum_amounts_usd(self, amounts: Mapping[str, Decimal]) -> float:
        total = Decimal("0")
        for currency, raw_amount in amounts.items():
            if raw_amount in (None, ""):
                continue
            try:
                amount = (
                    raw_amount
                    if isinstance(raw_amount, Decimal)
                    else Decimal(str(raw_amount))
                )
            except Exception:
                continue
            total += self._amount_to_usd(currency, amount)
        return float(total)

    def _normalize_amounts(
        self, raw_amounts: Mapping[str, Any] | None
    ) -> dict[str, Decimal]:
        normalized: dict[str, Decimal] = {}
        if not raw_amounts:
            return normalized
        for currency, raw_value in raw_amounts.items():
            if raw_value in (None, ""):
                continue
            try:
                amount = (
                    raw_value
                    if isinstance(raw_value, Decimal)
                    else Decimal(str(raw_value))
                )
            except Exception:
                continue
            normalized[currency.lower()] = amount
        return normalized

    def _amounts_list_to_map(
        self, items: list[Mapping[str, Any]] | None
    ) -> dict[str, Decimal]:
        if not items:
            return {}
        normalized: dict[str, Decimal] = {}
        for item in items:
            currency = str(item.get("currency", "")).lower().strip()
            if not currency:
                continue
            raw_value = item.get("amount")
            if raw_value in (None, ""):
                continue
            try:
                amount = (
                    raw_value
                    if isinstance(raw_value, Decimal)
                    else Decimal(str(raw_value))
                )
            except Exception:
                continue
            normalized[currency] = amount
        return normalized

    def _build_monthly_fee(
        self,
        year: int,
        month: int,
        raw_amounts: Mapping[str, Any] | None,
        unpaid_invoice_id: int | None,
        paid_invoice_id: int | None,
        unpaid_invoice_amounts: Mapping[str, Any] | None,
    ) -> MonthlyFee:
        amounts = self._normalize_amounts(raw_amounts)
        unpaid_amounts = self._normalize_amounts(unpaid_invoice_amounts)
        total_usd = self._sum_amounts_usd(amounts)
        return MonthlyFee(
            year=year,
            month=month,
            amounts=amounts,
            total_usd=total_usd,
            unpaid_invoice_id=unpaid_invoice_id,
            paid_invoice_id=paid_invoice_id,
            unpaid_invoice_amounts=unpaid_amounts,
        )

    def get_fees(self, filters: FeeFiltersSchema) -> list[FeeSchema]:
        hackerspace = self._entity_service.get(f0_entity.id)
        residents = (
            self.db.query(Entity)
            .filter(
                or_(
                    Entity.tags.contains(resident_tag),
                    Entity.tags.contains(member_tag),
                )
            )
            .order_by(Entity.active.desc(), Entity.name)
            .all()
        )

        # Base window: last N months up to today
        today = date.today()
        today_year, today_month = today.year, today.month
        today_idx = today_year * 12 + today_month
        # limit future extension to 12 months ahead of today
        max_future_idx = today_idx + 12
        # number of past months to include
        months = min(filters.months, 12)

        def subtract_months(base: date, months_back: int) -> date:
            year = base.year
            month = base.month - months_back
            while month <= 0:
                month += 12
                year -= 1
            return date(year, month, 1)

        def add_months(base: date, months_forward: int) -> date:
            year = base.year
            month = base.month + months_forward
            while month > 12:
                month -= 12
                year += 1
            return date(year, month, 1)

        resident_ids = [r.id for r in residents]
        start_period = subtract_months(date(today_year, today_month, 1), months - 1)
        max_future_period = add_months(date(today_year, today_month, 1), 12)

        invoices = (
            self.db.query(Invoice)
            .options(selectinload(Invoice.transaction))
            .filter(
                Invoice.to_entity_id == hackerspace.id,
                Invoice.billing_period.isnot(None),
                Invoice.billing_period >= start_period,
                Invoice.billing_period <= max_future_period,
                Invoice.tags.contains(fee_tag),
                Invoice.from_entity_id.in_(resident_ids),
            )
            .all()
        )

        # Process transactions into a nested dictionary
        # {resident_id: {(year, month): {currency: amount}}}
        fees_by_resident_by_month = defaultdict(
            lambda: defaultdict(lambda: defaultdict(Decimal))
        )
        # Track unpaid invoices
        # {resident_id: {(year, month): invoice_id}}
        unpaid_invoice_by_resident_by_month: dict[int, dict[tuple[int, int], int]] = (
            defaultdict(dict)
        )
        unpaid_amounts_by_resident_by_month: dict[
            int, dict[tuple[int, int], dict[str, Decimal]]
        ] = defaultdict(dict)
        # Track paid invoices
        # {resident_id: {(year, month): invoice_id}}
        paid_invoice_by_resident_by_month: dict[int, dict[tuple[int, int], int]] = (
            defaultdict(dict)
        )
        for invoice in invoices:
            if invoice.billing_period is None:
                continue
            year = invoice.billing_period.year
            month = invoice.billing_period.month
            if invoice.status == InvoiceStatus.PENDING:
                current = unpaid_invoice_by_resident_by_month[
                    invoice.from_entity_id
                ].get((year, month))
                if current is None or invoice.id > current:
                    unpaid_invoice_by_resident_by_month[invoice.from_entity_id][
                        (year, month)
                    ] = invoice.id
                    unpaid_amounts_by_resident_by_month[invoice.from_entity_id][
                        (year, month)
                    ] = self._amounts_list_to_map(invoice.amounts or [])
                continue
            if invoice.status != InvoiceStatus.PAID:
                continue
            tx = invoice.transaction
            if tx is None or tx.status != TransactionStatus.COMPLETED:
                continue
            current_paid = paid_invoice_by_resident_by_month[
                invoice.from_entity_id
            ].get((year, month))
            if current_paid is None or invoice.id > current_paid:
                paid_invoice_by_resident_by_month[invoice.from_entity_id][
                    (year, month)
                ] = invoice.id
            fees_by_resident_by_month[invoice.from_entity_id][(year, month)][
                tx.currency.lower()
            ] += tx.amount

        # Build the final response structure
        results: list[FeeRecord] = []
        for r in residents:
            # Past months window
            monthly_fees: list[MonthlyFee] = []
            for i in range(months):
                year = today_year
                month = today_month - i
                while month <= 0:
                    month += 12
                    year -= 1
                monthly_fees.append(
                    self._build_monthly_fee(
                        year,
                        month,
                        fees_by_resident_by_month[r.id].get((year, month), {}),
                        unpaid_invoice_by_resident_by_month[r.id].get((year, month)),
                        paid_invoice_by_resident_by_month[r.id].get((year, month)),
                        unpaid_amounts_by_resident_by_month[r.id].get(
                            (year, month), {}
                        ),
                    )
                )

            # Trim trailing empty months (which correspond to the earliest months in the window)
            # Keep at least the current month so UI has an anchor row.
            while len(monthly_fees) > 1:
                last = monthly_fees[-1]
                has_unpaid = last.unpaid_invoice_id is not None or bool(
                    last.unpaid_invoice_amounts
                )
                has_paid = last.paid_invoice_id is not None
                if last.amounts in ({}, None) and not has_unpaid and not has_paid:
                    monthly_fees.pop()
                    continue
                break
            # Future months with payments (up to 12 months ahead)
            future_fees: list[MonthlyFee] = []
            for (y, m), currs in fees_by_resident_by_month[r.id].items():
                idx = y * 12 + m
                if idx > today_idx and idx <= max_future_idx:
                    future_fees.append(
                        self._build_monthly_fee(
                            y,
                            m,
                            currs,
                            unpaid_invoice_by_resident_by_month[r.id].get((y, m)),
                            paid_invoice_by_resident_by_month[r.id].get((y, m)),
                            unpaid_amounts_by_resident_by_month[r.id].get((y, m), {}),
                        )
                    )
            for (y, m), invoice_id in unpaid_invoice_by_resident_by_month[r.id].items():
                idx = y * 12 + m
                if idx <= today_idx or idx > max_future_idx:
                    continue
                if any(fee.year == y and fee.month == m for fee in future_fees):
                    continue
                future_fees.append(
                    self._build_monthly_fee(
                        y,
                        m,
                        {},
                        invoice_id,
                        paid_invoice_by_resident_by_month[r.id].get((y, m)),
                        unpaid_amounts_by_resident_by_month[r.id].get((y, m), {}),
                    )
                )
            # Combine and sort chronologically
            all_fees = monthly_fees + future_fees
            all_fees.sort(key=lambda x: (x.year, x.month))

            results.append(FeeRecord(entity=r, fees=all_fees))

        return [record.to_schema() for record in results]

    def get_fee_amounts(self) -> list[FeeAmountSchema]:
        items: list[FeeAmountSchema] = []
        for item in self._config.fee_presets:
            try:
                tag_id = int(item.get("tag_id"))
                currency = str(item.get("currency", "")).lower().strip()
                amount = Decimal(str(item.get("amount"))).quantize(Decimal("0.01"))
            except Exception:
                continue
            if not currency:
                continue
            items.append(
                FeeAmountSchema(
                    tag_id=tag_id,
                    currency=currency,
                    amount=amount,
                )
            )
        return items

    @staticmethod
    def _normalize_billing_period(
        value: date | None,
    ) -> date | None:
        if value is None:
            return None
        return date(value.year, value.month, 1)

    @staticmethod
    def _select_fee_tag_id(
        entity_tag_ids: set[int],
        fee_amounts_by_tag: dict[int, list[dict[str, Decimal]]],
    ) -> int | None:
        priority = [resident_tag.id, member_tag.id]
        for tag_id in priority:
            if tag_id in entity_tag_ids and tag_id in fee_amounts_by_tag:
                return tag_id
        for tag_id in sorted(fee_amounts_by_tag.keys()):
            if tag_id in entity_tag_ids:
                return tag_id
        return None

    def _load_fee_amounts_by_tag(self) -> dict[int, list[dict[str, Decimal]]]:
        fee_amounts_by_tag: dict[int, list[dict[str, Decimal]]] = defaultdict(list)
        for item in self._config.fee_presets:
            try:
                tag_id = int(item.get("tag_id"))
                currency = str(item.get("currency", "")).lower().strip()
                amount = Decimal(str(item.get("amount"))).quantize(Decimal("0.01"))
            except Exception:
                continue
            if not currency:
                continue
            fee_amounts_by_tag[tag_id].append({"currency": currency, "amount": amount})
        return fee_amounts_by_tag

    def issue_fee_invoices(
        self,
        *,
        billing_period: date | None = None,
        actor_entity_id: int | None = None,
    ) -> FeeInvoiceIssueReportSchema:
        period = self._normalize_billing_period(billing_period or date.today())
        if period is None:
            period = date.today().replace(day=1)
        hackerspace = self.db.query(Entity).filter(Entity.id == f0_entity.id).first()
        if hackerspace is None:
            hackerspace = f0_entity

        resolved_actor_id = actor_entity_id or hackerspace.id

        fee_amounts_by_tag = self._load_fee_amounts_by_tag()
        if not fee_amounts_by_tag:
            return FeeInvoiceIssueReportSchema(
                billing_period=period,
                created_count=0,
                skipped_count=0,
                invoice_ids=[],
            )

        fee_tag_ids = sorted(fee_amounts_by_tag.keys())
        tags = self.db.query(Tag).filter(Tag.id.in_(fee_tag_ids)).all()
        tag_filters = [Entity.tags.contains(tag) for tag in tags]
        if not tag_filters:
            return FeeInvoiceIssueReportSchema(
                billing_period=period,
                created_count=0,
                skipped_count=0,
                invoice_ids=[],
            )

        targets = self.db.query(Entity).filter(or_(*tag_filters)).all()

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

            entity_tag_ids = {tag.id for tag in (resident.tags or [])}
            fee_tag_id = self._select_fee_tag_id(entity_tag_ids, fee_amounts_by_tag)
            if fee_tag_id is None:
                skipped_count += 1
                continue

            fee_amounts = sorted(
                fee_amounts_by_tag[fee_tag_id], key=lambda item: item["currency"]
            )
            amounts = [
                {"currency": item["currency"], "amount": item["amount"]}
                for item in fee_amounts
            ]
            if not amounts:
                skipped_count += 1
                continue

            invoice = self._invoice_service.create(
                InvoiceCreateSchema(
                    from_entity_id=resident.id,
                    to_entity_id=hackerspace.id,
                    amounts=amounts,
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
