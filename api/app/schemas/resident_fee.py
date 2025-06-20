"""DTO for ResidentFee"""

from app.schemas.base import BaseSchema, CurrencyDecimal
from app.schemas.entity import EntitySchema


class MonthlyFeeSchema(BaseSchema):
    year: int
    month: int
    amounts: dict[str, CurrencyDecimal]


class ResidentFeeSchema(BaseSchema):
    entity: EntitySchema
    fees: list[MonthlyFeeSchema]


class ResidentFeeFiltersSchema(BaseSchema):
    months: int = 12
