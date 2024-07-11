"""Mixin of a schema of a model which supports item tagging"""

from app.schemas.base import BaseFilterSchema
from fastapi import Query
from pydantic import Field


class TagsFilterSchemaMixin(BaseFilterSchema):
    tags_ids: list[int] = Field(Query([]))
