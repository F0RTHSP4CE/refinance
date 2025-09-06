"""DTO for Entity"""

from typing import Optional

from app.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema
from app.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from app.schemas.tag import TagSchema
from pydantic import BaseModel, field_serializer, model_serializer


class EntityAuthSchema(BaseModel):
    telegram_id: int | str | None = None
    signal_id: int | str | None = None
    card_hash: str | None = None


class EntityAuthReadSchema(BaseModel):
    """Auth schema for API responses - excludes card_hash for security"""

    telegram_id: int | str | None = None
    signal_id: int | str | None = None
    card_hash: str | bool | None = None  # Accept string, serialize to boolean

    @field_serializer("card_hash")
    def serialize_card_hash(self, value):
        """Convert string card_hash to boolean presence indicator"""
        if isinstance(value, str) and value.strip():
            return True  # If it's a non-empty string, we have a card_hash
        elif value is None:
            return None
        else:
            return bool(value)  # Handle any other cases


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
    auth_card_hash: str | None = None
