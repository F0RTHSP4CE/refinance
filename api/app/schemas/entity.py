"""DTO for Entity"""

from typing import Optional

from app.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema
from app.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from app.schemas.tag import TagSchema
from pydantic import BaseModel


class EntityAuthSchema(BaseModel):
    telegram_id: int | str | None = None
    signal_id: int | str | None = None


class EntitySchema(BaseReadSchema):
    name: str
    active: bool
    tags: list[TagSchema]
    auth: Optional[EntityAuthSchema] | None


class EntityCreateSchema(BaseUpdateSchema):
    name: str
    auth: Optional[EntityAuthSchema] | None = None


class EntityUpdateSchema(BaseUpdateSchema):
    name: str | None = None
    active: bool | None = None
    auth: Optional[EntityAuthSchema] | None = None


class EntityFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
    auth_telegram_id: int | None = None
