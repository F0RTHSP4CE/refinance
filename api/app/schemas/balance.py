"""DTO for Balance"""

from decimal import Decimal

from app.schemas.base import BaseSchema, CurrencyDecimal


class BalanceSchema(BaseSchema):
    confirmed: dict[str, CurrencyDecimal]
    non_confirmed: dict[str, CurrencyDecimal]
