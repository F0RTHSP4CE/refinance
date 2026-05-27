"""Unified entity owed/top-up calculation shared by reminder and Stripe charging."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_UP, Decimal
from typing import Callable, Iterable, Mapping


@dataclass(frozen=True)
class EntityOwedSummary:
    owed_by_currency: dict[str, Decimal]
    total_owed_usd: Decimal
    available_credit_usd: Decimal
    net_owed_usd: Decimal
    minimum_topup_currency: str | None
    minimum_topup_amount: Decimal | None


def _normalize_currency_amounts(values: Mapping[str, Decimal]) -> dict[str, Decimal]:
    normalized: dict[str, Decimal] = {}
    for currency, amount in values.items():
        code = str(currency or "").lower().strip()
        if not code:
            continue
        normalized[code] = normalized.get(code, Decimal("0")) + Decimal(
            str(amount or "0")
        )
    return normalized


def calculate_entity_owed(
    *,
    pending_invoice_totals: Mapping[str, Decimal],
    completed_balances: Mapping[str, Decimal],
    convert_amount: Callable[[Decimal, str, str], Decimal],
    currency_candidates: Iterable[str] | None = None,
) -> EntityOwedSummary:
    """Calculate owed amounts and minimal top-up recommendation.

    Owed side per currency = unpaid invoices + absolute value of negative balances.
    All positive balances in any currency are converted to USD and counted as
    available credit, so a currency exchange can substitute for a Stripe charge.
    """
    invoice_totals = _normalize_currency_amounts(pending_invoice_totals)
    balances = _normalize_currency_amounts(completed_balances)

    owed_by_currency: dict[str, Decimal] = dict(invoice_totals)
    for currency, balance in balances.items():
        if balance < 0:
            owed_by_currency[currency] = owed_by_currency.get(
                currency, Decimal("0")
            ) + abs(balance)

    total_owed_usd = Decimal("0")
    for currency, amount in owed_by_currency.items():
        if amount > 0:
            total_owed_usd += Decimal(str(convert_amount(amount, currency, "usd")))

    available_credit_usd = Decimal("0")
    for currency, balance in balances.items():
        if balance > 0:
            available_credit_usd += Decimal(
                str(convert_amount(balance, currency, "usd"))
            )

    net_owed_usd = (total_owed_usd - available_credit_usd).quantize(Decimal("0.01"))
    if net_owed_usd <= 0:
        return EntityOwedSummary(
            owed_by_currency=owed_by_currency,
            total_owed_usd=total_owed_usd,
            available_credit_usd=available_credit_usd,
            net_owed_usd=Decimal("0.00"),
            minimum_topup_currency=None,
            minimum_topup_amount=None,
        )

    candidate_set = {
        str(currency or "").lower().strip()
        for currency in (currency_candidates or [])
        if str(currency or "").strip()
    }
    if not candidate_set:
        candidate_set = set(owed_by_currency.keys()) or {"usd"}

    options: list[tuple[Decimal, str]] = []
    for currency in sorted(candidate_set):
        try:
            amount = Decimal(
                str(convert_amount(net_owed_usd, "usd", currency))
            ).quantize(Decimal("0.01"), rounding=ROUND_UP)
        except Exception:
            continue
        if amount > 0:
            options.append((amount, currency))

    if not options:
        return EntityOwedSummary(
            owed_by_currency=owed_by_currency,
            total_owed_usd=total_owed_usd,
            available_credit_usd=available_credit_usd,
            net_owed_usd=net_owed_usd,
            minimum_topup_currency="usd",
            minimum_topup_amount=net_owed_usd,
        )

    minimum_topup_amount, minimum_topup_currency = min(
        options, key=lambda item: (item[0], item[1])
    )
    return EntityOwedSummary(
        owed_by_currency=owed_by_currency,
        total_owed_usd=total_owed_usd,
        available_credit_usd=available_credit_usd,
        net_owed_usd=net_owed_usd,
        minimum_topup_currency=minimum_topup_currency,
        minimum_topup_amount=minimum_topup_amount,
    )
