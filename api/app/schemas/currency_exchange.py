"""DTO for Currency Exchange service"""

from app.schemas.base import (
    CurrencyDecimal,
)
from app.schemas.entity import EntitySchema
from pydantic import BaseModel

class CurrencyExchangeSchema(BaseModel):
    entity_id: int
    entity: EntitySchema
    from_currency: str
    to_currency: bool
    amount: CurrencyDecimal
