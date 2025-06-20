"""Stats service"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.bootstrap import f0_entity, resident_tag
from app.models.entity import Entity
from app.models.transaction import Transaction
from app.services.base import BaseService
from app.services.entity import EntityService
from app.services.resident_fee import ResidentFeeService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import and_, extract, func
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
