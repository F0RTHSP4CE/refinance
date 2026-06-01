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
from app.services.entity_owed import calculate_entity_owed
from app.services.notification import NotificationService
from app.tasks import PeriodicTask
from sqlalchemy import nullslast

if TYPE_CHECKING:
    from app.services.balance import BalanceService
    from app.services.currency_exchange import CurrencyExchangeService
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


def _per_invoice_amounts(invoices: list[Invoice]) -> list[dict[str, Decimal]]:
    """Return per-invoice alternative currency amounts.

    Each element is one invoice represented as ``{currency: amount}`` where the
    currencies are *alternatives* — paying in any single one satisfies the invoice.
    """
    result: list[dict[str, Decimal]] = []
    for inv in invoices:
        options: dict[str, Decimal] = {}
        for entry in inv.amounts or []:
            currency = str(entry.get("currency", "")).lower()
            amount = Decimal(str(entry.get("amount", "0")))
            if currency:
                options[currency] = options.get(currency, Decimal(0)) + amount
        if options:
            result.append(options)
    return result


def _calc_recommended_topup(
    pending_invoices: list[Invoice],
    all_balances: dict[str, Decimal],
    convert_amount,
) -> dict[str, Decimal]:
    """Return the minimum top-up recommendation as {currency: amount}.

    Uses the shared owed calculation so reminders match Stripe auto-charge logic.
    """
    summary = calculate_entity_owed(
        pending_invoices=_per_invoice_amounts(pending_invoices),
        completed_balances=all_balances,
        convert_amount=convert_amount,
    )
    if not summary.minimum_topup_currency or not summary.minimum_topup_amount:
        return {}
    return {
        summary.minimum_topup_currency: summary.minimum_topup_amount.quantize(
            Decimal("0.01")
        )
    }


def _build_reminder_message(
    negative_balances: dict[str, Decimal],
    pending_invoices: list[Invoice],
    all_balances: dict[str, Decimal],
    entity_name: str,
    convert_amount,
) -> str:
    lines: list[str] = [f"{random.choice(_GREETINGS)}, <b>{entity_name}</b>."]

    topup = _calc_recommended_topup(pending_invoices, all_balances, convert_amount)
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
    currency_exchange_service: "CurrencyExchangeService",
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

    def _convert_amount(
        amount: Decimal, source_currency: str, target_currency: str
    ) -> Decimal:
        source = str(source_currency or "").lower().strip()
        target = str(target_currency or "").lower().strip()
        decimal_amount = Decimal(str(amount or "0"))
        if decimal_amount == 0:
            return Decimal("0")
        if source == target:
            return decimal_amount
        try:
            _, target_amount, _ = currency_exchange_service.calculate_conversion(
                source_amount=decimal_amount,
                target_amount=None,
                source_currency=source,
                target_currency=target,
            )
            return Decimal(str(target_amount))
        except Exception:
            return decimal_amount

    message = _build_reminder_message(
        negative_balances,
        pending_invoices,
        all_balances={
            currency: cd.value
            for currency, cd in balance.completed.items()
            if cd.value != Decimal(0)
        },
        entity_name=entity.name,
        convert_amount=_convert_amount,
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
    currency_exchange_service: "CurrencyExchangeService",
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
            currency_exchange_service=currency_exchange_service,
            notification_service=notification_service,
        )
        if results and any(results.values()):
            sent_count += 1
    return sent_count


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def _seconds_until_next_monday_12_20(now: datetime.datetime) -> float:
    """Return seconds until the next Monday at 12:20 (local time)."""
    days_ahead = (7 - now.weekday()) % 7
    target = datetime.datetime.combine(
        now.date() + datetime.timedelta(days=days_ahead),
        datetime.time(12, 20),
    )
    if target <= now:
        target += datetime.timedelta(weeks=1)
    return (target - now).total_seconds()


class BalanceReminderTask(PeriodicTask):
    def next_delay(self) -> float:
        return _seconds_until_next_monday_12_20(datetime.datetime.now())

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return send_reminders_to_all(
            db=container.db,
            balance_service=container.balance_service,
            currency_exchange_service=container.currency_exchange_service,
            notification_service=NotificationService(config),
        )


def run_balance_reminders() -> int:
    return BalanceReminderTask().run()


async def schedule_balance_reminders() -> None:
    await BalanceReminderTask().schedule()
