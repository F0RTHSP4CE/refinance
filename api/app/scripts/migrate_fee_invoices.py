"""Backfill fee invoices for historical transactions."""

from __future__ import annotations

import argparse
import calendar
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from app.config import get_config
from app.db import DatabaseConnection
from app.models.entity import Entity
from app.models.invoice import Invoice, InvoiceStatus
from app.models.tag import Tag
from app.models.transaction import Transaction, TransactionStatus
from sqlalchemy.orm import Session, selectinload

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

AUG_2025 = date(2025, 8, 1)

RESIDENT_FEE = {
    "usd": Decimal("42.00"),
    "gel": Decimal("115.00"),
}
MEMBER_FEE = {
    "usd": Decimal("25.00"),
    "gel": Decimal("70.00"),
}


@dataclass(frozen=True)
class FeeResolution:
    label: str
    amounts: list[dict[str, str]]
    used_fallback_amount: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill fee invoices")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of transactions to process (0 = no limit)",
    )
    return parser.parse_args()


def _parse_comment_for_date(comment: str | None) -> tuple[int, int] | None:
    if not comment:
        return None

    # regex to find YYYY-MM or MM-YYYY
    import re

    match = re.search(r"(\d{4})-(\d{1,2})|(\d{1,2})-(\d{4})", comment)
    if match:
        if match.group(1):
            return int(match.group(1)), int(match.group(2))
        return int(match.group(4)), int(match.group(3))

    # regex to find month name and year
    month_names = {
        name.lower(): idx for idx, name in enumerate(calendar.month_name) if name
    }
    month_names.update(
        {abbr.lower(): idx for idx, abbr in enumerate(calendar.month_abbr) if abbr}
    )
    month_pattern = "|".join(sorted(month_names.keys(), key=len, reverse=True))
    match = re.search(rf"({month_pattern})\s+(\d{{4}})", comment, re.IGNORECASE)
    if match:
        month_key = match.group(1).lower()
        year = int(match.group(2))
        return year, month_names[month_key]

    return None


