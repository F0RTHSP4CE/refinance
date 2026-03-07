"""DTO for Currency Exchange service"""

from decimal import Decimal
from typing import Optional

from app.schemas.base import BaseSchema, CurrencyDecimal
from app.schemas.transaction import TransactionSchema
from pydantic import field_validator, model_validator


class CurrencyExchangePreviewRequestSchema(BaseSchema):
    entity_id: int
    source_currency: str
    source_amount: Optional[Decimal] = None
    target_currency: str
    target_amount: Optional[Decimal] = None

    @field_validator("source_amount", "target_amount")
    def amount_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @model_validator(mode="after")
    def check_amounts(self) -> "CurrencyExchangePreviewRequestSchema":
        if (self.source_amount is None and self.target_amount is None) or (
            self.source_amount is not None and self.target_amount is not None
        ):
            raise ValueError(
                "Either source_amount or target_amount must be provided. But not both."
            )
        return self


class CurrencyExchangePreviewResponseSchema(BaseSchema):
    entity_id: int
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str
    target_amount: CurrencyDecimal
    rate: CurrencyDecimal


class CurrencyExchangeRequestSchema(BaseSchema):
    entity_id: int
    source_currency: str
    source_amount: Optional[Decimal] = None
    target_currency: str
    target_amount: Optional[Decimal] = None

    @field_validator("source_amount", "target_amount")
    def amount_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @model_validator(mode="after")
    def check_amounts(self) -> "CurrencyExchangeRequestSchema":
        if (self.source_amount is None and self.target_amount is None) or (
            self.source_amount is not None and self.target_amount is not None
        ):
            raise ValueError(
                "Either source_amount or target_amount must be provided. But not both."
            )
        return self


class CurrencyExchangeReceiptSchema(BaseSchema):
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str
    target_amount: CurrencyDecimal
    rate: CurrencyDecimal
    transactions: list[TransactionSchema]


class AutoBalanceExchangeItemSchema(BaseSchema):
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str
    target_amount: CurrencyDecimal
    rate: CurrencyDecimal


class AutoBalanceEntityPlanSchema(BaseSchema):
    entity_id: int
    entity_name: str
    exchanges: list[AutoBalanceExchangeItemSchema]


class AutoBalancePreviewSchema(BaseSchema):
    plans: list[AutoBalanceEntityPlanSchema]


class AutoBalanceEntityReceiptSchema(BaseSchema):
    entity_id: int
    entity_name: str
    receipts: list[CurrencyExchangeReceiptSchema]


class AutoBalanceRunResultSchema(BaseSchema):
    results: list[AutoBalanceEntityReceiptSchema]
