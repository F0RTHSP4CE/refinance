"""Unified entity owed/top-up calculation shared by reminder and Stripe charging."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_UP, Decimal
from typing import TYPE_CHECKING, Callable, Iterable, Mapping

import requests
from app.models.invoice import Invoice, InvoiceStatus
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.balance import BalanceService
    from app.services.currency_exchange import CurrencyExchangeService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntityOwedSummary:
    owed_by_currency: dict[str, Decimal]
    total_owed_usd: Decimal
    available_credit_usd: Decimal
    net_owed_usd: Decimal
    minimum_topup_currency: str | None
    minimum_topup_amount: Decimal | None


def invoice_currency_options(invoice: Invoice) -> dict[str, Decimal]:
    """Return an invoice's alternative whole-invoice payment totals.

    Legacy invoices keep their alternatives on ``Invoice.amounts``. For a
    multi-recipient invoice, each item's amount in a currency must be paid, so
    item amounts are summed while currencies remain alternatives.
    """
    amount_groups = (
        [item.amounts or [] for item in invoice.items]
        if invoice.items
        else [invoice.amounts or []]
    )
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
    pending_invoices: list[Mapping[str, Decimal]],
    completed_balances: Mapping[str, Decimal],
    convert_amount: Callable[[Decimal, str, str], Decimal],
    currency_candidates: Iterable[str] | None = None,
) -> EntityOwedSummary:
    """Calculate owed amounts and minimal top-up recommendation.

    Each element of ``pending_invoices`` is one invoice represented as a
    ``{currency: amount}`` mapping of alternative payment options.  Paying in
    *any* of those currencies satisfies that invoice, so only the cheapest
    option (by USD equivalent) is counted toward the total owed.

    Owed side per currency = (min-USD option for each invoice) + absolute value
    of negative balances.  All positive balances in any currency are converted
    to USD and counted as available credit so a currency exchange can substitute
    for a Stripe charge.
    """
    balances = _normalize_currency_amounts(completed_balances)

    owed_by_currency: dict[str, Decimal] = {}

    # For each invoice pick the currency option whose USD equivalent is lowest.
    for invoice_options in pending_invoices:
        normalized = _normalize_currency_amounts(invoice_options)
        best_currency: str | None = None
        best_usd: Decimal | None = None
        best_amount: Decimal | None = None
        for currency, amount in sorted(normalized.items()):
            if amount <= 0:
                continue
            try:
                usd_val = Decimal(str(convert_amount(amount, currency, "usd")))
            except Exception:
                continue
            if best_usd is None or usd_val < best_usd:
                best_usd = usd_val
                best_currency = currency
                best_amount = amount
        if best_currency is not None and best_amount is not None:
            owed_by_currency[best_currency] = (
                owed_by_currency.get(best_currency, Decimal("0")) + best_amount
            )

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


def calculate_same_currency_invoice_topup(
    *,
    pending_invoices: list[Mapping[str, Decimal]],
    completed_balances: Mapping[str, Decimal],
) -> tuple[str | None, Decimal | None]:
    """Return a deposit that makes every pending invoice payable in one currency.

    This deliberately performs no currency conversion. It is a safe degraded
    recommendation for a temporary exchange-rate outage: unlike a guessed FX
    rate, the result always makes the invoices payable in the returned currency.
    """
    if not pending_invoices:
        return None, None

    normalized_invoices = [
        _normalize_currency_amounts(options) for options in pending_invoices
    ]
    common_currencies = set(normalized_invoices[0])
    for options in normalized_invoices[1:]:
        common_currencies.intersection_update(options)
    balances = _normalize_currency_amounts(completed_balances)

    candidates: list[tuple[Decimal, str]] = []
    for currency in sorted(common_currencies):
        invoice_total = sum(
            (options[currency] for options in normalized_invoices), Decimal("0")
        )
        shortfall = (invoice_total - balances.get(currency, Decimal("0"))).quantize(
            Decimal("0.01"), rounding=ROUND_UP
        )
        if shortfall > 0:
            candidates.append((shortfall, currency))

    if not candidates:
        return None, None
    amount, currency = min(candidates, key=lambda item: (item[0], item[1]))
    return currency, amount


class EntityOwedService:
    """Load an entity's invoices and balances and calculate its total debt."""

    def __init__(
        self,
        db: Session,
        balance_service: "BalanceService",
        currency_exchange_service: "CurrencyExchangeService",
    ) -> None:
        self.db = db
        self.balance_service = balance_service
        self.currency_exchange_service = currency_exchange_service

    def _load_inputs(
        self, entity_id: int
    ) -> tuple[list[dict[str, Decimal]], dict[str, Decimal]]:
        pending_invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.from_entity_id == entity_id,
                Invoice.status == InvoiceStatus.PENDING,
            )
            .all()
        )
        invoice_options = [
            options
            for invoice in pending_invoices
            if (options := invoice_currency_options(invoice))
        ]

        balance = self.balance_service.get_balances(entity_id)
        completed_balances = {
            str(currency or "").lower().strip(): amount.value
            for currency, amount in balance.completed.items()
            if str(currency or "").strip()
        }
        return invoice_options, completed_balances

    def calculate(self, entity_id: int) -> EntityOwedSummary:
        invoice_options, completed_balances = self._load_inputs(entity_id)
        return calculate_entity_owed(
            pending_invoices=invoice_options,
            completed_balances=completed_balances,
            convert_amount=self._convert_amount,
        )

    def recommended_deposit(self, entity_id: int) -> tuple[str | None, Decimal | None]:
        invoice_options, completed_balances = self._load_inputs(entity_id)
        conversion_error: requests.RequestException | None = None

        def convert_with_outage_tracking(
            amount: Decimal, source_currency: str, target_currency: str
        ) -> Decimal:
            nonlocal conversion_error
            try:
                return self._convert_amount(amount, source_currency, target_currency)
            except requests.RequestException as exc:
                conversion_error = exc
                raise

        try:
            summary = calculate_entity_owed(
                pending_invoices=invoice_options,
                completed_balances=completed_balances,
                convert_amount=convert_with_outage_tracking,
            )
            if conversion_error is not None:
                raise conversion_error
            return (
                summary.minimum_topup_currency,
                self._round_recommended_deposit(summary.minimum_topup_amount),
            )
        except requests.RequestException as exc:
            logger.warning(
                "Currency rates unavailable for entity %s; using same-currency "
                "invoice shortfall: %s",
                entity_id,
                exc,
            )
            currency, amount = calculate_same_currency_invoice_topup(
                pending_invoices=invoice_options,
                completed_balances=completed_balances,
            )
            return currency, self._round_recommended_deposit(amount)

    @staticmethod
    def _round_recommended_deposit(amount: Decimal | None) -> Decimal | None:
        if amount is None:
            return None
        return amount.to_integral_value(rounding=ROUND_CEILING)

    def _convert_amount(
        self, amount: Decimal, source_currency: str, target_currency: str
    ) -> Decimal:
        source = str(source_currency or "").lower().strip()
        target = str(target_currency or "").lower().strip()
        decimal_amount = Decimal(str(amount or "0"))
        if decimal_amount == 0 or source == target:
            return decimal_amount
        _, target_amount, _ = self.currency_exchange_service.calculate_conversion(
            source_amount=decimal_amount,
            target_amount=None,
            source_currency=source,
            target_currency=target,
        )
        return Decimal(str(target_amount))