def _normalize_amount(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"))


def _as_amounts_payload(amounts: dict[str, Decimal]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for currency, amount in sorted(amounts.items()):
        payload.append(
            {
                "currency": currency.lower(),
                "amount": format(_normalize_amount(amount), "f"),
            }
        )
    return payload


def _resolve_fee_amounts(
    *,
    billing_period: date,
    currency: str,
    amount: Decimal,
) -> FeeResolution:
    normalized_currency = currency.lower()
    normalized_amount = _normalize_amount(amount)

    if billing_period < AUG_2025:
        return FeeResolution(
            label="resident-pre-2025-08",
            amounts=_as_amounts_payload({normalized_currency: normalized_amount}),
            used_fallback_amount=True,
        )

    if (
        normalized_currency in RESIDENT_FEE
        and normalized_amount == RESIDENT_FEE[normalized_currency]
    ):
        return FeeResolution(
            label="resident",
            amounts=_as_amounts_payload(RESIDENT_FEE),
            used_fallback_amount=False,
        )

    if (
        normalized_currency in MEMBER_FEE
        and normalized_amount == MEMBER_FEE[normalized_currency]
    ):
        return FeeResolution(
            label="member",
            amounts=_as_amounts_payload(MEMBER_FEE),
            used_fallback_amount=False,
        )

    return FeeResolution(
        label="unknown-amount",
        amounts=_as_amounts_payload({normalized_currency: normalized_amount}),
        used_fallback_amount=True,
    )


def _infer_fee_type_from_amount(currency: str, amount: Decimal) -> str | None:
    normalized_currency = currency.lower()
    normalized_amount = _normalize_amount(amount)
    if normalized_currency not in RESIDENT_FEE or normalized_currency not in MEMBER_FEE:
        return None

    resident_amount = RESIDENT_FEE[normalized_currency]
    member_amount = MEMBER_FEE[normalized_currency]
    resident_diff = abs(normalized_amount - resident_amount)
    member_diff = abs(normalized_amount - member_amount)

    if member_diff < resident_diff:
        return "member"
    return "resident"


def _resolve_billing_period(tx: Transaction) -> date | None:
    parsed = _parse_comment_for_date(tx.comment)
    if parsed is not None:
        year, month = parsed
        return date(year, month, 1)
    if tx.created_at is not None:
        return date(tx.created_at.year, tx.created_at.month, 1)
    return None


def _load_fee_tag(session: Session) -> Tag:
    fee_tag = session.query(Tag).filter(Tag.name.ilike("fee")).first()
    if fee_tag is None:
        raise RuntimeError("Fee tag not found; ensure seed data is present.")
    return fee_tag


def _load_hackerspace_entity(session: Session) -> Entity:
    hackerspace = session.query(Entity).filter(Entity.id == 1).first()
    if hackerspace is None:
        hackerspace = session.query(Entity).filter(Entity.name.ilike("f0")).first()
    if hackerspace is None:
        raise RuntimeError("Hackerspace entity not found; ensure seed data is present.")
    return hackerspace


def _load_existing_fee_invoices(session: Session, fee_tag: Tag) -> dict[int, set[date]]:
    existing: dict[int, set[date]] = defaultdict(set)
    invoices = (
        session.query(Invoice)
        .options(selectinload(Invoice.tags))
        .filter(Invoice.tags.contains(fee_tag))
        .all()
    )
    for invoice in invoices:
        if invoice.billing_period is None:
            continue
        existing[invoice.from_entity_id].add(invoice.billing_period)
    return existing


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _iter_months(start: date, end: date) -> Iterable[date]:
    current = _month_start(start)
    last = _month_start(end)
    while current <= last:
        yield current
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = date(year, month, 1)


def _iter_fee_transactions(
    session: Session, fee_tag: Tag, limit: int
) -> Iterable[Transaction]:
    query = (
        session.query(Transaction)
        .options(selectinload(Transaction.tags))
        .filter(Transaction.tags.contains(fee_tag))
        .order_by(Transaction.id)
    )
    if limit > 0:
        query = query.limit(limit)
    return query.all()


def _attach_invoice(
    session: Session,
    *,
    tx: Transaction,
    billing_period: date,
    fee_tag: Tag,
    resolution: FeeResolution,
) -> Invoice:
    invoice = Invoice(
        actor_entity_id=tx.actor_entity_id,
        from_entity_id=tx.from_entity_id,
        to_entity_id=tx.to_entity_id,
        amounts=resolution.amounts,
        billing_period=billing_period,
        status=(
            InvoiceStatus.PAID
            if tx.status == TransactionStatus.COMPLETED
            else InvoiceStatus.PENDING
        ),
        comment=tx.comment
        or f"Monthly fee {billing_period.year}-{billing_period.month:02d}",
    )
    invoice.tags = [fee_tag]
    session.add(invoice)
    session.flush()

    tx.invoice_id = invoice.id
    session.add(tx)
    session.flush()
    return invoice


def _attach_unpaid_invoice(
    session: Session,
    *,
    hackerspace: Entity,
    payer_entity_id: int,
    billing_period: date,
    fee_tag: Tag,
    fee_type: str,
) -> Invoice:
    amounts = RESIDENT_FEE if fee_type == "resident" else MEMBER_FEE
    invoice = Invoice(
        actor_entity_id=hackerspace.id,
        from_entity_id=payer_entity_id,
        to_entity_id=hackerspace.id,
        amounts=_as_amounts_payload(amounts),
        billing_period=billing_period,
        status=InvoiceStatus.PENDING,
        comment=f"Monthly fee {billing_period.year}-{billing_period.month:02d}",
    )
    invoice.tags = [fee_tag]
    session.add(invoice)
    session.flush()
    return invoice


def main() -> None:
    args = parse_args()

    config = get_config()
    db = DatabaseConnection(config=config)
    session = db.get_session()

    created = 0
    created_unpaid = 0
    skipped_existing = 0
    skipped_no_period = 0
    skipped_missing = 0
    used_fallback_amount = 0
    skipped_unpaid_existing = 0
    skipped_unpaid_no_type = 0

    try:
        fee_tag = _load_fee_tag(session)
        hackerspace = _load_hackerspace_entity(session)
        existing_invoices = _load_existing_fee_invoices(session, fee_tag)
        transactions = _iter_fee_transactions(session, fee_tag, args.limit)
        logger.info("Found %d fee transactions", len(transactions))

        first_paid_period: dict[int, date] = {}
        last_paid_type: dict[int, str] = {}
        last_paid_period: dict[int, date] = {}

        for tx in transactions:
            billing_period = _resolve_billing_period(tx)

            if (
                billing_period is not None
                and tx.status == TransactionStatus.COMPLETED
                and tx.amount is not None
                and tx.currency is not None
            ):
                if tx.from_entity_id not in first_paid_period:
                    first_paid_period[tx.from_entity_id] = billing_period
                else:
                    earliest = first_paid_period[tx.from_entity_id]
                    if billing_period < earliest:
                        first_paid_period[tx.from_entity_id] = billing_period

                inferred = _infer_fee_type_from_amount(tx.currency, tx.amount)
                if inferred is not None and billing_period >= AUG_2025:
                    last_seen = last_paid_period.get(tx.from_entity_id)
                    if last_seen is None or billing_period >= last_seen:
                        last_paid_type[tx.from_entity_id] = inferred
                        last_paid_period[tx.from_entity_id] = billing_period

            if tx.invoice_id is not None:
                skipped_existing += 1
                continue

            if billing_period is None:
                skipped_no_period += 1
                continue

            if tx.amount is None or tx.currency is None:
                skipped_missing += 1
                continue

            if billing_period in existing_invoices.get(tx.from_entity_id, set()):
                skipped_existing += 1
                continue

            resolution = _resolve_fee_amounts(
                billing_period=billing_period,
                currency=tx.currency,
                amount=tx.amount,
            )
            if resolution.used_fallback_amount:
                used_fallback_amount += 1

            _attach_invoice(
                session,
                tx=tx,
                billing_period=billing_period,
                fee_tag=fee_tag,
                resolution=resolution,
            )
            existing_invoices.setdefault(tx.from_entity_id, set()).add(billing_period)
            created += 1

        today = _month_start(date.today())
        for entity_id, start_period in first_paid_period.items():
            for period in _iter_months(start_period, today):
                if period in existing_invoices.get(entity_id, set()):
                    skipped_unpaid_existing += 1
                    continue

                if period < AUG_2025:
                    fee_type = "resident"
                else:
                    fee_type = last_paid_type.get(entity_id)

                if fee_type is None:
                    skipped_unpaid_no_type += 1
                    fee_type = "resident"

                _attach_unpaid_invoice(
                    session,
                    hackerspace=hackerspace,
                    payer_entity_id=entity_id,
                    billing_period=period,
                    fee_tag=fee_tag,
                    fee_type=fee_type,
                )
                existing_invoices.setdefault(entity_id, set()).add(period)
                created_unpaid += 1

        if args.dry_run:
            session.rollback()
            logger.info("Dry-run enabled; rolled back changes.")
        else:
            session.commit()
            logger.info("Committed fee invoice migration.")

    except Exception:
        session.rollback()
        logger.exception("Fee invoice migration failed; rolled back changes.")
        raise
    finally:
        session.close()

    logger.info(
        "Summary: created=%d created_unpaid=%d skipped_existing=%d "
        "skipped_no_period=%d skipped_missing=%d used_fallback_amount=%d "
        "skipped_unpaid_existing=%d skipped_unpaid_no_type=%d",
        created,
        created_unpaid,
        skipped_existing,
        skipped_no_period,
        skipped_missing,
        used_fallback_amount,
        skipped_unpaid_existing,
        skipped_unpaid_no_type,
    )


if __name__ == "__main__":
    main()
