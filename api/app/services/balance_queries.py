"""Shared balance aggregation helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

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

    credits = db.execute(credit_query).all()
    debits = db.execute(debit_query).all()

    credit_dict: dict[str, Decimal] = {
        result.currency: result.total_credit for result in credits
    }
    debit_dict: dict[str, Decimal] = {
        result.currency: result.total_debit for result in debits
    }

    total_by_currency: dict[str, Decimal] = {}
    all_currencies = set(credit_dict.keys()).union(set(debit_dict.keys()))
    for currency in all_currencies:
        credit = credit_dict.get(currency, Decimal(0))
        debit = debit_dict.get(currency, Decimal(0))
        total_by_currency[currency] = credit - debit

    return total_by_currency


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

    credits = db.execute(credit_query).all()
    debits = db.execute(debit_query).all()

    credit_dict: dict[str, Decimal] = {
        result.currency: result.total_credit for result in credits
    }
    debit_dict: dict[str, Decimal] = {
        result.currency: result.total_debit for result in debits
    }

    total_by_currency: dict[str, Decimal] = {}
    for currency in set(credit_dict.keys()) | set(debit_dict.keys()):
        credit = credit_dict.get(currency, Decimal(0))
        debit = debit_dict.get(currency, Decimal(0))
        total_by_currency[currency] = credit - debit

    return total_by_currency
