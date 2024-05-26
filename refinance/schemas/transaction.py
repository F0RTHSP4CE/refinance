"""DTO for Transaction"""

from decimal import Decimal

from pydantic import field_validator, model_validator

from refinance.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema
from refinance.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from refinance.schemas.tag import TagSchema


class TransactionSchema(BaseReadSchema):
    to_id: int
    from_id: int
    amount: Decimal
    currency: str
    confirmed: bool
    tags: list[TagSchema]


class TransactionCreateSchema(BaseUpdateSchema):
    to_id: int
    from_id: int
    amount: Decimal
    currency: str

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("currency")
    def currency_must_be_lowercase(cls, v):
        return v.lower()

    @model_validator(mode="after")
    def check_ids_are_different(self):
        if self.from_id == self.to_id:
            raise ValueError("from_id and to_id must be different")
        return self


class TransactionUpdateSchema(BaseUpdateSchema):
    confirmed: bool | None = None


class TransactionFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    to_id: int | None = None
    from_id: int | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    currency: str | None = None
    confirmed: bool | None = None
