"""Stats service"""

import calendar
from collections import defaultdict
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence as SequenceABC
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from threading import Lock
from typing import Any, Callable, Iterable, Literal, Mapping

from app.dependencies.services import (
    get_currency_exchange_service,
    get_entity_service,
)
from app.models.entity import Entity, entities_tags
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.tag import Tag
from app.models.transaction import Transaction, TransactionStatus, transactions_tags
from app.models.treasury import Treasury
from app.seeding import (
    currency_exchange_tag,
    deposit_tag,
    donation_tag,
    f0_entity,
    fee_tag,
    rent_tag,
    room_tag,
    utilities_tag,
    withdrawal_tag,
)
from app.services.base import BaseService
from app.services.currency_exchange import CurrencyExchangeService
from app.services.entity import EntityService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import Date, and_, case, extract, func, literal, or_, select, union_all
from sqlalchemy.orm import Session, selectinload


class StatsService(BaseService):
    _cache: dict[str, Any] = {}
    _entity_cache_index: defaultdict[int, set[str]] = defaultdict(set)
    _treasury_cache_index: defaultdict[int, set[str]] = defaultdict(set)
    _cache_lock: Lock = Lock()

    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(get_entity_service),
        currency_exchange_service: CurrencyExchangeService = Depends(
            get_currency_exchange_service
        ),
    ):
        self.db = db
        self._entity_service = entity_service
        self._currency_exchange_service = currency_exchange_service

    # --- cache management -------------------------------------------------
    @classmethod
    def invalidate_entity_cache(cls, *entity_ids: int | None) -> None:
        cls._invalidate_cache_index(cls._entity_cache_index, entity_ids)

    @classmethod
    def invalidate_treasury_cache(cls, *treasury_ids: int | None) -> None:
        cls._invalidate_cache_index(cls._treasury_cache_index, treasury_ids)

    @classmethod
    def _invalidate_cache_index(
        cls,
        cache_index: defaultdict[int, set[str]],
        subject_ids: Iterable[int | None],
    ) -> None:
        subject_ids_set = {
            int(subject_id) for subject_id in subject_ids if subject_id is not None
        }
        if not subject_ids_set:
            return

        with cls._cache_lock:
            keys_to_remove = {
                key
                for subject_id in subject_ids_set
                for key in cache_index.pop(subject_id, set())
            }

            if not keys_to_remove:
                return

            for key in keys_to_remove:
                cls._cache.pop(key, None)

            for index in (cls._entity_cache_index, cls._treasury_cache_index):
                for tracked_keys in index.values():
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
        *,
        treasury_ids: Iterable[int | None] = (),
    ) -> Any:
        cls = type(self)
        cache_key = cls._build_cache_key(cache_name, args, kwargs)

        entity_ids_set = {
            int(entity_id) for entity_id in entity_ids if entity_id is not None
        }
        treasury_ids_set = {
            int(treasury_id) for treasury_id in treasury_ids if treasury_id is not None
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
            for treasury_id in treasury_ids_set:
                cls._treasury_cache_index.setdefault(treasury_id, set()).add(cache_key)

        return result

    def _subject_transaction_columns(self, subject_type: Literal["entity", "treasury"]):
        """Return incoming/outgoing transaction columns for a balance-bearing subject."""
        if subject_type == "entity":
            return Transaction.to_entity_id, Transaction.from_entity_id
        if subject_type == "treasury":
            return Transaction.to_treasury_id, Transaction.from_treasury_id
        raise ValueError(f"Unsupported stats subject type: {subject_type}")

    def _validate_stats_subject(
        self, subject_type: Literal["entity", "treasury"], subject_id: int
    ) -> None:
        if subject_type == "entity":
            self._entity_service.get(subject_id)
            return
        treasury = self.db.query(Treasury).filter(Treasury.id == subject_id).first()
        if treasury is None:
            from app.errors.common import NotFoundError

            raise NotFoundError(f"Treasury id={subject_id}")

    @staticmethod
    def _subject_cache_dependencies(
        subject_type: Literal["entity", "treasury"], subject_id: int
    ) -> tuple[list[int], list[int]]:
        if subject_type == "entity":
            return [subject_id], []
        return [], [subject_id]

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
        if amount == 0:
            return Decimal("0")

        amount_sign = Decimal("1") if amount > 0 else Decimal("-1")
        absolute_amount = abs(amount)
        # Use calculate_conversion to convert source currency -> usd.
        # (source_amount, target_amount, rate) returned; target_amount is the USD value.
        try:
            _, usd_amount, _ = self._currency_exchange_service.calculate_conversion(
                source_amount=absolute_amount,
                target_amount=None,
                source_currency=currency,
                target_currency="usd",
            )
            return usd_amount * amount_sign
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

    @staticmethod
    def _invoice_amounts_for_entity(
        invoice: Invoice, entity_id: int
    ) -> dict[str, Decimal]:
        """Return an invoice's payment options that belong to one recipient.

        A legacy invoice stores its recipient and amounts on the invoice itself.
        Multi-recipient invoices store them per item, while a paid item's
        transaction is authoritative when the recipient was selected at pay time.
        """
        if not invoice.items:
            if invoice.to_entity_id != entity_id:
                return {}
            amount_groups = [invoice.amounts or []]
        else:
            amount_groups = []
            for item in invoice.items:
                transaction = item.transaction
                recipient_id = (
                    transaction.to_entity_id
                    if transaction is not None
                    else item.to_entity_id
                )
                if recipient_id == entity_id:
                    amount_groups.append(item.amounts or [])

        options: dict[str, Decimal] = {}
        for amounts in amount_groups:
            for entry in amounts:
                currency = str(entry.get("currency") or "").lower().strip()
                if not currency:
                    continue
                options[currency] = options.get(currency, Decimal("0")) + Decimal(
                    str(entry.get("amount") or "0")
                )
        return options

    @staticmethod
    def _completed_invoice_transactions_for_entity(
        invoice: Invoice, entity_id: int
    ) -> list[Transaction]:
        if invoice.items:
            transactions = [item.transaction for item in invoice.items]
        else:
            transactions = [invoice.transaction]
        return [
            transaction
            for transaction in transactions
            if transaction is not None
            and transaction.to_entity_id == entity_id
            and transaction.status == TransactionStatus.COMPLETED
        ]

    def get_monthly_fee_sum_by_month(
        self, timeframe_from: date | None = None, timeframe_to: date | None = None
    ):
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)
        start_month = timeframe_from.replace(day=1)
        end_month = min(timeframe_to, date.today()).replace(day=1)

        invoice_load_options = (
            selectinload(Invoice.items).selectinload(InvoiceItem.transaction),
            selectinload(Invoice.transactions),
        )

        # Apply the timeframe before loading relationships, and fetch both statuses
        # together. Previously this loaded every fee invoice twice and discarded old
        # rows in Python.
        invoices = (
            self.db.query(Invoice)
            .options(*invoice_load_options)
            .filter(
                Invoice.billing_period >= start_month,
                Invoice.billing_period <= end_month,
                Invoice.tags.contains(fee_tag),
                Invoice.status.in_((InvoiceStatus.PAID, InvoiceStatus.PENDING)),
            )
            .all()
        )

        monthly_paid_totals = defaultdict(lambda: defaultdict(Decimal))
        monthly_unpaid_totals = defaultdict(lambda: defaultdict(Decimal))
        for invoice in invoices:
            # billing_period is guaranteed by the query, but keeping this guard makes
            # the type narrowing explicit.
            if invoice.billing_period is None:
                continue
            year = invoice.billing_period.year
            month = invoice.billing_period.month
            if invoice.status == InvoiceStatus.PAID:
                completed_transactions = (
                    self._completed_invoice_transactions_for_entity(
                        invoice, f0_entity.id
                    )
                )
                for transaction in completed_transactions:
                    monthly_paid_totals[(year, month)][
                        transaction.currency.lower()
                    ] += transaction.amount
            else:
                # Fee invoices expose several payment options; only the primary one
                # belongs in the expected (unpaid) total.
                entity_amounts = self._invoice_amounts_for_entity(invoice, f0_entity.id)
                if entity_amounts:
                    currency, amount = next(iter(entity_amounts.items()))
                    if amount:
                        monthly_unpaid_totals[(year, month)][currency] += amount

        all_months = set(monthly_paid_totals.keys()) | set(monthly_unpaid_totals.keys())

        result = []
        for year, month in sorted(all_months):
            paid_amounts = monthly_paid_totals.get((year, month), {})
            unpaid_amounts = monthly_unpaid_totals.get((year, month), {})

            paid_amounts_float = {k: float(v) for k, v in paid_amounts.items()}

            paid_total_usd = self._sum_amounts_usd(paid_amounts)
            unpaid_total_usd = self._sum_amounts_usd(unpaid_amounts)
            expected_total_usd = paid_total_usd + unpaid_total_usd

            result.append(
                {
                    "year": year,
                    "month": month,
                    "amounts": paid_amounts_float,
                    "total_usd": paid_total_usd,
                    "expected_total_usd": expected_total_usd,
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
            start_dt = datetime.combine(timeframe_from, time.min)
            end_dt = datetime.combine(timeframe_to + timedelta(days=1), time.min)
            rows = (
                self.db.query(
                    func.date(Transaction.created_at).label("day"),
                    func.count(Transaction.id).label("transaction_count"),
                )
                .filter(
                    and_(
                        Transaction.created_at >= start_dt,
                        Transaction.created_at < end_dt,
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
        return self.get_money_flow_by_day(
            "entity", entity_id, timeframe_from, timeframe_to
        )

    def get_treasury_money_flow_by_day(
        self,
        treasury_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        return self.get_money_flow_by_day(
            "treasury", treasury_id, timeframe_from, timeframe_to
        )

    def get_money_flow_by_day(
        self,
        subject_type: Literal["entity", "treasury"],
        subject_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Return incoming vs outgoing totals (USD) per day.

        Both totals are always positive and represent the sum of transactions where
        the subject is the receiver (incoming) or sender (outgoing), converted to USD.
        """

        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)
        cache_name = f"get_{subject_type}_money_flow_by_day"
        cache_args = (int(subject_id), timeframe_from, timeframe_to)

        def builder() -> list[dict[str, Any]]:
            incoming_column, outgoing_column = self._subject_transaction_columns(
                subject_type
            )
            day_col = func.date(Transaction.created_at)
            start_dt = datetime.combine(timeframe_from, time.min)
            end_dt = datetime.combine(timeframe_to + timedelta(days=1), time.min)
            direction = case(
                (incoming_column == subject_id, "incoming"),
                (outgoing_column == subject_id, "outgoing"),
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
                        Transaction.created_at >= start_dt,
                        Transaction.created_at < end_dt,
                        (outgoing_column == subject_id)
                        | (incoming_column == subject_id),
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

        entity_ids, treasury_ids = self._subject_cache_dependencies(
            subject_type, subject_id
        )
        return self._cached_result(
            cache_name,
            entity_ids,
            cache_args,
            {},
            builder,
            treasury_ids=treasury_ids,
        )

    def get_fee_transactions_by_month(
        self, timeframe_from: date | None = None, timeframe_to: date | None = None
    ):
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)
        timeframe_to_exclusive = datetime.combine(
            timeframe_to + timedelta(days=1), time.min
        )

        fee_query_result = (
            self.db.query(
                extract("year", Transaction.created_at).label("year"),
                extract("month", Transaction.created_at).label("month"),
                Transaction.to_entity_id,
                Transaction.currency,
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                and_(
                    Transaction.created_at >= timeframe_from,
                    Transaction.created_at < timeframe_to_exclusive,
                    Transaction.status == TransactionStatus.COMPLETED,
                    or_(
                        Transaction.tags.any(Tag.id == fee_tag.id),
                        Transaction.invoice.has(Invoice.tags.contains(fee_tag)),
                        Transaction.invoice_item.has(
                            InvoiceItem.invoice.has(Invoice.tags.contains(fee_tag))
                        ),
                    ),
                )
            )
            .group_by("year", "month", Transaction.to_entity_id, "currency")
            .order_by("year", "month")
            .all()
        )

        room_entity_ids = {
            entity_id
            for (entity_id,) in self.db.query(entities_tags.c.entity_id)
            .filter(entities_tags.c.tag_id == room_tag.id)
            .all()
        }
        f0_fee_monthly_totals: defaultdict[tuple, defaultdict[str, Decimal]] = (
            defaultdict(lambda: defaultdict(Decimal))
        )
        room_fee_monthly_totals: defaultdict[tuple, defaultdict[str, Decimal]] = (
            defaultdict(lambda: defaultdict(Decimal))
        )
        for row in fee_query_result:
            if row.to_entity_id == f0_entity.id:
                monthly_totals = f0_fee_monthly_totals
            elif row.to_entity_id in room_entity_ids:
                monthly_totals = room_fee_monthly_totals
            else:
                continue
            monthly_totals[(row.year, row.month)][row.currency] += row.total_amount

        expense_tag_ids = (rent_tag.id, utilities_tag.id)
        expense_query_result = (
            self.db.query(
                extract("year", Transaction.created_at).label("year"),
                extract("month", Transaction.created_at).label("month"),
                Transaction.currency,
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                Transaction.created_at >= timeframe_from,
                Transaction.created_at < timeframe_to_exclusive,
                Transaction.from_entity_id == f0_entity.id,
                Transaction.status == TransactionStatus.COMPLETED,
                or_(
                    Transaction.tags.any(Tag.id.in_(expense_tag_ids)),
                    Transaction.to_entity.has(
                        Entity.tags.any(Tag.id.in_(expense_tag_ids))
                    ),
                ),
            )
            .group_by("year", "month", "currency")
            .order_by("year", "month")
            .all()
        )
        expense_monthly_totals: defaultdict[tuple, defaultdict[str, Decimal]] = (
            defaultdict(lambda: defaultdict(Decimal))
        )
        for row in expense_query_result:
            expense_monthly_totals[(row.year, row.month)][
                row.currency
            ] += row.total_amount

        result = []
        all_months = (
            set(f0_fee_monthly_totals)
            | set(room_fee_monthly_totals)
            | set(expense_monthly_totals)
        )
        for year, month in sorted(all_months):
            f0_fee_total_usd = self._sum_amounts_usd(
                f0_fee_monthly_totals.get((year, month), {})
            )
            room_fee_total_usd = self._sum_amounts_usd(
                room_fee_monthly_totals.get((year, month), {})
            )
            expenses_usd = self._sum_amounts_usd(
                expense_monthly_totals.get((year, month), {})
            )
            result.append(
                {
                    "year": year,
                    "month": month,
                    "f0_fee_total_usd": f0_fee_total_usd,
                    "room_fee_total_usd": room_fee_total_usd,
                    "expenses_usd": expenses_usd,
                }
            )
        return result

    def get_donations_by_month(
        self, timeframe_from: date | None = None, timeframe_to: date | None = None
    ):
        timeframe_to = timeframe_to or date.today()
        timeframe_from = timeframe_from or timeframe_to - timedelta(days=365)
        timeframe_to_exclusive = datetime.combine(
            timeframe_to + timedelta(days=1), time.min
        )

        rows = (
            self.db.query(
                extract("year", Transaction.created_at).label("year"),
                extract("month", Transaction.created_at).label("month"),
                Transaction.to_entity_id,
                Transaction.currency,
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                Transaction.created_at >= timeframe_from,
                Transaction.created_at < timeframe_to_exclusive,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.tags.any(Tag.id == donation_tag.id),
            )
            .group_by("year", "month", Transaction.to_entity_id, "currency")
            .order_by("year", "month")
            .all()
        )

        f0_monthly_totals: defaultdict[tuple, defaultdict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        general_monthly_totals: defaultdict[tuple, defaultdict[str, Decimal]] = (
            defaultdict(lambda: defaultdict(Decimal))
        )
        for row in rows:
            monthly_totals = (
                f0_monthly_totals
                if row.to_entity_id == f0_entity.id
                else general_monthly_totals
            )
            monthly_totals[(row.year, row.month)][row.currency] += row.total_amount

        all_months = set(f0_monthly_totals) | set(general_monthly_totals)
        return [
            {
                "year": year,
                "month": month,
                "f0_donation_total_usd": self._sum_amounts_usd(
                    f0_monthly_totals.get((year, month), {})
                ),
                "general_donation_total_usd": self._sum_amounts_usd(
                    general_monthly_totals.get((year, month), {})
                ),
            }
            for year, month in sorted(all_months)
        ]

    def get_system_balance_history(
        self,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Compare physical treasury funds with positive virtual balances monthly.

        Entity balances are calculated independently so a debtor's negative balance
        cannot cancel money owed to another entity. Deposit, withdrawal, and exchange
        entities are excluded because they model the boundary of the accounting system.
        """
        timeframe_to = timeframe_to or date.today()
        start_day = timeframe_from or self._subtract_months(timeframe_to, 12)
        if start_day > timeframe_to:
            start_day = timeframe_to

        start_dt = datetime.combine(start_day, time.min)
        end_dt = datetime.combine(timeframe_to + timedelta(days=1), time.min)
        initial_day = start_day - timedelta(days=1)
        excluded_entity_ids = select(entities_tags.c.entity_id).where(
            entities_tags.c.tag_id.in_(
                (deposit_tag.id, withdrawal_tag.id, currency_exchange_tag.id)
            )
        )

        def balance_leg(
            *,
            subject_type: Literal["treasury", "entity"],
            incoming: bool,
            initial: bool,
        ):
            incoming_column, outgoing_column = self._subject_transaction_columns(
                subject_type
            )
            subject_column = incoming_column if incoming else outgoing_column
            subject_id = literal(0) if subject_type == "treasury" else subject_column
            amount = Transaction.amount if incoming else -Transaction.amount
            if initial:
                day = literal(initial_day, type_=Date)
                date_filter = Transaction.created_at < start_dt
            else:
                day = func.date(Transaction.created_at)
                date_filter = and_(
                    Transaction.created_at >= start_dt,
                    Transaction.created_at < end_dt,
                )

            subject_filter = subject_column.is_not(None)
            if subject_type == "entity":
                subject_filter = and_(
                    subject_filter,
                    ~subject_column.in_(excluded_entity_ids),
                )

            group_columns = [Transaction.currency]
            if subject_type == "entity":
                group_columns.append(subject_column)
            if not initial:
                group_columns.append(day)

            return (
                select(
                    literal(subject_type).label("subject_type"),
                    subject_id.label("subject_id"),
                    day.label("day"),
                    Transaction.currency.label("currency"),
                    func.sum(amount).label("delta"),
                )
                .where(
                    Transaction.status == TransactionStatus.COMPLETED,
                    subject_filter,
                    date_filter,
                )
                .group_by(*group_columns)
            )

        balance_legs = union_all(
            *(
                balance_leg(
                    subject_type=subject_type,
                    incoming=incoming,
                    initial=initial,
                )
                for subject_type in ("treasury", "entity")
                for incoming in (True, False)
                for initial in (True, False)
            )
        ).subquery()
        rows = self.db.execute(
            select(
                balance_legs.c.subject_type,
                balance_legs.c.subject_id,
                balance_legs.c.day,
                balance_legs.c.currency,
                func.sum(balance_legs.c.delta).label("delta"),
            )
            .group_by(
                balance_legs.c.subject_type,
                balance_legs.c.subject_id,
                balance_legs.c.day,
                balance_legs.c.currency,
            )
            .order_by(balance_legs.c.day)
        ).all()

        treasury_balances: defaultdict[str, Decimal] = defaultdict(Decimal)
        entity_balances: defaultdict[int, defaultdict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        treasury_deltas: defaultdict[date, defaultdict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        entity_deltas: defaultdict[
            date, defaultdict[int, defaultdict[str, Decimal]]
        ] = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))

        for row in rows:
            delta = row.delta or Decimal("0")
            if row.subject_type == "treasury":
                target = (
                    treasury_balances
                    if row.day == initial_day
                    else treasury_deltas[row.day]
                )
                target[row.currency] += delta
                continue

            target = (
                entity_balances[row.subject_id]
                if row.day == initial_day
                else entity_deltas[row.day][row.subject_id]
            )
            target[row.currency] += delta

        checkpoint_days: set[date] = set()
        checkpoint_month = start_day.replace(day=1)
        while checkpoint_month <= timeframe_to:
            month_end = checkpoint_month.replace(
                day=calendar.monthrange(checkpoint_month.year, checkpoint_month.month)[
                    1
                ]
            )
            checkpoint_days.add(min(month_end, timeframe_to))
            checkpoint_month = month_end + timedelta(days=1)

        result: list[dict[str, Any]] = []
        timeline = sorted(checkpoint_days | set(treasury_deltas) | set(entity_deltas))
        for current_day in timeline:
            for currency, delta in treasury_deltas[current_day].items():
                treasury_balances[currency] += delta
            for entity_id, currency_deltas in entity_deltas[current_day].items():
                for currency, delta in currency_deltas.items():
                    entity_balances[entity_id][currency] += delta

            if current_day not in checkpoint_days:
                continue

            positive_entity_balances: defaultdict[str, Decimal] = defaultdict(Decimal)
            for balances in entity_balances.values():
                for currency, amount in balances.items():
                    if amount > 0:
                        positive_entity_balances[currency] += amount

            real_funds_usd = self._sum_amounts_usd(treasury_balances)
            positive_entity_balances_usd = self._sum_amounts_usd(
                positive_entity_balances
            )
            result.append(
                {
                    "day": current_day,
                    "real_funds_usd": real_funds_usd,
                    "positive_entity_balances_usd": positive_entity_balances_usd,
                    "deficit_usd": max(
                        positive_entity_balances_usd - real_funds_usd, 0.0
                    ),
                }
            )

        return result

    def get_entity_balance_history(
        self,
        entity_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ):
        return self.get_balance_history(
            "entity", entity_id, timeframe_from, timeframe_to
        )

    def get_treasury_balance_history(
        self,
        treasury_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ):
        return self.get_balance_history(
            "treasury", treasury_id, timeframe_from, timeframe_to
        )

    def get_balance_history(
        self,
        subject_type: Literal["entity", "treasury"],
        subject_id: int,
        timeframe_from: date | None = None,
        timeframe_to: date | None = None,
    ):
        timeframe_to = timeframe_to or date.today()
        default_start_day = self._subtract_months(timeframe_to, 3)

        start_day = timeframe_from if timeframe_from is not None else default_start_day
        if start_day > timeframe_to:
            start_day = timeframe_to

        cache_name = f"get_{subject_type}_balance_history"
        cache_args = (int(subject_id), start_day, timeframe_to)

        def builder() -> list[dict[str, Any]]:
            self._validate_stats_subject(subject_type, subject_id)
            incoming_column, outgoing_column = self._subject_transaction_columns(
                subject_type
            )

            start_dt = datetime.combine(start_day, time.min)
            end_dt = datetime.combine(timeframe_to + timedelta(days=1), time.min)
            initial_day = start_day - timedelta(days=1)

            def balance_leg(*, incoming: bool, initial: bool):
                subject_column = incoming_column if incoming else outgoing_column
                amount = Transaction.amount if incoming else -Transaction.amount
                if initial:
                    day = literal(initial_day, type_=Date)
                    date_filter = Transaction.created_at < start_dt
                else:
                    day = func.date(Transaction.created_at)
                    date_filter = and_(
                        Transaction.created_at >= start_dt,
                        Transaction.created_at < end_dt,
                    )

                return (
                    select(
                        day.label("day"),
                        Transaction.currency.label("currency"),
                        func.sum(amount).label("delta"),
                    )
                    .where(
                        subject_column == subject_id,
                        Transaction.status == TransactionStatus.COMPLETED,
                        date_filter,
                    )
                    .group_by(day, Transaction.currency)
                )

            # Four index-friendly range aggregates replace the previous O(days)
            # balance recalculation. UNION ALL keeps incoming and outgoing legs
            # independent so PostgreSQL can use each composite entity/date index.
            balance_legs = union_all(
                balance_leg(incoming=True, initial=True),
                balance_leg(incoming=False, initial=True),
                balance_leg(incoming=True, initial=False),
                balance_leg(incoming=False, initial=False),
            ).subquery()

            rows = self.db.execute(
                select(
                    balance_legs.c.day,
                    balance_legs.c.currency,
                    func.sum(balance_legs.c.delta).label("delta"),
                )
                .group_by(balance_legs.c.day, balance_legs.c.currency)
                .order_by(balance_legs.c.day)
            ).all()

            initial_balances: dict[str, Decimal] = {}
            deltas_by_day: defaultdict[date, dict[str, Decimal]] = defaultdict(dict)
            for row in rows:
                delta = row.delta or Decimal("0")
                if row.day == initial_day:
                    initial_balances[row.currency] = delta
                else:
                    deltas_by_day[row.day][row.currency] = delta

            completed_balances = initial_balances.copy()
            last_completed_balances = completed_balances.copy()
            result: list[dict[str, Any]] = []
            for current_day in sorted(deltas_by_day):
                for currency, delta in deltas_by_day[current_day].items():
                    completed_balances[currency] = (
                        completed_balances.get(currency, Decimal("0")) + delta
                    )

                if completed_balances == last_completed_balances:
                    continue
                last_completed_balances = completed_balances.copy()
                result.append(
                    {
                        "day": current_day,
                        "balance_changes": {
                            currency: float(amount)
                            for currency, amount in completed_balances.items()
                        },
                        "total_usd": self._sum_amounts_usd(completed_balances),
                    }
                )

            return result

        entity_ids, treasury_ids = self._subject_cache_dependencies(
            subject_type, subject_id
        )
        return self._cached_result(
            cache_name,
            entity_ids,
            cache_args,
            {},
            builder,
            treasury_ids=treasury_ids,
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

    def _get_entity_activity(
        self,
        entity_id: int,
        incoming: bool,
        months: int,
        timeframe_to: date | None,
    ) -> dict[int, dict[str, Any]]:
        """Aggregate entity activity once for both top and monthly charts."""

        cache_args = (int(entity_id), incoming, months, timeframe_to)

        def builder() -> dict[int, dict[str, Any]]:
            start_dt, end_dt = self._calculate_timeframe_bounds(months, timeframe_to)
            other_entity_column = (
                Transaction.from_entity_id if incoming else Transaction.to_entity_id
            )
            filter_condition = (
                Transaction.to_entity_id == entity_id
                if incoming
                else Transaction.from_entity_id == entity_id
            )
            year = extract("year", Transaction.created_at)
            month = extract("month", Transaction.created_at)

            rows = self.db.execute(
                select(
                    year.label("year"),
                    month.label("month"),
                    other_entity_column.label("entity_id"),
                    Entity.name.label("entity_name"),
                    Transaction.currency,
                    func.sum(Transaction.amount).label("total_amount"),
                )
                .select_from(Transaction)
                .join(Entity, Entity.id == other_entity_column)
                .where(
                    Transaction.created_at >= start_dt,
                    Transaction.created_at <= end_dt,
                    filter_condition,
                )
                .group_by(
                    year,
                    month,
                    other_entity_column,
                    Entity.name,
                    Transaction.currency,
                )
            ).all()

            activity: dict[int, dict[str, Any]] = {}
            for row in rows:
                other_entity_id = int(row.entity_id)
                entity_data = activity.setdefault(
                    other_entity_id,
                    {"name": row.entity_name, "by_month": {}},
                )
                ym = (int(row.year), int(row.month))
                currency_totals = entity_data["by_month"].setdefault(ym, {})
                currency_totals[row.currency] = row.total_amount
            return activity

        return self._cached_result(
            "_get_entity_activity",
            [entity_id],
            cache_args,
            {},
            builder,
        )

    def _get_tag_activity(
        self,
        entity_id: int,
        incoming: bool,
        months: int,
        timeframe_to: date | None,
    ) -> dict[int, dict[str, Any]]:
        """Aggregate direct/fallback tags once for top and monthly charts.

        Transaction tags take precedence. Entity tags are used only when a
        transaction has no direct tags, matching the previous ORM-loading logic.
        """

        cache_args = (int(entity_id), incoming, months, timeframe_to)

        def builder() -> dict[int, dict[str, Any]]:
            start_dt, end_dt = self._calculate_timeframe_bounds(months, timeframe_to)
            entity_filter = (
                Transaction.to_entity_id == entity_id
                if incoming
                else Transaction.from_entity_id == entity_id
            )
            fallback_entity_column = (
                Transaction.from_entity_id if incoming else Transaction.to_entity_id
            )
            year = extract("year", Transaction.created_at)
            month = extract("month", Transaction.created_at)

            def aggregate_tag_query(*, fallback: bool):
                if fallback:
                    tag_id = entities_tags.c.tag_id
                    query = (
                        select(
                            year.label("year"),
                            month.label("month"),
                            tag_id.label("tag_id"),
                            Tag.name.label("tag_name"),
                            Transaction.currency.label("currency"),
                            func.sum(Transaction.amount).label("total_amount"),
                        )
                        .select_from(Transaction)
                        .join(
                            entities_tags,
                            entities_tags.c.entity_id == fallback_entity_column,
                        )
                        .join(Tag, Tag.id == tag_id)
                        .where(
                            ~select(transactions_tags.c.transaction_id)
                            .where(transactions_tags.c.transaction_id == Transaction.id)
                            .exists()
                        )
                    )
                else:
                    tag_id = transactions_tags.c.tag_id
                    query = (
                        select(
                            year.label("year"),
                            month.label("month"),
                            tag_id.label("tag_id"),
                            Tag.name.label("tag_name"),
                            Transaction.currency.label("currency"),
                            func.sum(Transaction.amount).label("total_amount"),
                        )
                        .select_from(Transaction)
                        .join(
                            transactions_tags,
                            transactions_tags.c.transaction_id == Transaction.id,
                        )
                        .join(Tag, Tag.id == tag_id)
                    )

                return query.where(
                    Transaction.created_at >= start_dt,
                    Transaction.created_at <= end_dt,
                    entity_filter,
                ).group_by(
                    year,
                    month,
                    tag_id,
                    Tag.name,
                    Transaction.currency,
                )

            rows = self.db.execute(
                union_all(
                    aggregate_tag_query(fallback=False),
                    aggregate_tag_query(fallback=True),
                )
            ).all()

            activity: dict[int, dict[str, Any]] = {}
            for row in rows:
                tag_id = int(row.tag_id)
                tag_data = activity.setdefault(
                    tag_id,
                    {"name": row.tag_name, "by_month": {}},
                )
                ym = (int(row.year), int(row.month))
                currency_totals = tag_data["by_month"].setdefault(ym, {})
                currency_totals[row.currency] = (
                    currency_totals.get(row.currency, Decimal("0")) + row.total_amount
                )
            return activity

        return self._cached_result(
            "_get_tag_activity",
            [entity_id],
            cache_args,
            {},
            builder,
        )

    def _get_top_entities(
        self,
        entity_id: int,
        incoming: bool,
        limit: int,
        months: int,
        timeframe_to: date | None,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        activity = self._get_entity_activity(entity_id, incoming, months, timeframe_to)
        totals: dict[int, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        for other_entity_id, entity_data in activity.items():
            for currency_map in entity_data["by_month"].values():
                for currency, amount in currency_map.items():
                    totals[other_entity_id][currency] += amount

        results = []
        for other_entity_id, amounts in totals.items():
            amounts_float = {
                currency: float(amount) for currency, amount in amounts.items()
            }
            total_usd = self._sum_amounts_usd(amounts)
            results.append(
                {
                    "entity_id": other_entity_id,
                    "entity_name": activity[other_entity_id]["name"],
                    "amounts": amounts_float,
                    "total_usd": total_usd,
                }
            )

        results.sort(key=lambda item: item["total_usd"], reverse=True)
        return results[:limit]

    def _get_top_tags(
        self,
        entity_id: int,
        incoming: bool,
        limit: int,
        months: int,
        timeframe_to: date | None,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        activity = self._get_tag_activity(entity_id, incoming, months, timeframe_to)
        totals: dict[int, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(Decimal)
        )
        for tag_id, tag_data in activity.items():
            for currency_map in tag_data["by_month"].values():
                for currency, amount in currency_map.items():
                    totals[tag_id][currency] += amount

        results = []
        for tag_id, amounts in totals.items():
            amounts_float = {
                currency: float(amount) for currency, amount in amounts.items()
            }
            total_usd = self._sum_amounts_usd(amounts)
            results.append(
                {
                    "tag_id": tag_id,
                    "tag_name": activity[tag_id]["name"],
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
                entity_id,
                True,
                limit,
                months,
                timeframe_to,
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
                entity_id,
                False,
                limit,
                months,
                timeframe_to,
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
                entity_id,
                True,
                limit,
                months,
                timeframe_to,
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
                entity_id,
                False,
                limit,
                months,
                timeframe_to,
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

        start_dt = datetime.combine(timeframe_from, time.min)
        end_dt = datetime.combine(timeframe_to + timedelta(days=1), time.min)

        # Aggregate only the requested range in the database. The previous version
        # materialized every matching Transaction ORM object from all history.
        rows = (
            self.db.query(
                extract("year", Transaction.created_at).label("year"),
                extract("month", Transaction.created_at).label("month"),
                Transaction.currency,
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                Transaction.created_at >= start_dt,
                Transaction.created_at < end_dt,
                or_(
                    Transaction.tags.any(Tag.id == tag_id),
                    Transaction.from_entity.has(Entity.tags.any(Tag.id == tag_id)),
                    Transaction.to_entity.has(Entity.tags.any(Tag.id == tag_id)),
                ),
            )
            .group_by("year", "month", Transaction.currency)
            .all()
        )

        # prepare monthly buckets
        monthly_totals: dict[tuple[int, int], dict[str, Decimal]] = {
            m: defaultdict(Decimal) for m in months
        }

        for row in rows:
            ym = (int(row.year), int(row.month))
            if ym in monthly_totals:
                monthly_totals[ym][row.currency] += row.total_amount

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

    # --- activity-by-month helpers ----------------------------------------

    def _build_months_list(
        self, start_dt: datetime, timeframe_to: date | None
    ) -> list[tuple[int, int]]:
        """Build ordered list of (year, month) tuples from start_dt through timeframe_to."""
        start_month = start_dt.date().replace(day=1)
        end_month = (timeframe_to or date.today()).replace(day=1)
        month_list: list[tuple[int, int]] = []
        cur = start_month
        while cur <= end_month:
            month_list.append((cur.year, cur.month))
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        return month_list

    def _get_activity_by_entity_by_month(
        self,
        entity_id: int,
        incoming: bool,
        limit: int,
        months: int,
        timeframe_to: date | None,
    ) -> list[dict[str, Any]]:
        """Return top-N entities with their USD totals per month."""
        start_dt, _ = self._calculate_timeframe_bounds(months, timeframe_to)
        month_list = self._build_months_list(start_dt, timeframe_to)
        activity = self._get_entity_activity(entity_id, incoming, months, timeframe_to)

        entity_period_totals: dict[int, float] = {}
        for eid, entity_data in activity.items():
            combined: dict[str, Decimal] = defaultdict(Decimal)
            for currency_map in entity_data["by_month"].values():
                for cur, amt in currency_map.items():
                    combined[cur] += amt
            entity_period_totals[eid] = float(self._sum_amounts_usd(combined))

        top_entity_ids = sorted(
            entity_period_totals, key=entity_period_totals.__getitem__, reverse=True
        )[:limit]

        result: list[dict[str, Any]] = []
        for eid in top_entity_ids:
            by_month = []
            ym_data = activity[eid]["by_month"]
            for ym in month_list:
                currency_map = ym_data.get(ym, {})
                total_usd = (
                    float(self._sum_amounts_usd(currency_map)) if currency_map else 0.0
                )
                by_month.append({"year": ym[0], "month": ym[1], "total_usd": total_usd})
            result.append(
                {
                    "entity_id": eid,
                    "entity_name": activity[eid]["name"],
                    "by_month": by_month,
                }
            )
        return result

    def _get_activity_by_tag_by_month(
        self,
        entity_id: int,
        incoming: bool,
        limit: int,
        months: int,
        timeframe_to: date | None,
    ) -> list[dict[str, Any]]:
        """Return top-N tags with their USD totals per month."""
        start_dt, _ = self._calculate_timeframe_bounds(months, timeframe_to)
        month_list = self._build_months_list(start_dt, timeframe_to)
        activity = self._get_tag_activity(entity_id, incoming, months, timeframe_to)

        tag_period_totals: dict[int, float] = {}
        for tid, tag_data in activity.items():
            combined: dict[str, Decimal] = defaultdict(Decimal)
            for currency_map in tag_data["by_month"].values():
                for cur, amt in currency_map.items():
                    combined[cur] += amt
            tag_period_totals[tid] = float(self._sum_amounts_usd(combined))

        top_tag_ids = sorted(
            tag_period_totals, key=tag_period_totals.__getitem__, reverse=True
        )[:limit]

        result: list[dict[str, Any]] = []
        for tid in top_tag_ids:
            by_month = []
            ym_data = activity[tid]["by_month"]
            for ym in month_list:
                currency_map = ym_data.get(ym, {})
                total_usd = (
                    float(self._sum_amounts_usd(currency_map)) if currency_map else 0.0
                )
                by_month.append({"year": ym[0], "month": ym[1], "total_usd": total_usd})
            result.append(
                {
                    "tag_id": tid,
                    "tag_name": activity[tid]["name"],
                    "by_month": by_month,
                }
            )
        return result

    def get_outgoing_by_entity_by_month(
        self,
        entity_id: int | None = None,
        limit: int = 5,
        months: int = 6,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Top-N expense destinations with monthly USD totals."""
        entity_id = entity_id or f0_entity.id
        cache_args = (int(entity_id), limit, months, timeframe_to)
        return self._cached_result(
            "get_outgoing_by_entity_by_month",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_activity_by_entity_by_month(
                entity_id,
                False,
                limit,
                months,
                timeframe_to,
            ),
        )

    def get_incoming_by_entity_by_month(
        self,
        entity_id: int | None = None,
        limit: int = 5,
        months: int = 6,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Top-N income sources with monthly USD totals."""
        entity_id = entity_id or f0_entity.id
        cache_args = (int(entity_id), limit, months, timeframe_to)
        return self._cached_result(
            "get_incoming_by_entity_by_month",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_activity_by_entity_by_month(
                entity_id,
                True,
                limit,
                months,
                timeframe_to,
            ),
        )

    def get_outgoing_by_tag_by_month(
        self,
        entity_id: int | None = None,
        limit: int = 5,
        months: int = 6,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Top-N outgoing tags with monthly USD totals."""
        entity_id = entity_id or f0_entity.id
        cache_args = (int(entity_id), limit, months, timeframe_to)
        return self._cached_result(
            "get_outgoing_by_tag_by_month",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_activity_by_tag_by_month(
                entity_id,
                False,
                limit,
                months,
                timeframe_to,
            ),
        )

    def get_incoming_by_tag_by_month(
        self,
        entity_id: int | None = None,
        limit: int = 5,
        months: int = 6,
        timeframe_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Top-N incoming tags with monthly USD totals."""
        entity_id = entity_id or f0_entity.id
        cache_args = (int(entity_id), limit, months, timeframe_to)
        return self._cached_result(
            "get_incoming_by_tag_by_month",
            [entity_id],
            cache_args,
            {},
            lambda: self._get_activity_by_tag_by_month(
                entity_id,
                True,
                limit,
                months,
                timeframe_to,
            ),
        )
