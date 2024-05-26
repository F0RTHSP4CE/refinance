"""Mixin of a schema of a model which supports item tagging"""

from fastapi import Query
from pydantic import Field

from refinance.schemas.base import BaseFilterSchema


class TagsFilterSchemaMixin(BaseFilterSchema):
    tags_ids: list[int] = Field(Query([]))
