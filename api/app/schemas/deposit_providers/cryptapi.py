"""DTO for CryptAPI Deposit Provider"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator


class CryptAPIDepositCreateSchema(BaseModel):
    to_entity_id: int
    amount: Decimal
    coin: Literal["trc20/usdt"] | Literal["erc20/usdt"]

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v > 0:
            return v
        raise ValueError("Amount must be greater than 0")


# https://docs.cryptapi.io/#operation/confirmedcallbackget
class CryptAPICallbackSchema(BaseModel):
    address_in: str
    address_out: str
    txid_in: str
    txid_out: str
    confirmations: int
    value_coin: Decimal
    value_forwarded_coin: Decimal
    fee_coin: Decimal
    coin: str
    price: Decimal
    pending: int
