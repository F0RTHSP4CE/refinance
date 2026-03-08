"""Shared balance aggregation helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Sequence

from app.models.transaction import Transaction, TransactionStatus
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def build_entity_balance_subqueries(
    *,
    currency: str,
    status: TransactionStatus,
    end_datetime: datetime | None = None,
):
    credit_query = select(
        Transaction.to_entity_id.label("entity_id"),
        func.sum(Transaction.amount).label("total_credit"),
    ).where(
        Transaction.currency == currency,
        Transaction.status == status,
    )
    if end_datetime is not None:
        credit_query = credit_query.where(Transaction.created_at <= end_datetime)
    credit_subq = credit_query.group_by(Transaction.to_entity_id).subquery()

    debit_query = select(
        Transaction.from_entity_id.label("entity_id"),
        func.sum(Transaction.amount).label("total_debit"),
    ).where(
        Transaction.currency == currency,
        Transaction.status == status,
    )
    if end_datetime is not None:
        debit_query = debit_query.where(Transaction.created_at <= end_datetime)
    debit_subq = debit_query.group_by(Transaction.from_entity_id).subquery()

    balance_expr = func.coalesce(credit_subq.c.total_credit, 0) - func.coalesce(
        debit_subq.c.total_debit, 0
    )

    return credit_subq, debit_subq, balance_expr


def build_treasury_balance_subqueries(
    *,
    currency: str,
    status: TransactionStatus,
):
    credit_subq = (
        select(
            Transaction.to_treasury_id.label("treasury_id"),
            func.sum(Transaction.amount).label("total_credit"),
        )
        .where(
            Transaction.currency == currency,
            Transaction.status == status,
        )
        .group_by(Transaction.to_treasury_id)
        .subquery()
    )

    debit_subq = (
        select(
            Transaction.from_treasury_id.label("treasury_id"),
            func.sum(Transaction.amount).label("total_debit"),
        )
        .where(
            Transaction.currency == currency,
            Transaction.status == status,
        )
        .group_by(Transaction.from_treasury_id)
        .subquery()
    )

    balance_expr = func.coalesce(credit_subq.c.total_credit, 0) - func.coalesce(
        debit_subq.c.total_debit, 0
    )

    return credit_subq, debit_subq, balance_expr


def _merge_currency_totals(
    credit_rows: Sequence[Any],
    debit_rows: Sequence[Any],
) -> dict[str, Decimal]:
    totals_by_currency: dict[str, Decimal] = {}

    for row in credit_rows:
        current = totals_by_currency.get(row.currency, Decimal(0))
        totals_by_currency[row.currency] = current + row.total_credit

    for row in debit_rows:
        current = totals_by_currency.get(row.currency, Decimal(0))
        totals_by_currency[row.currency] = current - row.total_debit

    return totals_by_currency


def _execute_and_merge_currency_totals(
    *,
    db: Session,
    credit_query,
    debit_query,
) -> dict[str, Decimal]:
    credits = db.execute(credit_query).all()
    debits = db.execute(debit_query).all()
    return _merge_currency_totals(credits, debits)


def sum_entity_balances(
    *,
    db: Session,
    entity_id: int,
    status: TransactionStatus,
    end_datetime: datetime | None = None,
) -> dict[str, Decimal]:
    credit_query = select(
        Transaction.currency,
        func.sum(Transaction.amount).label("total_credit"),
    ).where(
        Transaction.to_entity_id == entity_id,
        Transaction.status == status,
    )
    if end_datetime is not None:
        credit_query = credit_query.where(Transaction.created_at <= end_datetime)
    credit_query = credit_query.group_by(Transaction.currency)

    debit_query = select(
        Transaction.currency,
        func.sum(Transaction.amount).label("total_debit"),
    ).where(
        Transaction.from_entity_id == entity_id,
        Transaction.status == status,
    )
    if end_datetime is not None:
        debit_query = debit_query.where(Transaction.created_at <= end_datetime)
    debit_query = debit_query.group_by(Transaction.currency)

    return _execute_and_merge_currency_totals(
        db=db,
        credit_query=credit_query,
        debit_query=debit_query,
    )


def sum_entity_balances_many(
    *,
    db: Session,
    entity_ids: list[int],
    status: TransactionStatus,
    end_datetime: datetime | None = None,
) -> dict[int, dict[str, Decimal]]:
    if not entity_ids:
        return {}

    unique_entity_ids = list(dict.fromkeys(entity_ids))

    credit_query = select(
        Transaction.to_entity_id.label("entity_id"),
        Transaction.currency,
        func.sum(Transaction.amount).label("total_credit"),
    ).where(
        Transaction.to_entity_id.in_(unique_entity_ids),
        Transaction.status == status,
    )
    if end_datetime is not None:
        credit_query = credit_query.where(Transaction.created_at <= end_datetime)
    credit_query = credit_query.group_by(
        Transaction.to_entity_id,
        Transaction.currency,
    )

    debit_query = select(
        Transaction.from_entity_id.label("entity_id"),
        Transaction.currency,
        func.sum(Transaction.amount).label("total_debit"),
    ).where(
        Transaction.from_entity_id.in_(unique_entity_ids),
        Transaction.status == status,
    )
    if end_datetime is not None:
        debit_query = debit_query.where(Transaction.created_at <= end_datetime)
    debit_query = debit_query.group_by(
        Transaction.from_entity_id,
        Transaction.currency,
    )

    credits = db.execute(credit_query).all()
    debits = db.execute(debit_query).all()

    totals_by_entity: dict[int, dict[str, Decimal]] = {
        entity_id: {} for entity_id in unique_entity_ids
    }

    for row in credits:
        entity_totals = totals_by_entity[row.entity_id]
        current = entity_totals.get(row.currency, Decimal(0))
        entity_totals[row.currency] = current + row.total_credit

    for row in debits:
        entity_totals = totals_by_entity[row.entity_id]
        current = entity_totals.get(row.currency, Decimal(0))
        entity_totals[row.currency] = current - row.total_debit

    return totals_by_entity


def sum_treasury_balances(
    *,
    db: Session,
    treasury_id: int,
    status: TransactionStatus,
) -> dict[str, Decimal]:
    credit_query = (
        select(
            Transaction.currency,
            func.sum(Transaction.amount).label("total_credit"),
        )
        .where(
            Transaction.to_treasury_id == treasury_id,
            Transaction.status == status,
        )
        .group_by(Transaction.currency)
    )
    debit_query = (
        select(
            Transaction.currency,
            func.sum(Transaction.amount).label("total_debit"),
        )
        .where(
            Transaction.from_treasury_id == treasury_id,
            Transaction.status == status,
        )
        .group_by(Transaction.currency)
    )

    return _execute_and_merge_currency_totals(
        db=db,
        credit_query=credit_query,
        debit_query=debit_query,
    )
