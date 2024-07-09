"""DTO for Balance"""

from decimal import Decimal

from app.schemas.base import BaseSchema


class BalanceSchema(BaseSchema):
    confirmed: dict[str, Decimal]
    non_confirmed: dict[str, Decimal]
