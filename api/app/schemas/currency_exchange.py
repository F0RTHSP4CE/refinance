"""DTO for Currency Exchange service"""

from decimal import Decimal

from app.schemas.base import CurrencyDecimal
from app.schemas.entity import EntitySchema
from pydantic import BaseModel

from api.app.schemas.transaction import TransactionSchema


class CurrencyExchangePreviewRequestSchema(BaseModel):
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str


class CurrencyExchangePreviewResponseSchema(BaseModel):
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str
    target_amount: CurrencyDecimal
    rate: CurrencyDecimal


class CurrencyExchangeRequestSchema(BaseModel):
    entity_id: int
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str


class CurrencyExchangeReceiptSchema(BaseModel):
    source_currency: str
    source_amount: CurrencyDecimal
    target_currency: str
    target_amount: CurrencyDecimal
    rate: CurrencyDecimal

    source_transaction: TransactionSchema
    target_transaction: TransactionSchema
