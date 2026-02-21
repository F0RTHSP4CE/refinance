"""Currency exchange service"""

import logging
import threading
import time
from datetime import timedelta
from decimal import ROUND_DOWN, Decimal
from typing import NamedTuple, Optional, TypeVar

import requests
from app.dependencies.services import (
    get_balance_service,
    get_entity_service,
    get_transaction_service,
)
from app.errors.currency_exchange import CurrencyExchangeSourceOrTargetAmountZero
from app.models.entity import Entity
from app.models.transaction import TransactionStatus
from app.schemas.base import CurrencyDecimal
from app.schemas.currency_exchange import (
    AutoBalanceEntityPlanSchema,
    AutoBalanceEntityReceiptSchema,
    AutoBalanceExchangeItemSchema,
    AutoBalancePreviewSchema,
    AutoBalanceRunResultSchema,
    CurrencyExchangePreviewRequestSchema,
    CurrencyExchangePreviewResponseSchema,
    CurrencyExchangeReceiptSchema,
    CurrencyExchangeRequestSchema,
)
from app.schemas.transaction import TransactionCreateSchema, TransactionSchema
from app.seeding import (
    automatic_tag,
    currency_exchange_entity,
    currency_exchange_tag,
    ex_resident_tag,
    member_tag,
    resident_tag,
)
from app.services.balance import BalanceService
from app.services.entity import EntityService
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

D = TypeVar("D", bound=CurrencyDecimal)
logger = logging.getLogger(__name__)


class _ExchangePlanItem(NamedTuple):
    """Internal representation of a single planned exchange."""

    source_currency: str
    source_amount: Decimal
    target_currency: str
    target_amount: Decimal
    rate: Decimal
    # When True the executor must pass target_amount to `exchange()` so the
    # exact debt amount is received without double-rounding loss.
    use_target_amount: bool = False


