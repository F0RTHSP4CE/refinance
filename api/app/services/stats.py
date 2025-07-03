"""Stats service"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.seeding import f0_entity, resident_tag
from app.models.entity import Entity
from app.models.tag import Tag
from app.models.transaction import Transaction
from app.services.base import BaseService
from app.services.entity import EntityService
from app.services.resident_fee import ResidentFeeService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import Session


class StatsService(BaseService):
    def __init__(
        self,
        db: Session = Depends(get_uow),
        resident_fee_service: ResidentFeeService = Depends(),
        entity_service: EntityService = Depends(),
    ):
        self.db = db
        self._resident_fee_service = resident_fee_service
        self._entity_service = entity_service

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

        result = [
            {
                "year": year,
                "month": month,
                "amounts": {k: float(v) for k, v in amounts.items()},
            }
            for (year, month), amounts in sorted(monthly_totals.items())
        ]

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

        result = [
            {
                "year": year,
                "week": week,
                "amounts": {k: float(v) for k, v in amounts.items()},
            }
            for (year, week), amounts in sorted(weekly_totals.items())
        ]

        return result

    def get_entity_balance_change_by_day(
        self,
        entity_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ):
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)

        incoming_q = (
            self.db.query(
                func.date(Transaction.created_at).label("day"),
                Transaction.currency,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(
                and_(
                    Transaction.created_at >= timeframe_from,
                    Transaction.created_at <= timeframe_to,
                    Transaction.to_entity_id == entity_id,
                )
            )
            .group_by("day", "currency")
            .all()
        )

        outgoing_q = (
            self.db.query(
                func.date(Transaction.created_at).label("day"),
                Transaction.currency,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(
                and_(
                    Transaction.created_at >= timeframe_from,
                    Transaction.created_at <= timeframe_to,
                    Transaction.from_entity_id == entity_id,
                )
            )
            .group_by("day", "currency")
            .all()
        )

        balance_changes = defaultdict(lambda: defaultdict(Decimal))

        for row in incoming_q:
            balance_changes[row.day][row.currency] += row.total

        for row in outgoing_q:
            balance_changes[row.day][row.currency] -= row.total

        result = [
            {
                "day": day,
                "balance_changes": {k: float(v) for k, v in changes.items()},
            }
            for day, changes in sorted(balance_changes.items())
        ]

        return result

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
        return [
            {
                "year": y,
                "month": m,
                "amounts": {c: float(v) for c, v in monthly_totals[(y, m)].items()},
            }
            for (y, m) in months
        ]
