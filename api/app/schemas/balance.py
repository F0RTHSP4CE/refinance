"""DTO for Balance"""

from decimal import Decimal

from app.schemas.base import BaseSchema, CurrencyDecimal


class BalanceSchema(BaseSchema):
    completed: dict[str, CurrencyDecimal]
    draft: dict[str, CurrencyDecimal]
