"""Weekly balance-reminder background task.

Every Monday at 10:00 a notification is sent to every active entity that has a
``telegram_id`` configured and either:

  - has a negative completed balance in at least one currency, or
  - has at least one PENDING invoice where it is the debtor (``from_entity_id``).

Entities with a non-negative balance *and* no unpaid invoices are silently skipped.
"""

from __future__ import annotations

import datetime
import logging
import random
from decimal import ROUND_UP, Decimal
from typing import TYPE_CHECKING

from app.config import Config
from app.dependencies.services import ServiceContainer
from app.models.entity import Entity
from app.models.invoice import Invoice, InvoiceStatus
from app.services.notification import NotificationService
from app.tasks import PeriodicTask
from sqlalchemy import nullslast

if TYPE_CHECKING:
    from app.services.balance import BalanceService
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_GREETINGS = (
    "Hello",
    "Dear",
    "Good evening",
    "Good day",
    "Hey",
    "Greetings",
    "Hi there",
    "Howdy",
)


# ---------------------------------------------------------------------------
# Message formatting helpers
# ---------------------------------------------------------------------------


def _fmt_amounts(amounts: list[dict]) -> str:
    """Return a human-readable string for a list of {currency, amount} dicts."""
    parts = []
    for entry in amounts:
        currency = str(entry.get("currency", "")).upper()
        amount = Decimal(str(entry.get("amount", "0")))
        parts.append(f"{amount:,.2f} {currency}")
    return " or ".join(parts)


def _sum_invoice_amounts(invoices: list[Invoice]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for inv in invoices:
        for entry in inv.amounts or []:
            currency = str(entry.get("currency", "")).lower()
            amount = Decimal(str(entry.get("amount", "0")))
            totals[currency] = totals.get(currency, Decimal(0)) + amount
    return totals


def _calc_recommended_topup(
    pending_invoices: list[Invoice],
    all_balances: dict[str, Decimal],
) -> dict[str, Decimal]:
    """Return the recommended top-up per currency.

    = sum of unpaid invoices - current balance (per currency), floored at 0.
    Positive balances reduce what needs to be deposited; negative ones add to it.
    """
    invoice_totals = _sum_invoice_amounts(pending_invoices)
    totals: dict[str, Decimal] = {}
    for currency, owed in invoice_totals.items():
        current = all_balances.get(currency, Decimal(0))
        needed = owed - current
        if needed > Decimal(0):
            totals[currency] = needed
    return totals


def _build_reminder_message(
    negative_balances: dict[str, Decimal],
    pending_invoices: list[Invoice],
    all_balances: dict[str, Decimal],
    entity_name: str,
) -> str:
    lines: list[str] = [f"{random.choice(_GREETINGS)}, <b>{entity_name}</b>."]

    topup = _calc_recommended_topup(pending_invoices, all_balances)
    if topup:
        topup_rounded = {
            currency: int(amount.to_integral_value(rounding=ROUND_UP))
            for currency, amount in topup.items()
        }
        topup_str = " / ".join(
            f"{amount} {currency.upper()}"
            for currency, amount in sorted(topup_rounded.items())
        )
        lines.append(f"\nYou owe <b>{topup_str}</b> ⚠️")
        for currency, amount in sorted(topup_rounded.items()):
            lines.append(f"💳 /deposit {amount} {currency.upper()}")

    if pending_invoices and all_balances:
        lines.append("\n💸 Current balance:")
        for currency, amount in sorted(all_balances.items()):
            lines.append(f"  {amount:,.2f} {currency.upper()}")

    if negative_balances:
        lines.append("\n💸 Negative balance:")
        for currency, amount in sorted(negative_balances.items()):
            lines.append(f"⚠️ <b>{amount:,.2f} {currency.upper()}</b>")

    if pending_invoices:
        lines.append("\n📋 Unpaid invoices:")
        for inv in pending_invoices:
            period = inv.billing_period.strftime("%b %Y") if inv.billing_period else "—"
            amounts_str = _fmt_amounts(inv.amounts or [])
            lines.append(f"  • Invoice #{inv.id} — {period} — {amounts_str}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def send_balance_reminder(
    entity: Entity,
    db: "Session",
    balance_service: "BalanceService",
    notification_service: NotificationService,
) -> dict[str, bool] | None:
    """Send a balance reminder to a single entity if needed.

    Returns the per-channel delivery results if a message was sent,
    or ``None`` if the entity had nothing to report (or no channels configured).
    """
    auth = entity.auth or {}
    if not auth.get("telegram_id"):
        return None

    balance = balance_service.get_balances(entity.id)
    negative_balances: dict[str, Decimal] = {}
    for currency, cd in balance.completed.items():
        if cd.value < Decimal(0):
            negative_balances[currency] = cd.value

    pending_invoices: list[Invoice] = (
        db.query(Invoice)
        .filter(
            Invoice.from_entity_id == entity.id,
            Invoice.status == InvoiceStatus.PENDING,
        )
        .order_by(
            nullslast(Invoice.billing_period.asc()),
            Invoice.id.asc(),
        )
        .all()
    )

    if not negative_balances and not pending_invoices:
        return None

    message = _build_reminder_message(
        negative_balances,
        pending_invoices,
        all_balances={
            currency: cd.value
            for currency, cd in balance.completed.items()
            if cd.value != Decimal(0)
        },
        entity_name=entity.name,
    )
    results = notification_service.send(entity, message)
    logger.info(
        "Balance reminder sent to entity id=%s via %s",
        entity.id,
        list(results.keys()),
    )
    return results


def send_reminders_to_all(
    db: "Session",
    balance_service: "BalanceService",
    notification_service: NotificationService,
) -> int:
    """Send reminders to all active entities that need attention. Returns number sent."""
    entities: list[Entity] = (
        db.query(Entity)
        .filter(Entity.active.is_(True))
        .filter(Entity.auth.isnot(None))
        .all()
    )
    sent_count = 0
    for entity in entities:
        results = send_balance_reminder(
            entity,
            db=db,
            balance_service=balance_service,
            notification_service=notification_service,
        )
        if results and any(results.values()):
            sent_count += 1
    return sent_count


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def _seconds_until_next_monday_10am(now: datetime.datetime) -> float:
    """Return seconds until the next Monday at 10:00 (local time)."""
    days_ahead = (7 - now.weekday()) % 7
    target = datetime.datetime.combine(
        now.date() + datetime.timedelta(days=days_ahead),
        datetime.time(10, 0),
    )
    if target <= now:
        target += datetime.timedelta(weeks=1)
    return (target - now).total_seconds()


class BalanceReminderTask(PeriodicTask):
    def next_delay(self) -> float:
        return _seconds_until_next_monday_10am(datetime.datetime.now())

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return send_reminders_to_all(
            db=container.db,
            balance_service=container.balance_service,
            notification_service=NotificationService(config),
        )


def run_balance_reminders() -> int:
    return BalanceReminderTask().run()


async def schedule_balance_reminders() -> None:
    await BalanceReminderTask().schedule()
