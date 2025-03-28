"""Currency exchange service"""

import time
from datetime import timedelta
from decimal import Decimal
from typing import TypeVar

import requests
from app.db import get_db
from app.models.entity import Entity
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreateSchema,
    TransactionFiltersSchema,
    TransactionSchema,
    TransactionUpdateSchema,
)
from app.services.base import BaseService
from cachetools import TTLCache, cached
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from api.app.schemas.base import CurrencyDecimal
from api.app.schemas.currency_exchange import (
    CurrencyExchangePreviewRequestSchema,
    CurrencyExchangePreviewResponseSchema,
    CurrencyExchangeReceiptSchema,
    CurrencyExchangeRequestSchema,
)
from api.app.services.transaction import TransactionService

D = TypeVar("D", bound=CurrencyDecimal)


class CurrencyExchangeService:
    ttl_cache = TTLCache(
        maxsize=1, ttl=timedelta(hours=1).total_seconds(), timer=time.time
    )

    def __init__(
        self,
        db: Session = Depends(get_db),
        transaction_service: TransactionService = Depends(),
    ):
        self.db = db
        self._transaction_service = transaction_service

    @property
    @cached(ttl_cache)
    def _raw_rates(self) -> dict:
        r = requests.get(
            "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json"
        )
        assert r.status_code == 200
        return r.json()

    def convert(
        self, source_amount: CurrencyDecimal, source_currency, target_currency
    ) -> tuple[CurrencyDecimal, CurrencyDecimal]:
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

        # Find the source and target currency entries
        source_currency = next(
            (cur for cur in currencies if cur["code"] == source_currency), None
        )
        target_currency = next(
            (cur for cur in currencies if cur["code"] == target_currency), None
        )

        if source_currency is None or target_currency is None:
            raise ValueError("Source or target currency not found in rates data.")

        # Convert to Decimal for precision.
        # The rate represents the amount in GEL for the given quantity of the currency.
        source_rate = Decimal(str(source_currency["rate"]))
        source_quantity = Decimal(str(source_currency["quantity"]))
        target_rate = Decimal(str(target_currency["rate"]))
        target_quantity = Decimal(str(target_currency["quantity"]))

        # Calculate GEL equivalent for one unit of each currency.
        gel_per_source = source_rate / source_quantity
        gel_per_target = target_rate / target_quantity

        # Conversion rate: number of target currency units per one source currency unit.
        conversion_rate = gel_per_source / gel_per_target

        # Convert the source amount to target currency.
        converted_amount = source_amount.to_decimal() * conversion_rate

        return CurrencyDecimal(converted_amount), CurrencyDecimal(conversion_rate)

    def preview(
        self, preview: CurrencyExchangePreviewRequestSchema
    ) -> CurrencyExchangePreviewResponseSchema:
        amount, rate = self.convert(
            source_amount=preview.source_amount,
            source_currency=preview.source_currency,
            target_currency=preview.target_currency,
        )
        return CurrencyExchangePreviewResponseSchema(
            **preview.model_dump(),
            target_amount=amount,
            rate=rate,
        )

    def exchange(
        self, exchange_request: CurrencyExchangeRequestSchema
    ) -> CurrencyExchangeReceiptSchema:
        # calculate the amount and rate
        amount, rate = self.convert(
            source_amount=exchange_request.source_amount,
            source_currency=exchange_request.source_currency,
            target_currency=exchange_request.target_currency,
        )
        # construct a comment
        comment = f"exchange {exchange_request.source_amount} {exchange_request.source_currency} -> {amount} {exchange_request.target_currency} (rate {rate})"
        # construct inbound and outbound transactions
        source_tx = TransactionCreateSchema(
            comment=comment,
            from_entity_id=exchange_request.entity_id,
            to_entity_id=CURRENCY_EXCHANGE_ENTITY.id,
            amount=exchange_request.source_amount,
            currency=exchange_request.source_currency,
            confirmed=True,
        )
        target_tx = TransactionCreateSchema(
            comment=comment,
            from_entity_id=CURRENCY_EXCHANGE_ENTITY.id,
            to_entity_id=exchange_request.entity_id,
            amount=amount,
            currency=exchange_request.target_currency,
            confirmed=True,
        )
        # create transactions
        source_transaction = self._transaction_service.create(source_tx)
        target_transaction = self._transaction_service.create(target_tx)
        self._transaction_service.add_tag(
            source_transaction.id, CURRENCY_EXCHANGE_TAG.id
        )
        self._transaction_service.add_tag(
            target_transaction.id, CURRENCY_EXCHANGE_TAG.id
        )
        # return currency exchange receipt
        return CurrencyExchangeReceiptSchema(
            source_currency=exchange_request.source_currency,
            source_amount=exchange_request.source_amount,
            target_currency=exchange_request.target_currency,
            target_amount=amount,
            rate=rate,
            source_transaction=TransactionSchema.model_validate(source_transaction),
            target_transaction=TransactionSchema.model_validate(target_transaction),
        )
