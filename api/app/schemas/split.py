"""DTO for Split"""

from decimal import Decimal
from typing import Optional

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
from app.schemas.transaction import TransactionSchema
from pydantic import BaseModel, Field, field_validator


class SplitParticipantAddSchema(BaseModel):
    entity_id: int
    fixed_amount: Optional[Decimal] = None

    @field_validator("fixed_amount")
    def fixed_amount_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Fixed amount must be non-negative")
        return v


class SplitParticipantSchema(BaseSchema):
    entity: EntitySchema
    fixed_amount: Optional[CurrencyDecimal] = None


class SplitSharePreview(BaseSchema):
    current_share: CurrencyDecimal
    next_share: CurrencyDecimal
    impact_percent: Decimal


class SplitSchema(BaseReadSchema):
    actor_entity_id: int
    actor_entity: EntitySchema
    recipient_entity_id: int
    recipient_entity: EntitySchema
    participants: list[SplitParticipantSchema] = Field(default_factory=list)
    amount: CurrencyDecimal
    currency: str
    collected_amount: Decimal
    performed: bool
    share_preview: SplitSharePreview
    performed_transactions: list[TransactionSchema] = Field(default_factory=list)
    tags: list[TagSchema]


class SplitCreateSchema(BaseUpdateSchema):
    recipient_entity_id: int
    amount: Decimal
    currency: str

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v > 0:
            return v
        raise ValueError("Amount must be positive")

    @field_validator("currency")
    def currency_must_be_lowercase(cls, v):
        return v.lower()


class SplitUpdateSchema(BaseUpdateSchema):
    recipient_entity_id: int | None = None
    amount: Decimal | None = None
    currency: str | None = None


class SplitFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    recipient_entity_id: int | None = None
    actor_entity_id: int | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    currency: str | None = None
    performed: bool | None = None
    entity_id: int | None = None
