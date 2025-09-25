"""Stats service"""

import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Mapping

from app.models.entity import Entity
from app.models.tag import Tag
from app.models.transaction import Transaction
from app.seeding import f0_entity, resident_tag
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.services.currency_exchange import CurrencyExchangeService
from app.services.entity import EntityService
from app.services.resident_fee import ResidentFeeService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import Session, selectinload


class StatsService(BaseService):
    def __init__(
        self,
        db: Session = Depends(get_uow),
        resident_fee_service: ResidentFeeService = Depends(),
        balance_service: BalanceService = Depends(),
        entity_service: EntityService = Depends(),
        currency_exchange_service: CurrencyExchangeService = Depends(),
    ):
        self.db = db
        self._resident_fee_service = resident_fee_service
        self._balance_service = balance_service
        self._entity_service = entity_service
        self._currency_exchange_service = currency_exchange_service

    # --- internal helpers -------------------------------------------------
    def _amount_to_usd(self, currency: str, amount: Decimal) -> Decimal:
        """Convert an amount in any supported currency to USD using the latest rates.

        The CurrencyExchangeService uses GEL as base; we leverage its `calculate_conversion`.
        """
        if amount is None:
            return Decimal("0")
        if currency.lower() == "usd":
            return amount
        # Use calculate_conversion to convert source currency -> usd.
        # (source_amount, target_amount, rate) returned; target_amount is the USD value.
        try:
            _, usd_amount, _ = self._currency_exchange_service.calculate_conversion(
                source_amount=amount,
                target_amount=None,
                source_currency=currency,
                target_currency="usd",
            )
            return usd_amount
        except Exception:
            # Fail safe: ignore unknown currency.
            return Decimal("0")

    def _sum_amounts_usd(self, amounts: Mapping[str, Any]) -> float:
        total = Decimal("0")
        for cur, amt in amounts.items():
            if amt in (None, ""):
                continue
            try:
                if not isinstance(amt, Decimal):
                    amt = Decimal(str(amt))
                total += self._amount_to_usd(cur, amt)
            except Exception:
                continue
        return float(total)

    def get_resident_fee_sum_by_month(
        self, timeframe_from: date | None = None, timeframe_to: date | None = None
    ):
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)
        hackerspace = self._entity_service.get(f0_entity.id)
        residents = (
            self.db.query(Entity)
            .filter(
                Entity.tags.contains(resident_tag),
            )
            .all()
        )

        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.from_entity_id.in_([r.id for r in residents]),
                Transaction.to_entity_id == hackerspace.id,
            )
            .all()
        )

        monthly_totals = defaultdict(lambda: defaultdict(Decimal))
        today = date.today()

        for t in transactions:
            parsed_date = self._resident_fee_service._parse_comment_for_date(t.comment)
            if parsed_date:
                year, month = parsed_date
            else:
                year, month = t.created_at.year, t.created_at.month

            # Skip future months
            if year > today.year or (year == today.year and month > today.month):
                continue

            # Check if the month is within the requested timeframe
            fee_date = date(year, month, 1)
            start_month = timeframe_from.replace(day=1)
            end_month = timeframe_to.replace(day=1)

            if not (start_month <= fee_date <= end_month):
                continue

            monthly_totals[(year, month)][t.currency] += t.amount

        result = []
        for (year, month), amounts in sorted(monthly_totals.items()):
            amounts_float = {k: float(v) for k, v in amounts.items()}
            total_usd = self._sum_amounts_usd(amounts)
            result.append(
                {
                    "year": year,
                    "month": month,
                    "amounts": amounts_float,
                    "total_usd": total_usd,
                }
            )
        return result

    def get_entity_transactions_by_day(
        self,
        entity_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ):
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)
        return (
            self.db.query(
                func.date(Transaction.created_at).label("day"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .filter(
                and_(
                    Transaction.created_at >= timeframe_from,
                    Transaction.created_at <= timeframe_to,
                    (Transaction.from_entity_id == entity_id)
                    | (Transaction.to_entity_id == entity_id),
                )
            )
            .group_by("day")
            .order_by("day")
            .all()
        )

    def get_transactions_sum_by_week(
        self, timeframe_from: date | None = None, timeframe_to: date | None = None
    ):
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)

        query_result = (
            self.db.query(
                extract("year", Transaction.created_at).label("year"),
                extract("week", Transaction.created_at).label("week"),
                Transaction.currency,
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                and_(
                    Transaction.created_at >= timeframe_from,
                    Transaction.created_at <= timeframe_to,
                )
            )
            .group_by("year", "week", "currency")
            .order_by("year", "week")
            .all()
        )

        weekly_totals = defaultdict(lambda: defaultdict(Decimal))
        for row in query_result:
            weekly_totals[(row.year, row.week)][row.currency] = row.total_amount

        result = []
        for (year, week), amounts in sorted(weekly_totals.items()):
            amounts_float = {k: float(v) for k, v in amounts.items()}
            total_usd = self._sum_amounts_usd(amounts)
            result.append(
                {
                    "year": year,
                    "week": week,
                    "amounts": amounts_float,
                    "total_usd": total_usd,
                }
            )
        return result

    def get_entity_balance_history(
        self,
        entity_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ):
        timeframe_to = timeframe_to or date.today()
        three_months_ago = self._subtract_months(timeframe_to, 3)

        if timeframe_from is None or timeframe_from < three_months_ago:
            timeframe_from = three_months_ago

        if timeframe_from > timeframe_to:
            timeframe_from = timeframe_to

        result = []
        current_day = timeframe_from
        last_completed_balances: dict[str, Decimal] | None = None

        while current_day <= timeframe_to:
            balances = self._balance_service.get_balances(
                entity_id, end_date=current_day
            )
            completed_balances = self._normalize_currency_mapping(balances.completed)
            if (
                last_completed_balances is not None
                and completed_balances == last_completed_balances
            ):
                current_day += timedelta(days=1)
                continue

            last_completed_balances = completed_balances.copy()

            balances_float = {
                currency: float(amount)
                for currency, amount in completed_balances.items()
            }
            total_usd = self._sum_amounts_usd(completed_balances)
            result.append(
                {
                    "day": current_day,
                    "balance_changes": balances_float,
                    "total_usd": total_usd,
                }
            )
            current_day += timedelta(days=1)

        return result

    def _subtract_months(self, dt: date, months: int) -> date:
        year = dt.year
        month = dt.month - months
        while month <= 0:
            month += 12
            year -= 1
        last_day = calendar.monthrange(year, month)[1]
        day = min(dt.day, last_day)
        return date(year, month, day)

    def _normalize_currency_mapping(
        self, values: Mapping[str, Any]
    ) -> dict[str, Decimal]:
        normalized: dict[str, Decimal] = {}
        for currency, amount in values.items():
            if isinstance(amount, Decimal):
                normalized[currency] = amount
            elif hasattr(amount, "to_decimal"):
                normalized[currency] = amount.to_decimal()  # type: ignore[attr-defined]
            else:
                try:
                    normalized[currency] = Decimal(str(amount))
                except Exception:
                    normalized[currency] = Decimal("0")
        return normalized

    def _calculate_timeframe_bounds(
        self, months: int, timeframe_to: date | None
    ) -> tuple[datetime, datetime]:
        """Return datetime bounds spanning the last ``months`` months up to ``timeframe_to``."""

        timeframe_to = timeframe_to or date.today()
        months = max(1, months)
        start_month = timeframe_to.replace(day=1)
        if months > 1:
            start_month = self._subtract_months(start_month, months - 1)

        start_dt = datetime.combine(start_month, time.min)
        end_dt = datetime.combine(timeframe_to, time.max)
        return start_dt, end_dt

    def _get_top_entities(
        self,
        entity_column,
        limit: int,
        months: int,
        timeframe_to: date | None,
        *additional_filters,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        start_dt, end_dt = self._calculate_timeframe_bounds(months, timeframe_to)

        labeled_entity_col = entity_column.label("entity_id")
        rows = (
            self.db.query(
                labeled_entity_col,
                Transaction.currency,
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                Transaction.created_at >= start_dt,
                Transaction.created_at <= end_dt,
                *additional_filters,
            )
            .group_by(labeled_entity_col, Transaction.currency)
            .all()
        )

        if not rows:
            return []

        totals: dict[int, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        for row in rows:
            totals[int(row.entity_id)][row.currency] += row.total_amount

        entity_ids = list(totals.keys())
        entity_names = {}
        if entity_ids:
            for entity_id, name in (
                self.db.query(Entity.id, Entity.name)
                .filter(Entity.id.in_(entity_ids))
                .all()
            ):
                entity_names[int(entity_id)] = name

        results = []
        for entity_id, amounts in totals.items():
            amounts_float = {
                currency: float(amount) for currency, amount in amounts.items()
            }
            total_usd = self._sum_amounts_usd(amounts)
            results.append(
                {
                    "entity_id": entity_id,
                    "entity_name": entity_names.get(entity_id, "Unknown"),
                    "amounts": amounts_float,
                    "total_usd": total_usd,
                }
            )

        results.sort(key=lambda item: item["total_usd"], reverse=True)
        return results[:limit]

    def _get_top_tags(
        self,
        limit: int,
        months: int,
        timeframe_to: date | None,
        entity_filter,
        fallback_entity_attr: str,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        start_dt, end_dt = self._calculate_timeframe_bounds(months, timeframe_to)

        transactions = (
            self.db.query(Transaction)
            .options(
                selectinload(Transaction.tags),
                selectinload(Transaction.from_entity).selectinload(Entity.tags),
                selectinload(Transaction.to_entity).selectinload(Entity.tags),
            )
            .filter(
                Transaction.created_at >= start_dt,
                Transaction.created_at <= end_dt,
                entity_filter,
            )
            .all()
        )

        if not transactions:
            return []

        totals: dict[int, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        tag_names: dict[int, str] = {}

        for tx in transactions:
            tags = tx.tags if tx.tags else []
            if not tags:
                fallback_entity = getattr(tx, fallback_entity_attr, None)
                if fallback_entity:
                    tags = fallback_entity.tags

            if not tags:
                continue

            unique_tags: dict[int, Tag] = {}
            for tag in tags:
                if tag and tag.id is not None:
                    unique_tags[int(tag.id)] = tag

            if not unique_tags:
                continue

            for tag_id, tag in unique_tags.items():
                totals[tag_id][tx.currency] += tx.amount
                tag_names[tag_id] = tag.name

        if not totals:
            return []

        results = []
        for tag_id, amounts in totals.items():
            amounts_float = {
                currency: float(amount) for currency, amount in amounts.items()
            }
            total_usd = self._sum_amounts_usd(amounts)
            results.append(
                {
                    "tag_id": tag_id,
                    "tag_name": tag_names.get(tag_id, "Unknown"),
                    "amounts": amounts_float,
                    "total_usd": total_usd,
                }
            )

        results.sort(key=lambda item: item["total_usd"], reverse=True)
        return results[:limit]

    def get_top_incoming_entities(
        self,
        limit: int = 5,
        months: int = 3,
        timeframe_to: date | None = None,
        entity_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top entities receiving funds within the timeframe."""

        entity_id = entity_id or f0_entity.id
        return self._get_top_entities(
            Transaction.from_entity_id,
            limit,
            months,
            timeframe_to,
            Transaction.to_entity_id == entity_id,
        )

    def get_top_outgoing_entities(
        self,
        limit: int = 5,
        months: int = 3,
        timeframe_to: date | None = None,
        entity_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top entities sending funds within the timeframe."""

        entity_id = entity_id or f0_entity.id
        return self._get_top_entities(
            Transaction.to_entity_id,
            limit,
            months,
            timeframe_to,
            Transaction.from_entity_id == entity_id,
        )

    def get_top_incoming_tags(
        self,
        limit: int = 5,
        months: int = 3,
        timeframe_to: date | None = None,
        entity_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top tags for incoming transactions within the timeframe."""

        entity_id = entity_id or f0_entity.id
        return self._get_top_tags(
            limit,
            months,
            timeframe_to,
            Transaction.to_entity_id == entity_id,
            "from_entity",
        )

    def get_top_outgoing_tags(
        self,
        limit: int = 5,
        months: int = 3,
        timeframe_to: date | None = None,
        entity_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top tags for outgoing transactions within the timeframe."""

        entity_id = entity_id or f0_entity.id
        return self._get_top_tags(
            limit,
            months,
            timeframe_to,
            Transaction.from_entity_id == entity_id,
            "to_entity",
        )

    def get_transactions_sum_by_tag_by_month(
        self,
        tag_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ):
        """
        1. Find all transactions with the given tag either on the transaction or on its from/to entities,
        2. Sum their amounts by month and currency,
        3. Return one entry per month in the timeframe (default last 12 months), even if zero.
        """
        # establish timeframe: default to last 12 months including current month
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or (timeframe_to - timedelta(days=365))

        # build list of months in timeframe
        months: list[tuple[int, int]] = []
        current = timeframe_from.replace(day=1)
        end = timeframe_to.replace(day=1)
        while current <= end:
            months.append((current.year, current.month))
            # move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        # fetch all tagged transactions, then filter dates in Python to avoid datetime-vs-date issues
        transactions = (
            self.db.query(Transaction)
            .filter(
                or_(
                    Transaction.tags.any(Tag.id == tag_id),
                    Transaction.from_entity.has(Entity.tags.any(Tag.id == tag_id)),
                    Transaction.to_entity.has(Entity.tags.any(Tag.id == tag_id)),
                )
            )
            .all()
        )

        # prepare monthly buckets
        monthly_totals: dict[tuple[int, int], dict[str, Decimal]] = {
            m: defaultdict(Decimal) for m in months
        }

        # accumulate sums, filtering dates in Python to cover full days
        for t in transactions:
            t_date = t.created_at.date()
            if not (timeframe_from <= t_date <= timeframe_to):
                continue
            ym = (t_date.year, t_date.month)
            if ym in monthly_totals:
                monthly_totals[ym][t.currency] += t.amount

        # format result preserving month order
        result = []
        for y, m in months:
            amounts = monthly_totals[(y, m)]
            amounts_float = {c: float(v) for c, v in amounts.items()}
            total_usd = self._sum_amounts_usd(amounts)
            result.append(
                {
                    "year": y,
                    "month": m,
                    "amounts": amounts_float,
                    "total_usd": total_usd,
                }
            )
        return result
