"""DTO for Entity"""

from refinance.schemas.base import BaseFilterSchema, BaseReadSchema, BaseUpdateSchema


class EntitySchema(BaseReadSchema):
    name: str
    active: bool


class EntityCreateSchema(BaseUpdateSchema):
    name: str


class EntityUpdateSchema(BaseUpdateSchema):
    name: str | None = None
    active: bool | None = None


class EntityFiltersSchema(BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
