"""Currency exchange service"""

import math
import time
from datetime import timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Optional, TypeVar

import requests
from app.bootstrap import currency_exchange_entity, currency_exchange_tag
from app.models.entity import Entity
from app.models.transaction import TransactionStatus
from app.schemas.base import CurrencyDecimal
from app.schemas.currency_exchange import (
    CurrencyExchangePreviewRequestSchema,
    CurrencyExchangePreviewResponseSchema,
    CurrencyExchangeReceiptSchema,
    CurrencyExchangeRequestSchema,
)
from app.schemas.transaction import TransactionCreateSchema, TransactionSchema
from app.services.entity import EntityService
from app.services.tag import TagService
from app.services.transaction import TransactionService
from app.uow import get_uow
from cachetools import TTLCache, cached
from fastapi import Depends
from sqlalchemy.orm import Session

D = TypeVar("D", bound=CurrencyDecimal)


class CurrencyExchangeService:
    ttl_cache = TTLCache(
        maxsize=1, ttl=timedelta(hours=1).total_seconds(), timer=time.time
    )

    def __init__(
        self,
        db: Session = Depends(get_uow),
        transaction_service: TransactionService = Depends(),
        entity_service: EntityService = Depends(),
    ):
        self.db = db
        self.transaction_service = transaction_service
        self.entity_service = entity_service

    @property
    @cached(ttl_cache)
    def _raw_rates(self) -> dict:
        r = requests.get(
            "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json"
        )
        assert r.status_code == 200
        return r.json()

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
                TransactionSchema.model_validate(source_transaction),
                TransactionSchema.model_validate(target_transaction),
            ],
        )
