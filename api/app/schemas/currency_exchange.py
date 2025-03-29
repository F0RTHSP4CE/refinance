"""DTO for Currency Exchange service"""

from decimal import Decimal

from app.schemas.base import BaseSchema, CurrencyDecimal
from app.schemas.transaction import TransactionSchema


class CurrencyExchangePreviewRequestSchema(BaseSchema):
    entity_id: int
    source_currency: str
    source_amount: Decimal
    target_currency: str


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
    source_amount: Decimal
    target_currency: str


class CurrencyExchangeReceiptSchema(BaseSchema):
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str
    target_amount: CurrencyDecimal
    rate: CurrencyDecimal

    transactions: list[TransactionSchema]