class CurrencyExchangeService:
    rates_ttl_seconds = timedelta(hours=1).total_seconds()
    rates_request_timeout_seconds: tuple[float, float] = (2.0, 3.0)
    _rates_cache: dict | None = None
    _rates_cached_at: float = 0.0
    _rates_lock = threading.Lock()

    def __init__(
        self,
        db: Session = Depends(get_uow),
        transaction_service: TransactionService = Depends(get_transaction_service),
        entity_service: EntityService = Depends(get_entity_service),
        balance_service: BalanceService = Depends(get_balance_service),
    ):
        self.db = db
        self.transaction_service = transaction_service
        self.entity_service = entity_service
        self.balance_service = balance_service

    @property
    def _raw_rates(self) -> dict:
        now = time.time()
        cached_rates = self.__class__._rates_cache
        cached_at = self.__class__._rates_cached_at
        if cached_rates is not None and now - cached_at < self.rates_ttl_seconds:
            return cached_rates

        with self.__class__._rates_lock:
            now = time.time()
            cached_rates = self.__class__._rates_cache
            cached_at = self.__class__._rates_cached_at
            if cached_rates is not None and now - cached_at < self.rates_ttl_seconds:
                return cached_rates

            try:
                response = requests.get(
                    "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json",
                    timeout=self.rates_request_timeout_seconds,
                )
                response.raise_for_status()
                rates = response.json()
                self.__class__._rates_cache = rates
                self.__class__._rates_cached_at = time.time()
                return rates
            except requests.RequestException:
                if cached_rates is not None:
                    logger.warning(
                        "Currency rates fetch failed, using stale cached rates",
                        exc_info=True,
                    )
                    return cached_rates
                raise

    def calculate_conversion(
        self,
        source_amount: Optional[Decimal],
        target_amount: Optional[Decimal],
        source_currency: str,
        target_currency: str,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Depending on which amount is provided (source or target),
        calculate the missing value using GEL as the base currency.

        Returns a tuple of (computed_source_amount, computed_target_amount, conversion_rate)
        where conversion_rate is the rate for converting one unit of source into target.
        """
        currencies = self._raw_rates[0]["currencies"]

        def get_currency_info(code: str):
            code = code.lower()
            if code == "gel":
                # GEL is the base currency.
                return {"rate": Decimal("1"), "quantity": Decimal("1")}
            cur = next((cur for cur in currencies if cur["code"].lower() == code), None)
            if cur is None:
                raise ValueError(f"Currency {code} not found in rates data.")
            return {
                "rate": Decimal(str(cur["rate"])),
                "quantity": Decimal(str(cur["quantity"])),
            }

        source_info = get_currency_info(source_currency)
        target_info = get_currency_info(target_currency)
        gel_per_source = source_info["rate"] / source_info["quantity"]
        gel_per_target = target_info["rate"] / target_info["quantity"]

        # Conversion rate: how many units of target currency per one unit of source currency.
        conversion_rate = gel_per_source / gel_per_target
        # Calculate a human-readable conversion rate, to avoid rates like 0.1, make it 10 instead.
        reversed_conversion_rate = gel_per_target / gel_per_source
        displayed_conversion_rate = max(conversion_rate, reversed_conversion_rate)

        if source_amount is not None and target_amount is None:
            computed_source = source_amount
            computed_target = source_amount * conversion_rate
        elif target_amount is not None and source_amount is None:
            computed_target = target_amount
            computed_source = target_amount / conversion_rate
        else:
            raise ValueError(
                "Exactly one of source_amount or target_amount must be provided."
            )
        if computed_target <= 0 or computed_source <= 0:
            raise CurrencyExchangeSourceOrTargetAmountZero

        return (
            computed_source.quantize(Decimal("0.01"), rounding=ROUND_DOWN),
            computed_target.quantize(Decimal("0.01"), rounding=ROUND_DOWN),
            displayed_conversion_rate.quantize(Decimal("0.01"), rounding=ROUND_DOWN),
        )

    def preview(
        self,
        preview: CurrencyExchangePreviewRequestSchema,
    ) -> CurrencyExchangePreviewResponseSchema:
        computed_source, computed_target, rate = self.calculate_conversion(
            source_amount=preview.source_amount,
            target_amount=preview.target_amount,
            source_currency=preview.source_currency,
            target_currency=preview.target_currency,
        )
        if computed_target <= 0 or computed_source <= 0:
            raise CurrencyExchangeSourceOrTargetAmountZero

        data = preview.model_dump()
        # Remove the existing amount fields to avoid duplicates.
        data.pop("source_amount", None)
        data.pop("target_amount", None)
        data.update(
            {
                "source_amount": computed_source,
                "target_amount": computed_target,
                "rate": rate,
            }
        )
        return CurrencyExchangePreviewResponseSchema.model_construct(**data)

    def exchange(
        self, exchange_request: CurrencyExchangeRequestSchema, actor_entity: Entity
    ) -> CurrencyExchangeReceiptSchema:
        computed_source, computed_target, rate = self.calculate_conversion(
            source_amount=exchange_request.source_amount,
            target_amount=exchange_request.target_amount,
            source_currency=exchange_request.source_currency,
            target_currency=exchange_request.target_currency,
        )
        comment = (
            f"{computed_source} {exchange_request.source_currency.upper()} → "
            f"{computed_target} {exchange_request.target_currency.upper()} (rate {rate})"
        )
        source_tx = TransactionCreateSchema(
            comment=comment,
            from_entity_id=exchange_request.entity_id,
            to_entity_id=currency_exchange_entity.id,
            amount=computed_source,
            currency=exchange_request.source_currency,
            status=TransactionStatus.COMPLETED,
        )
        target_tx = TransactionCreateSchema(
            comment=comment,
            from_entity_id=currency_exchange_entity.id,
            to_entity_id=exchange_request.entity_id,
            amount=computed_target,
            currency=exchange_request.target_currency,
            status=TransactionStatus.COMPLETED,
        )
        source_transaction = self.transaction_service.create(
            source_tx, overrides={"actor_entity_id": actor_entity.id}
        )
        target_transaction = self.transaction_service.create(
            target_tx, overrides={"actor_entity_id": actor_entity.id}
        )
        self.transaction_service.add_tag(
            source_transaction.id, currency_exchange_tag.id
        )
        self.transaction_service.add_tag(
            target_transaction.id, currency_exchange_tag.id
        )
        return CurrencyExchangeReceiptSchema(
            source_currency=exchange_request.source_currency,
            source_amount=computed_source,
            target_currency=exchange_request.target_currency,
            target_amount=computed_target,
            rate=rate,
            transactions=[
                TransactionSchema.model_validate(target_transaction),
                TransactionSchema.model_validate(source_transaction),
            ],
        )

    # ------------------------------------------------------------------ #
    # Auto-balance helpers                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cd_to_decimal(value) -> Decimal:
        """Convert a CurrencyDecimal (or any numeric) to plain Decimal."""
        if isinstance(value, CurrencyDecimal):
            return value.to_decimal()
        return Decimal(str(value))

    def _to_usd(self, currency: str, amount: Decimal) -> Decimal:
        """Return the USD-equivalent value of *amount* in *currency*."""
        if currency.lower() == "usd":
            return amount
        try:
            _, usd_amount, _ = self.calculate_conversion(
                source_amount=amount,
                target_amount=None,
                source_currency=currency,
                target_currency="usd",
            )
            return usd_amount
        except Exception:
            return amount  # fallback: treat as USD to stay safe

    def _plan_exchanges(self, balances: dict[str, Decimal]) -> list[_ExchangePlanItem]:
        """Compute the minimal sequence of exchanges needed to eliminate all negative
        balances using the available positive ones.

        Positive currencies are consumed starting from the one with the lowest
        USD-equivalent value (smallest first).  The largest debt (by USD value)
        is targeted first in each round.
        """
        ZERO = Decimal("0")
        remaining = {c: Decimal(str(a)) for c, a in balances.items()}
        result: list[_ExchangePlanItem] = []

        for _ in range(500):  # safety cap
            debts = {c: abs(a) for c, a in remaining.items() if a < ZERO}
            positives = {c: a for c, a in remaining.items() if a > ZERO}

            if not debts or not positives:
                break

            # Smallest positive currency first (by USD value)
            sorted_positives = sorted(
                positives.items(),
                key=lambda item: self._to_usd(item[0], item[1]),
            )
            source_currency, source_avail = sorted_positives[0]

            # Largest debt first (by USD value)
            sorted_debts = sorted(
                debts.items(),
                key=lambda item: self._to_usd(item[0], item[1]),
                reverse=True,
            )

            exchange_happened = False
            for debt_currency, debt_needed in sorted_debts:
                if debt_currency == source_currency:
                    continue

                # How much source do we need to cover the full debt?
                try:
                    needed_src, _, rate = self.calculate_conversion(
                        source_amount=None,
                        target_amount=debt_needed,
                        source_currency=source_currency,
                        target_currency=debt_currency,
                    )
                except Exception:
                    continue

                if source_avail >= needed_src:
                    # Full coverage: use target_amount in the actual exchange so
                    # the debt is covered exactly (avoids double ROUND_DOWN).
                    plan_src = needed_src
                    plan_tgt = debt_needed
                    use_target = True
                else:
                    # Partial coverage: spend all available source.
                    plan_src = source_avail
                    try:
                        _, plan_tgt, rate = self.calculate_conversion(
                            source_amount=plan_src,
                            target_amount=None,
                            source_currency=source_currency,
                            target_currency=debt_currency,
                        )
                    except Exception:
                        continue
                    use_target = False

                if plan_src <= ZERO or plan_tgt <= ZERO:
                    continue

                result.append(
                    _ExchangePlanItem(
                        source_currency=source_currency,
                        source_amount=plan_src,
                        target_currency=debt_currency,
                        target_amount=plan_tgt,
                        rate=rate,
                        use_target_amount=use_target,
                    )
                )

                remaining[source_currency] = (
                    remaining.get(source_currency, ZERO) - plan_src
                )
                remaining[debt_currency] = remaining.get(debt_currency, ZERO) + plan_tgt
                exchange_happened = True
                break  # re-evaluate sort order after each exchange

            if not exchange_happened:
                break

        return result

    def _get_eligible_entities(self) -> list[Entity]:
        """Return active entities tagged as resident, member, or ex-resident."""
        target_tag_ids = [resident_tag.id, member_tag.id, ex_resident_tag.id]
        return (
            self.db.query(Entity)
            .filter(Entity.active == True)  # noqa: E712
            .filter(or_(*[Entity.tags.any(id=tid) for tid in target_tag_ids]))
            .all()
        )

    def compute_auto_balance_plan_for_entity(
        self, entity_id: int
    ) -> AutoBalanceEntityPlanSchema:
        """Compute what exchanges would be needed to cover all debts for *entity_id*."""
        entity = self.entity_service.get(entity_id)
        balances_schema = self.balance_service.get_balances(entity_id)
        completed = {
            c.lower(): self._cd_to_decimal(a)
            for c, a in (balances_schema.completed or {}).items()
        }
        plan = self._plan_exchanges(completed)
        return AutoBalanceEntityPlanSchema(
            entity_id=entity_id,
            entity_name=entity.name,
            exchanges=[
                AutoBalanceExchangeItemSchema(
                    source_currency=p.source_currency,
                    source_amount=p.source_amount,
                    target_currency=p.target_currency,
                    target_amount=p.target_amount,
                    rate=p.rate,
                )
                for p in plan
            ],
        )

    def compute_auto_balance_plan_for_all(self) -> AutoBalancePreviewSchema:
        """Compute auto-balance plans for all eligible entities."""
        entities = self._get_eligible_entities()
        plans = []
        for entity in entities:
            plan = self.compute_auto_balance_plan_for_entity(entity.id)
            if plan.exchanges:
                plans.append(plan)
        return AutoBalancePreviewSchema(plans=plans)

    def run_auto_balance_for_entity(
        self, entity_id: int, actor_entity: Entity
    ) -> AutoBalanceEntityReceiptSchema:
        """Execute auto-balance exchanges for *entity_id*."""
        entity = self.entity_service.get(entity_id)
        balances_schema = self.balance_service.get_balances(entity_id)
        completed = {
            c.lower(): self._cd_to_decimal(a)
            for c, a in (balances_schema.completed or {}).items()
        }
        plan = self._plan_exchanges(completed)
        receipts = []
        for item in plan:
            if item.use_target_amount:
                exchange_req = CurrencyExchangeRequestSchema(
                    entity_id=entity_id,
                    source_currency=item.source_currency,
                    target_currency=item.target_currency,
                    target_amount=item.target_amount,
                )
            else:
                exchange_req = CurrencyExchangeRequestSchema(
                    entity_id=entity_id,
                    source_currency=item.source_currency,
                    source_amount=item.source_amount,
                    target_currency=item.target_currency,
                )
            receipt = self.exchange(exchange_req, actor_entity)
            # Mark both transactions as automatic and refresh for the response
            refreshed_txs = []
            for tx in receipt.transactions:
                try:
                    self.transaction_service.add_tag(tx.id, automatic_tag.id)
                except Exception:
                    pass
                refreshed_txs.append(
                    TransactionSchema.model_validate(
                        self.transaction_service.get(tx.id)
                    )
                )
            receipt = CurrencyExchangeReceiptSchema(
                source_currency=receipt.source_currency,
                source_amount=receipt.source_amount,
                target_currency=receipt.target_currency,
                target_amount=receipt.target_amount,
                rate=receipt.rate,
                transactions=refreshed_txs,
            )
            receipts.append(receipt)
            # Invalidate balance cache so next iteration sees fresh data
            self.balance_service.invalidate_cache_entry(entity_id)
        return AutoBalanceEntityReceiptSchema(
            entity_id=entity_id,
            entity_name=entity.name,
            receipts=receipts,
        )

    def run_auto_balance_for_all(
        self, actor_entity: Entity
    ) -> AutoBalanceRunResultSchema:
        """Execute auto-balance exchanges for all eligible entities."""
        entities = self._get_eligible_entities()
        results = []
        for entity in entities:
            try:
                receipt = self.run_auto_balance_for_entity(entity.id, actor_entity)
                if receipt.receipts:
                    results.append(receipt)
            except Exception:
                logger.exception(
                    "Auto-balance failed for entity id=%s", entity.id, exc_info=True
                )
        return AutoBalanceRunResultSchema(results=results)
