"""DTO for Invoice"""

from datetime import date
from decimal import Decimal

from app.models.invoice import InvoiceStatus
from app.schemas.base import (
    BaseFilterSchema,
    BaseReadSchema,
    BaseSchema,
    BaseUpdateSchema,
    CurrencyDecimal,
)
from app.schemas.entity import EntitySchema
from app.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from app.schemas.tag import TagSchema
from pydantic import Field, field_validator, model_validator


class InvoiceAmountSchema(BaseSchema):
    currency: str
    amount: CurrencyDecimal


class InvoiceAmountCreateSchema(BaseSchema):
    currency: str
    amount: Decimal

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v > 0:
            return v
        raise ValueError("Amount must be greater than 0")

    @field_validator("currency")
    def currency_must_be_lowercase(cls, v):
        return v.lower()


class InvoiceSchema(BaseReadSchema):
    actor_entity_id: int
    actor_entity: EntitySchema
    from_entity_id: int
    from_entity: EntitySchema
    to_entity_id: int
    to_entity: EntitySchema
    amounts: list[InvoiceAmountSchema]
    billing_period: date | None = None
    status: InvoiceStatus
    tags: list[TagSchema]
    transaction_id: int | None = None


class InvoiceCreateSchema(BaseUpdateSchema):
    from_entity_id: int
    to_entity_id: int
    amounts: list[InvoiceAmountCreateSchema] = Field(default_factory=list)
    billing_period: date | None = None
    tag_ids: list[int] = []

    @model_validator(mode="after")
    def amounts_must_be_unique(self) -> "InvoiceCreateSchema":
        currencies = [item.currency for item in self.amounts]
        if len(currencies) != len(set(currencies)):
            raise ValueError("Amounts must use unique currencies")
        if not self.amounts:
            raise ValueError("At least one amount must be provided")
        return self


class InvoiceUpdateSchema(BaseUpdateSchema):
    amounts: list[InvoiceAmountCreateSchema] | None = None
    billing_period: date | None = None
    tag_ids: list[int] | None = None

    @model_validator(mode="after")
    def amounts_must_be_unique(self) -> "InvoiceUpdateSchema":
        if self.amounts is None:
            return self
        currencies = [item.currency for item in self.amounts]
        if len(currencies) != len(set(currencies)):
            raise ValueError("Amounts must use unique currencies")
        if not self.amounts:
            raise ValueError("At least one amount must be provided")
        return self


class InvoiceFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    entity_id: int | None = None
    actor_entity_id: int | None = None
    from_entity_id: int | None = None
    to_entity_id: int | None = None
    status: InvoiceStatus | None = None
    billing_period: date | None = None
