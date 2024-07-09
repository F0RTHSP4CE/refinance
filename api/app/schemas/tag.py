"""DTO for Tag"""

from app.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema


class TagSchema(BaseReadSchema):
    name: str


class TagCreateSchema(BaseUpdateSchema):
    name: str


class TagUpdateSchema(BaseUpdateSchema):
    name: str | None = None


class TagFiltersSchema(BaseFilterSchema):
    name: str | None = None
