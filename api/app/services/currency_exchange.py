"""Currency exchange service"""

import time
from datetime import timedelta
from decimal import Decimal
from typing import TypeVar

import requests
from app.bootstrap import currency_exchange_entity, currency_exchange_tag
from app.db import get_db
from app.models.entity import Entity
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
        db: Session = Depends(get_db),
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

    def calculate(
        self, source_amount: Decimal, source_currency: str, target_currency: str
    ) -> tuple[Decimal, Decimal]:
        """
        Convert an amount from a source currency to a target currency using GEL as the base.

        Parameters:
        amount (str, int, float, or Decimal): The amount in the source currency.
        source_currency (str): The 3-letter code for the source currency (e.g., "AED").
        target_currency (str): The 3-letter code for the target currency (e.g., "AMD").

        Returns:
        Decimal: The converted amount in the target currency.
        """
        currencies = self._raw_rates[0]["currencies"]

        # Helper function to fetch currency info or create default for GEL.
        def get_currency_info(code: str):
            code = code.lower()
            if code == "gel":
                # GEL is the base currency
                return {"rate": Decimal("1"), "quantity": Decimal("1")}
            # Find the currency in the list.
            cur = next((cur for cur in currencies if cur["code"].lower() == code), None)
            if cur is None:
                raise ValueError(f"Currency {code} not found in rates data.")
            return {
                "rate": Decimal(str(cur["rate"])),
                "quantity": Decimal(str(cur["quantity"])),
            }

        # Retrieve source and target currency info.
        source_info = get_currency_info(source_currency)
        target_info = get_currency_info(target_currency)

        # Calculate how many GEL one unit of each currency equals.
        gel_per_source = source_info["rate"] / source_info["quantity"]
        gel_per_target = target_info["rate"] / target_info["quantity"]

        # Conversion rate: number of target currency units per one unit of source currency.
        conversion_rate = gel_per_source / gel_per_target
        reverse_conversion_rate = gel_per_target / gel_per_source

        # Convert the source amount to target currency.
        converted_amount = source_amount * conversion_rate

        # Choose meaningful conversion rate to display, for example 0.01 is a garbage, but 100 is not.
        displayed_conversion_rate = max(conversion_rate, reverse_conversion_rate)
        return round(converted_amount, 2), round(displayed_conversion_rate, 2)

    def preview(
        self,
        preview: CurrencyExchangePreviewRequestSchema,
    ) -> CurrencyExchangePreviewResponseSchema:
        amount, rate = self.calculate(
            source_amount=preview.source_amount,
            source_currency=preview.source_currency,
            target_currency=preview.target_currency,
        )
        return CurrencyExchangePreviewResponseSchema.model_construct(
            **preview.model_dump(),
            target_amount=amount,
            rate=rate,
        )

    def exchange(
        self, exchange_request: CurrencyExchangeRequestSchema, actor_entity: Entity
    ) -> CurrencyExchangeReceiptSchema:
        # calculate the amount and rate
        amount, rate = self.calculate(
            source_amount=exchange_request.source_amount,
            source_currency=exchange_request.source_currency,
            target_currency=exchange_request.target_currency,
        )
        # construct a comment
        comment = f"{exchange_request.source_amount} {exchange_request.source_currency.upper()} → {amount} {exchange_request.target_currency.upper()} (rate {rate})"
        # construct inbound and outbound transactions
        source_tx = TransactionCreateSchema(
            from_entity_id=exchange_request.entity_id,
            to_entity_id=currency_exchange_entity.id,
            amount=exchange_request.source_amount,
            currency=exchange_request.source_currency,
            confirmed=True,
        )
        target_tx = TransactionCreateSchema(
            comment=comment,
            from_entity_id=currency_exchange_entity.id,
            to_entity_id=exchange_request.entity_id,
            amount=amount,
            currency=exchange_request.target_currency,
            confirmed=True,
        )
        # create transactions
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
        # return currency exchange receipt
        return CurrencyExchangeReceiptSchema(
            source_currency=exchange_request.source_currency,
            source_amount=exchange_request.source_amount,
            target_currency=exchange_request.target_currency,
            target_amount=amount,
            rate=rate,
            transactions=[
                TransactionSchema.model_validate(source_transaction),
                TransactionSchema.model_validate(target_transaction),
            ],
        )
