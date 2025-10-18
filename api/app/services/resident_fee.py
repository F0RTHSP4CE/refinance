"""ResidentFee service"""

import calendar
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from app.models.entity import Entity
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.base import CurrencyDecimal
from app.schemas.entity import EntitySchema
from app.schemas.resident_fee import (
    MonthlyFeeSchema,
    ResidentFeeFiltersSchema,
    ResidentFeeSchema,
)
from app.seeding import ex_resident_tag, f0_entity, fee_tag, member_tag, resident_tag
from app.services.base import BaseService
from app.services.currency_exchange import CurrencyExchangeService
from app.services.entity import EntityService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session


@dataclass(slots=True)
class MonthlyFee:
    year: int
    month: int
    amounts: dict[str, Decimal]
    total_usd: float

    def to_schema(self) -> MonthlyFeeSchema:
        return MonthlyFeeSchema(
            year=self.year,
            month=self.month,
            amounts={
                currency: CurrencyDecimal(amount)
                for currency, amount in self.amounts.items()
            },
            total_usd=self.total_usd,
        )


@dataclass(slots=True)
class ResidentFeeRecord:
    entity: Entity
    fees: list[MonthlyFee]

    def to_schema(self) -> ResidentFeeSchema:
        return ResidentFeeSchema(
            entity=EntitySchema.model_validate(self.entity),
            fees=[fee.to_schema() for fee in self.fees],
        )


class ResidentFeeService(BaseService):
    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(),
        currency_exchange_service: CurrencyExchangeService = Depends(),
    ):
        self.db = db
        self._entity_service = entity_service
        self._currency_exchange_service = currency_exchange_service

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

    def _build_monthly_fee(
        self, year: int, month: int, raw_amounts: Mapping[str, Any] | None
    ) -> MonthlyFee:
        amounts = self._normalize_amounts(raw_amounts)
        total_usd = self._sum_amounts_usd(amounts)
        return MonthlyFee(
            year=year,
            month=month,
            amounts=amounts,
            total_usd=total_usd,
        )

    def get_fees(self, filters: ResidentFeeFiltersSchema) -> list[ResidentFeeSchema]:
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

        # Get all relevant transactions in one go
        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.to_entity_id == hackerspace.id,
                Transaction.tags.contains(fee_tag),
                # Transaction.status == TransactionStatus.COMPLETED,
                # We get all transactions and then filter by date in python
                # because comment can override the date
            )
            .all()
        )

        # Process transactions into a nested dictionary
        # {resident_id: {(year, month): {currency: amount}}}
        fees_by_resident_by_month = defaultdict(
            lambda: defaultdict(lambda: defaultdict(Decimal))
        )
        for t in transactions:
            parsed_date = self._parse_comment_for_date(t.comment)
            if parsed_date:
                year, month = parsed_date
            else:
                year, month = t.created_at.year, t.created_at.month
            idx = year * 12 + month
            # accumulate all future transactions up to allowed window
            # future months handled later per resident

            fees_by_resident_by_month[t.from_entity_id][(year, month)][
                t.currency
            ] += t.amount

        # Build the final response structure
        results: list[ResidentFeeRecord] = []
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
                    )
                )

            # Trim trailing empty months (which correspond to the earliest months in the window)
            # Keep at least the current month so UI has an anchor row.
            while len(monthly_fees) > 1 and monthly_fees[-1].amounts in ({}, None):
                monthly_fees.pop()
            # Future months with payments (up to 12 months ahead)
            future_fees: list[MonthlyFee] = []
            for (y, m), currs in fees_by_resident_by_month[r.id].items():
                idx = y * 12 + m
                if idx > today_idx and idx <= max_future_idx:
                    future_fees.append(self._build_monthly_fee(y, m, currs))
            # Combine and sort chronologically
            all_fees = monthly_fees + future_fees
            all_fees.sort(key=lambda x: (x.year, x.month))

            results.append(ResidentFeeRecord(entity=r, fees=all_fees))

        return [record.to_schema() for record in results]
