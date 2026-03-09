"""DTOs for fees"""

from datetime import date

from app.schemas.base import BaseSchema, CurrencyDecimal
from app.schemas.entity import EntitySchema
from pydantic import field_validator, model_validator


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
    from_period: date | None = None
    to_period: date | None = None
    include_empty_entities: bool = False
    include_empty_months: bool = False

    @field_validator("from_period", "to_period")
    @classmethod
    def normalize_period(cls, value: date | None) -> date | None:
        if value is None:
            return None
        return date(value.year, value.month, 1)

    @model_validator(mode="after")
    def validate_range(self) -> "FeeFiltersSchema":
        if self.from_period and self.to_period and self.from_period > self.to_period:
            raise ValueError("from_period must be before or equal to to_period")
        return self


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
