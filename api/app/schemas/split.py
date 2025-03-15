"""DTO for Split"""

from decimal import Decimal

from app.schemas.base import (
    BaseFilterSchema,
    BaseReadSchema,
    BaseUpdateSchema,
    CurrencyDecimal,
)
from app.schemas.entity import EntitySchema
from app.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from app.schemas.tag import TagSchema
from pydantic import field_validator


class SplitSchema(BaseReadSchema):
    actor_entity_id: int
    actor_entity: EntitySchema
    recipient_entity_id: int
    recipient_entity: EntitySchema
    participants: list[EntitySchema]
    amount: CurrencyDecimal
    currency: str
    performed: bool
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
    performed: bool | None = None


class SplitFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    recipient_entity_id: int | None = None
    actor_entity_id: int | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    currency: str | None = None
    performed: bool | None = None
    participant_entity_id: int | None = None
