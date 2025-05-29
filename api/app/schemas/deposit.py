"""DTO for Deposit"""

from decimal import Decimal

from app.models.deposit import DepositStatus
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


class DepositSchema(BaseReadSchema):
    actor_entity: EntitySchema
    from_entity: EntitySchema
    to_entity: EntitySchema
    amount: CurrencyDecimal
    currency: str
    status: str
    provider: str
    details: dict | None = None
    tags: list[TagSchema]


class DepositCreateSchema(BaseUpdateSchema):
    from_entity_id: int
    to_entity_id: int
    amount: Decimal
    currency: str
    provider: str
    details: dict | None = None

    @field_validator("currency")
    def currency_must_be_lowercase(cls, v):
        return v.lower()


class DepositUpdateSchema(BaseUpdateSchema):
    status: DepositStatus | None = None
    details: dict | None = None


class DepositFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    entity_id: int | None = None
    actor_entity_id: int | None = None
    from_entity_id: int | None = None
    to_entity_id: int | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    currency: str | None = None
    status: str | None = None
    provider: str | None = None
