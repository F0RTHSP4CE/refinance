"""DTO for Entity"""

from typing import Literal, Optional

from app.models.transaction import TransactionStatus
from app.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema
from app.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from app.schemas.tag import TagSchema
from pydantic import BaseModel, field_serializer, field_validator, model_serializer


class EntityAuthSchema(BaseModel):
    telegram_id: int | str | None = None
    signal_id: int | str | None = None


class EntityAuthReadSchema(BaseModel):
    """Auth schema for API responses - card management moved to entity_cards"""

    telegram_id: int | str | None = None
    signal_id: int | str | None = None


class EntitySchema(BaseReadSchema):
    name: str
    active: bool
    tags: list[TagSchema]
    auth: Optional[EntityAuthReadSchema] | None


class EntityCreateSchema(BaseUpdateSchema):
    name: str
    auth: Optional[EntityAuthSchema] | None = None
    tag_ids: list[int] = []


class EntityUpdateSchema(BaseUpdateSchema):
    name: str | None = None
    active: bool | None = None
    auth: Optional[EntityAuthSchema] | None = None
    tag_ids: list[int] | None = None


class EntityFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
    auth_telegram_id: int | None = None
    balance_currency: str | None = None
    balance_status: TransactionStatus | None = None
    balance_order: Literal["asc", "desc"] | None = None

    @field_validator("balance_currency")
    def normalize_balance_currency(cls, v: str | None) -> str | None:
        return v.lower() if v else v
