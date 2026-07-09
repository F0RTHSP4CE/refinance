"""DTO for InvoiceItem"""

from decimal import Decimal

from app.schemas.base import (
    BaseReadSchema,
    BaseSchema,
    BaseUpdateSchema,
    CurrencyDecimal,
)
from app.schemas.entity import EntitySchema
from app.schemas.tag import TagSchema
from pydantic import Field, field_validator, model_validator


class InvoiceItemAmountSchema(BaseSchema):
    currency: str
    amount: CurrencyDecimal


class InvoiceItemAmountCreateSchema(BaseSchema):
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


class InvoiceItemCreateSchema(BaseUpdateSchema):
    """Schema for a single line item when creating a multi-recipient invoice."""

    to_entity_id: int | None = None
    to_tag_id: int | None = None
    amounts: list[InvoiceItemAmountCreateSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_item(self) -> "InvoiceItemCreateSchema":
        if not self.amounts:
            raise ValueError("Each invoice item must have at least one amount.")
        currencies = [a.currency for a in self.amounts]
        if len(currencies) != len(set(currencies)):
            raise ValueError("Item amounts must use unique currencies.")
        return self


class InvoiceItemSchema(BaseReadSchema):
    """Full response schema for an invoice item."""

    invoice_id: int
    to_entity_id: int | None = None
    to_entity: EntitySchema | None = None
    to_tag_id: int | None = None
    to_tag: TagSchema | None = None
    amounts: list[InvoiceItemAmountSchema]
    transaction_id: int | None = None


class InvoiceItemPaymentSchema(BaseSchema):
    """Per-item payment specification sent to POST /invoices/{id}/pay-items."""

    item_id: int
    to_entity_id: int
    currency: str | None = None  # Optional; service will auto-select if not provided
    amount: Decimal | None = (
        None  # Optional; derived from invoice item when currency is auto-selected
    )

    @field_validator("currency")
    def currency_must_be_lowercase(cls, v):
        if v is None:
            return None
        return v.lower()

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v is None:
            return None
        if v > 0:
            return v
        raise ValueError("Amount must be greater than 0")


class InvoicePayItemsSchema(BaseSchema):
    """Request body for POST /invoices/{id}/pay-items."""

    items: list[InvoiceItemPaymentSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def items_required(self) -> "InvoicePayItemsSchema":
        if not self.items:
            raise ValueError("At least one item payment must be provided.")
        return self
