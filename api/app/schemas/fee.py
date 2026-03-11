"""DTOs for fees"""

from app.schemas.base import BaseSchema, CurrencyDecimal
from app.schemas.entity import EntitySchema


class MonthlyFeeSchema(BaseSchema):
    year: int
    month: int
    amounts: dict[str, CurrencyDecimal]
    total_usd: float
    unpaid_invoice_id: int | None = None
    paid_invoice_id: int | None = None
    unpaid_invoice_amounts: dict[str, CurrencyDecimal] | None = None


class FeeSchema(BaseSchema):
    entity: EntitySchema
    fees: list[MonthlyFeeSchema]


class FeeFiltersSchema(BaseSchema):
    months: int = 12


class FeeAmountSchema(BaseSchema):
    tag_id: int
    currency: str
    amount: CurrencyDecimal
