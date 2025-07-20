"""DTO for Transaction"""

from decimal import Decimal

from app.models.transaction import TransactionStatus
from app.schemas.base import (
    BaseFilterSchema,
    BaseReadSchema,
    BaseUpdateSchema,
    CurrencyDecimal,
)
from app.schemas.entity import EntitySchema
from app.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from app.schemas.tag import TagSchema
from app.schemas.treasury import TreasurySchema
from pydantic import field_validator, model_validator


class TransactionSchema(BaseReadSchema):
    actor_entity_id: int
    actor_entity: EntitySchema
    to_entity_id: int
    to_entity: EntitySchema
    from_entity_id: int
    from_entity: EntitySchema
    amount: CurrencyDecimal
    currency: str
    status: TransactionStatus
    tags: list[TagSchema]
    from_treasury_id: int | None
    to_treasury_id: int | None
    from_treasury: TreasurySchema | None
    to_treasury: TreasurySchema | None


class TransactionCreateSchema(BaseUpdateSchema):
    to_entity_id: int
    from_entity_id: int
    amount: Decimal
    currency: str
    status: TransactionStatus | None = None
    from_treasury_id: int | None = None
    to_treasury_id: int | None = None
    tag_ids: list[int] = []

    @field_validator("currency")
    def currency_must_be_lowercase(cls, v):
        return v.lower()

    @field_validator("from_treasury_id", mode="before")
    def normalize_from_treasury(cls, v):
        return None if v == 0 else v

    @field_validator("to_treasury_id", mode="before")
    def normalize_to_treasury(cls, v):
        return None if v == 0 else v


class TransactionUpdateSchema(BaseUpdateSchema):
    amount: Decimal | None = None
    currency: str | None = None
    status: TransactionStatus | None = None
    from_treasury_id: int | None = None
    to_treasury_id: int | None = None
    tag_ids: list[int] | None = None

    @field_validator("currency")
    def currency_must_be_lowercase(cls, v):
        return v.lower()

    @field_validator("from_treasury_id", mode="before")
    def normalize_from_treasury(cls, v):
        return None if v == 0 else v

    @field_validator("to_treasury_id", mode="before")
    def normalize_to_treasury(cls, v):
        return None if v == 0 else v


class TransactionFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    entity_id: int | None = None
    actor_entity_id: int | None = None
    to_entity_id: int | None = None
    from_entity_id: int | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    currency: str | None = None
    status: TransactionStatus | None = None
    from_treasury_id: int | None = None
    to_treasury_id: int | None = None
