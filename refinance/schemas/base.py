"""Base DTOs for API endpoints"""

from typing import Any, Generic, Optional, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    # needed for ORM
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    # default dump options to deserialize pydantic models
    def dump(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class BaseReadSchema(BaseSchema):
    id: int
    comment: Optional[str] = None


class BaseUpdateSchema(BaseSchema):
    comment: Optional[str] = None


class BaseFilterSchema(BaseSchema):
    pass


_M = TypeVar("_M", bound=BaseModel)


class PaginationSchema(BaseSchema, Generic[_M]):
    items: Sequence[_M]
    total: int
    skip: int
    limit: int
