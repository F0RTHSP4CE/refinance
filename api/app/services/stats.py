"""Stats service"""

import calendar
from collections import defaultdict
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence as SequenceABC
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from threading import Lock
from typing import Any, Callable, Iterable, Mapping

from app.dependencies.services import (
    get_balance_service,
    get_currency_exchange_service,
    get_entity_service,
    get_fee_service,
)
from app.models.entity import Entity
from app.models.invoice import Invoice, InvoiceStatus
from app.models.tag import Tag
from app.models.transaction import Transaction, TransactionStatus
from app.seeding import ex_resident_tag, f0_entity, fee_tag, member_tag, resident_tag
from app.services.balance import BalanceService
from app.services.base import BaseService
from app.services.currency_exchange import CurrencyExchangeService
from app.services.entity import EntityService
from app.services.fee import FeeService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import and_, case, extract, func, or_
from sqlalchemy.orm import Session, selectinload


class StatsService(BaseService):
    _cache: dict[str, Any] = {}
    _entity_cache_index: defaultdict[int, set[str]] = defaultdict(set)
    _cache_lock: Lock = Lock()

    def __init__(
        self,
        db: Session = Depends(get_uow),
        fee_service: FeeService = Depends(get_fee_service),
        balance_service: BalanceService = Depends(get_balance_service),
        entity_service: EntityService = Depends(get_entity_service),
        currency_exchange_service: CurrencyExchangeService = Depends(
            get_currency_exchange_service
        ),
    ):
        self.db = db
        self._fee_service = fee_service
        self._balance_service = balance_service
        self._entity_service = entity_service
        self._currency_exchange_service = currency_exchange_service

    # --- cache management -------------------------------------------------
    @classmethod
    def invalidate_entity_cache(cls, *entity_ids: int | None) -> None:
        entity_ids_set = {
            int(entity_id) for entity_id in entity_ids if entity_id is not None
        }
        if not entity_ids_set:
            return

        with cls._cache_lock:
            keys_to_remove = {
                key
                for entity_id in entity_ids_set
                for key in cls._entity_cache_index.pop(entity_id, set())
            }

            if not keys_to_remove:
                return

            for key in keys_to_remove:
                cls._cache.pop(key, None)

            for tracked_keys in cls._entity_cache_index.values():
                tracked_keys.difference_update(keys_to_remove)

    @staticmethod
    def _serialize_cache_value(value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, MappingABC):
            return tuple(
                (k, StatsService._serialize_cache_value(v))
                for k, v in sorted(value.items())
            )
        if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes)):
            return tuple(StatsService._serialize_cache_value(v) for v in value)
        return value

    @classmethod
    def _build_cache_key(
        cls, name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> str:
        serialized_args = tuple(cls._serialize_cache_value(arg) for arg in args)
        serialized_kwargs = tuple(
            (key, cls._serialize_cache_value(val))
            for key, val in sorted(kwargs.items())
        )
        return repr((name, serialized_args, serialized_kwargs))

    def _cached_result(
        self,
        cache_name: str,
        entity_ids: Iterable[int | None],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        builder: Callable[[], Any],
    ) -> Any:
        cls = type(self)
        cache_key = cls._build_cache_key(cache_name, args, kwargs)

        entity_ids_set = {
            int(entity_id) for entity_id in entity_ids if entity_id is not None
        }

        with cls._cache_lock:
            cached = cls._cache.get(cache_key)
            if cached is not None:
                return deepcopy(cached)

        result = builder()

        with cls._cache_lock:
            cls._cache[cache_key] = deepcopy(result)
            for entity_id in entity_ids_set:
                cls._entity_cache_index.setdefault(entity_id, set()).add(cache_key)

        return result

    @classmethod
    def _get_cached_value(
        cls, cache_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> Any | None:
        cache_key = cls._build_cache_key(cache_name, args, kwargs)
        with cls._cache_lock:
            cached = cls._cache.get(cache_key)
            if cached is None:
                return None
            return deepcopy(cached)

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
        invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.to_entity_id == hackerspace.id,
                Invoice.billing_period.isnot(None),
                Invoice.tags.contains(fee_tag),
                Invoice.status == InvoiceStatus.PAID,
            )
            .all()
        )

        monthly_totals = defaultdict(lambda: defaultdict(Decimal))
        today = date.today()

        for invoice in invoices:
            if invoice.billing_period is None:
                continue
            if invoice.transaction is None:
                continue
            if invoice.transaction.status != TransactionStatus.COMPLETED:
                continue
            year = invoice.billing_period.year
            month = invoice.billing_period.month

            # Skip future months
            if year > today.year or (year == today.year and month > today.month):
                continue

            # Check if the month is within the requested timeframe
            fee_date = date(year, month, 1)
            start_month = timeframe_from.replace(day=1)
            end_month = timeframe_to.replace(day=1)

            if not (start_month <= fee_date <= end_month):
                continue

            monthly_totals[(year, month)][
                invoice.transaction.currency.lower()
            ] += invoice.transaction.amount

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
        cache_args = (int(entity_id), timeframe_from, timeframe_to)

        def builder() -> list[dict[str, Any]]:
            rows = (
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
            return [
                {"day": row.day, "transaction_count": row.transaction_count}
                for row in rows
            ]

        return self._cached_result(
            "get_entity_transactions_by_day",
            [entity_id],
            cache_args,
            {},
            builder,
        )

    def get_entity_money_flow_by_day(
        self,
        entity_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Return incoming vs outgoing totals (USD) per day.

        Both totals are always positive and represent the sum of transactions where
        the entity is the receiver (incoming) or sender (outgoing), converted to USD.
        """

        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)
        cache_args = (int(entity_id), timeframe_from, timeframe_to)

        def builder() -> list[dict[str, Any]]:
            day_col = func.date(Transaction.created_at)
            direction = case(
                (Transaction.to_entity_id == entity_id, "incoming"),
                (Transaction.from_entity_id == entity_id, "outgoing"),
                else_="other",
            ).label("direction")

            rows = (
                self.db.query(
                    day_col.label("day"),
                    direction,
                    Transaction.currency.label("currency"),
                    func.sum(Transaction.amount).label("total_amount"),
                )
                .filter(
                    and_(
                        day_col >= timeframe_from,
                        day_col <= timeframe_to,
                        (Transaction.from_entity_id == entity_id)
                        | (Transaction.to_entity_id == entity_id),
                    )
                )
                .group_by("day", "direction", "currency")
                .order_by("day")
                .all()
            )

            totals_by_day: defaultdict[date, dict[str, defaultdict[str, Decimal]]] = (
                defaultdict(
                    lambda: {
                        "incoming": defaultdict(Decimal),
                        "outgoing": defaultdict(Decimal),
                    }
                )
            )

            for row in rows:
                if row.direction not in ("incoming", "outgoing"):
                    continue
                if row.total_amount is None:
                    continue
                totals_by_day[row.day][row.direction][row.currency] += row.total_amount

            result: list[dict[str, Any]] = []
            for day in sorted(totals_by_day.keys()):
                incoming_amounts = totals_by_day[day]["incoming"]
                outgoing_amounts = totals_by_day[day]["outgoing"]
                result.append(
                    {
                        "day": day,
                        "incoming_total_usd": float(
                            self._sum_amounts_usd(incoming_amounts)
                        ),
                        "outgoing_total_usd": float(
                            self._sum_amounts_usd(outgoing_amounts)
                        ),
                    }
                )
            return result

        return self._cached_result(
            "get_entity_money_flow_by_day",
            [entity_id],
            cache_args,
            {},
            builder,
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
        default_start_day = self._subtract_months(timeframe_to, 3)

        start_day = timeframe_from if timeframe_from is not None else default_start_day
        if start_day > timeframe_to:
            start_day = timeframe_to

        cache_args = (int(entity_id), start_day, timeframe_to)

        def builder() -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            current_day = start_day
            last_completed_balances: dict[str, Decimal] | None = None

            # To avoid rendering a long empty stretch at the beginning of the timeframe,
            # only emit the first day if there is an actual balance change versus the
            # previous day. This keeps the chart aligned with other stats charts that
            # naturally begin at the first available datapoint.
            previous_day = start_day - timedelta(days=1)
            previous_balances = self._balance_service.get_balances(
                entity_id, end_date=previous_day
            )
            previous_completed = self._normalize_currency_mapping(
                previous_balances.completed
            )

            while current_day <= timeframe_to:
                balances = self._balance_service.get_balances(
                    entity_id, end_date=current_day
                )
                completed_balances = self._normalize_currency_mapping(
                    balances.completed
                )

                if current_day == start_day:
                    # Emit start_day only if it differs from the previous day.
                    if completed_balances == previous_completed:
                        last_completed_balances = completed_balances.copy()
                        current_day += timedelta(days=1)
                        continue

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

        return self._cached_result(
            "get_entity_balance_history",
            [entity_id],
            cache_args,
            {},
            builder,
        )

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
        cache_args = (entity_id, limit, months, timeframe_to)

        return self._cached_result(
            "get_top_incoming_entities",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_top_entities(
                Transaction.from_entity_id,
                limit,
                months,
                timeframe_to,
                Transaction.to_entity_id == entity_id,
            ),
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
        cache_args = (entity_id, limit, months, timeframe_to)

        return self._cached_result(
            "get_top_outgoing_entities",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_top_entities(
                Transaction.to_entity_id,
                limit,
                months,
                timeframe_to,
                Transaction.from_entity_id == entity_id,
            ),
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
        cache_args = (entity_id, limit, months, timeframe_to)

        return self._cached_result(
            "get_top_incoming_tags",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_top_tags(
                limit,
                months,
                timeframe_to,
                Transaction.to_entity_id == entity_id,
                "from_entity",
            ),
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
        cache_args = (entity_id, limit, months, timeframe_to)

        return self._cached_result(
            "get_top_outgoing_tags",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_top_tags(
                limit,
                months,
                timeframe_to,
                Transaction.from_entity_id == entity_id,
                "to_entity",
            ),
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
