"""DTO for Balance"""

from app.schemas.base import BaseSchema, CurrencyDecimal


class BalanceSchema(BaseSchema):
    completed: dict[str, CurrencyDecimal]
    draft: dict[str, CurrencyDecimal]


class RecommendedDepositSchema(BaseSchema):
    entity_id: int
    currency: str | None = None
    amount: CurrencyDecimal | None = None
