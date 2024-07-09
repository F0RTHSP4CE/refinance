"""DTO for Entity"""

from app.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema
from app.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from app.schemas.tag import TagSchema


class EntitySchema(BaseReadSchema):
    name: str
    active: bool
    tags: list[TagSchema]
    telegram_id: int | None


class EntityCreateSchema(BaseUpdateSchema):
    name: str
    telegram_id: int | None = None


class EntityUpdateSchema(BaseUpdateSchema):
    name: str | None = None
    active: bool | None = None
    telegram_id: int | None = None


class EntityFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
    telegram_id: int | None = None
