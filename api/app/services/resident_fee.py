"""ResidentFee service"""

import calendar
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.models.entity import Entity
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.resident_fee import ResidentFeeFiltersSchema
from app.seeding import ex_resident_tag, f0_entity, member_tag, resident_tag
from app.services.base import BaseService
from app.services.entity import EntityService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session


class ResidentFeeService(BaseService):
    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(),
    ):
        self.db = db
        self._entity_service = entity_service

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

    def get_fees(self, filters: ResidentFeeFiltersSchema) -> list[dict]:
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
                Transaction.from_entity_id.in_([r.id for r in residents]),
                Transaction.to_entity_id == hackerspace.id,
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
        results = []
        for r in residents:
            # Past months window
            monthly_fees = []
            for i in range(months):
                year = today_year
                month = today_month - i
                while month <= 0:
                    month += 12
                    year -= 1
                amounts = fees_by_resident_by_month[r.id].get((year, month), {})
                monthly_fees.append({"year": year, "month": month, "amounts": amounts})

            # Trim trailing empty months (which correspond to the earliest months in the window)
            # Keep at least the current month so UI has an anchor row.
            while len(monthly_fees) > 1 and monthly_fees[-1]["amounts"] in ({}, None):
                monthly_fees.pop()
            # Future months with payments (up to 12 months ahead)
            future_fees = []
            for (y, m), currs in fees_by_resident_by_month[r.id].items():
                idx = y * 12 + m
                if idx > today_idx and idx <= max_future_idx:
                    future_fees.append({"year": y, "month": m, "amounts": currs})
            # Combine and sort chronologically
            all_fees = monthly_fees + future_fees
            all_fees.sort(key=lambda x: (x["year"], x["month"]))

            results.append({"entity": r, "fees": all_fees})

        return results
