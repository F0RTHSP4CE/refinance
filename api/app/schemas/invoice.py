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
from app.schemas.invoice_item import (
    InvoiceItemCreateSchema,
    InvoiceItemSchema,
    InvoicePayItemsSchema,
)
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
    to_entity_id: int | None = None
    to_entity: EntitySchema | None = None
    amounts: list[InvoiceAmountSchema]
    billing_period: date | None = None
    status: InvoiceStatus
    tags: list[TagSchema]
    transaction_id: int | None = None
    items: list[InvoiceItemSchema] = Field(default_factory=list)


class InvoiceCreateSchema(BaseUpdateSchema):
    from_entity_id: int
    to_entity_id: int | None = None
    amounts: list[InvoiceAmountCreateSchema] = Field(default_factory=list)
    items: list[InvoiceItemCreateSchema] = Field(default_factory=list)
    billing_period: date | None = None
    tag_ids: list[int] = []

    @model_validator(mode="after")
    def validate_schema(self) -> "InvoiceCreateSchema":
        has_simple = bool(self.to_entity_id and self.amounts)
        has_items = bool(self.items)
        if has_simple and has_items:
            raise ValueError(
                "Provide either (to_entity_id + amounts) for a simple invoice "
                "or items for a multi-recipient invoice, not both."
            )
        if not has_simple and not has_items:
            raise ValueError("Provide either (to_entity_id + amounts) or items.")
        if has_simple:
            currencies = [item.currency for item in self.amounts]
            if len(currencies) != len(set(currencies)):
                raise ValueError("Amounts must use unique currencies")
        return self


class InvoiceUpdateSchema(BaseUpdateSchema):
    amounts: list[InvoiceAmountCreateSchema] | None = None
    items: list[InvoiceItemCreateSchema] | None = None
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


class InvoiceAutoPayReportSchema(BaseSchema):
    paid: int


class InvoiceBulkCreateSchema(BaseUpdateSchema):
    from_entity_ids: list[int] = Field(default_factory=list)
    from_tag_ids: list[int] = Field(default_factory=list)
    to_entity_id: int | None = None
    amounts: list[InvoiceAmountCreateSchema] = Field(default_factory=list)
    items: list[InvoiceItemCreateSchema] = Field(default_factory=list)
    billing_period: date | None = None
    tag_ids: list[int] = Field(default_factory=list)
    comment: str | None = None

    @model_validator(mode="after")
    def validate_schema(self) -> "InvoiceBulkCreateSchema":
        if not self.from_tag_ids:
            raise ValueError("Must provide from_tag_ids")
        if self.items:
            # Multi-item mode: items take precedence over to_entity_id + amounts
            pass
        else:
            if self.to_entity_id is None:
                raise ValueError("Must provide to_entity_id when not using items")
            if not self.amounts:
                raise ValueError("At least one amount must be provided")
            currencies = [item.currency for item in self.amounts]
            if len(currencies) != len(set(currencies)):
                raise ValueError("Amounts must use unique currencies")
        return self


class InvoiceBulkCreateReportSchema(BaseSchema):
    billing_period: date
    created_count: int
    skipped_count: int
    invoice_ids: list[int]
