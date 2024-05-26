"""DTO for Entity"""

from refinance.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema
from refinance.schemas.mixins.tags_filter_mixin import TagsFilterSchemaMixin
from refinance.schemas.tag import TagSchema


class EntitySchema(BaseReadSchema):
    name: str
    active: bool
    tags: list[TagSchema]


class EntityCreateSchema(BaseUpdateSchema):
    name: str


class EntityUpdateSchema(BaseUpdateSchema):
    name: str | None = None
    active: bool | None = None


class EntityFiltersSchema(TagsFilterSchemaMixin, BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
