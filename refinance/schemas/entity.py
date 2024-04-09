"""DTO for Entity"""

from fastapi import Query
from pydantic import Field

from refinance.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema
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


class EntityFiltersSchema(BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
    tags_ids: list[int] = Field(Query([]))
