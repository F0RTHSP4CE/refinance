"""DTOs for fees"""

from datetime import date

from app.schemas.base import BaseSchema, CurrencyDecimal
from app.schemas.entity import EntitySchema


class MonthlyFeeSchema(BaseSchema):
    year: int
    month: int
    amounts: dict[str, CurrencyDecimal]
    total_usd: float


class FeeSchema(BaseSchema):
    entity: EntitySchema
    fees: list[MonthlyFeeSchema]


class FeeFiltersSchema(BaseSchema):
    months: int = 12


class FeeAmountSchema(BaseSchema):
    tag_id: int
    currency: str
    amount: CurrencyDecimal


class FeeInvoiceIssueSchema(BaseSchema):
    billing_period: date | None = None


class FeeInvoiceIssueReportSchema(BaseSchema):
    billing_period: date
    created_count: int
    skipped_count: int
    invoice_ids: list[int]
