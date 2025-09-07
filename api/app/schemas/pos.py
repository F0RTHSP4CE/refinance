"""Schemas for POS operations."""

from decimal import Decimal

from app.schemas.balance import BalanceSchema
from app.schemas.base import BaseSchema
from app.schemas.entity import EntitySchema
from pydantic import BaseModel


class POSChargeRequest(BaseModel):
    card_hash: str
    amount: Decimal
    currency: str
    to_entity_id: int
    comment: str | None = None


class POSChargeResponse(BaseSchema):
    entity: EntitySchema
    balance: BalanceSchema
