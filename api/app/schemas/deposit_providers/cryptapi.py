"""DTO for CryptAPI Deposit Provider"""

from decimal import Decimal

from pydantic import BaseModel


class CryptAPIDepositCreateSchema(BaseModel):
    to_entity_id: int
    amount: Decimal
    coin: str


# https://docs.cryptapi.io/#operation/confirmedcallbackget
class CryptAPICallbackSchema(BaseModel):
    address_in: str | None = None
    address_out: str | None = None
    txid_in: str | None = None
    txid_out: str | None = None
    confirmations: int | None = None
    value_coin: Decimal | None = None
    value_forwarded_coin: Decimal | None = None
    fee_coin: Decimal | None = None
    coin: str | None = None
    price: Decimal | None = None
    pending: int | None = None
