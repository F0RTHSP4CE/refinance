"""Base DTOs for API endpoints"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    # needed for ORM
    model_config = ConfigDict(from_attributes=True)

    # default dump options to deserialize pydantic models
    def dump(self):
        return self.model_dump(exclude_unset=True)


class BaseReadSchema(BaseSchema):
    id: int
    comment: Optional[str] = None


class BaseUpdateSchema(BaseSchema):
    comment: Optional[str] = None


class BaseFilterSchema(BaseSchema):
    pass
