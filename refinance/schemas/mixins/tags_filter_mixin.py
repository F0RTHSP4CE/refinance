from fastapi import Query
from pydantic import Field

from refinance.schemas.base import BaseFilterSchema


class TagsFilterSchemaMixin(BaseFilterSchema):
    tags_ids: list[int] = Field(Query([]))
