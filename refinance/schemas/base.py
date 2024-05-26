"""Base DTOs for API endpoints"""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    # needed for ORM
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    # default dump options to deserialize pydantic models
    def dump(self):
        return self.model_dump(exclude_none=True)


class BaseReadSchema(BaseSchema):
    id: int
    comment: Optional[str] = None
    created_at: datetime


class BaseUpdateSchema(BaseSchema):
    comment: Optional[str] = None


class BaseFilterSchema(BaseSchema):
    comment: str | None = None


M = TypeVar("M")


class PaginationSchema(BaseSchema, Generic[M]):
    items: list[M]
    total: int
    skip: int
    limit: int
